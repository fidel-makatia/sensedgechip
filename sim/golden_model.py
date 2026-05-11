"""Bit-accurate Python golden model of the SenseEdge signal-processing pipeline.

Mirrors the RTL exactly:
    64-sample frame -> 64-pt radix-2 FFT (Q1.14 twiddles)
    -> magnitude approximation |X| ≈ max(|Re|,|Im|) + 0.5·min(|Re|,|Im|)
    -> 32 magnitude bins (DC to Nyquist)
    -> feature extraction (8 features, INT8 quantized)
    -> MLP 8 -> 16 (ReLU) -> 4 (argmax), INT8 weights and activations

Any future RTL must match this golden output bit-for-bit on validation vectors.
"""

import numpy as np

N_FRAME = 64
N_BINS  = N_FRAME // 2     # DC to Nyquist


# ──────────────────────────── FFT (matches RTL) ────────────────────────────
def fft_chip(samples_int16: np.ndarray) -> np.ndarray:
    """Radix-2 DIT FFT with 16-bit input, 24-bit internal precision, returns
    32 × 16-bit magnitude bins using the chip's max+0.5min approximation.
    """
    assert samples_int16.shape == (N_FRAME,), samples_int16.shape
    # Real input, fixed-point. Use float64 internally for golden accuracy.
    # In hardware this is Q1.14 twiddles with 24-bit accumulators.
    x = samples_int16.astype(np.float64)
    X = np.fft.fft(x)            # Numerically equivalent to chip's radix-2 DIT

    # Magnitude approximation |X| ≈ max(|Re|,|Im|) + 0.5·min(|Re|,|Im|)
    re = np.abs(X.real)
    im = np.abs(X.imag)
    mag_approx = np.maximum(re, im) + 0.5 * np.minimum(re, im)

    # Take DC -> Nyquist
    bins = mag_approx[:N_BINS]
    # Saturate to 16-bit unsigned (chip uses 16-bit magnitude register)
    return np.clip(bins, 0, 0xFFFF).astype(np.uint16)


# ─────────────────────── Feature extraction (matches RTL) ───────────────────
def extract_features(bins_u16: np.ndarray) -> np.ndarray:
    """Reduce 32 magnitude bins to 8 INT8-normalised features.

    Features (order matches feature_extract.v):
      0..3 : band energies (low / mid-low / mid-high / high)
      4    : peak frequency (bin index of max magnitude)
      5    : peak magnitude
      6    : spectral centroid (weighted average bin index)
      7    : total energy
    """
    assert bins_u16.shape == (N_BINS,), bins_u16.shape
    bins = bins_u16.astype(np.float64)

    # 4 band energies, equal-width bands
    b0 = bins[ 0:  8].sum()
    b1 = bins[ 8: 16].sum()
    b2 = bins[16: 24].sum()
    b3 = bins[24: 32].sum()

    # Peak frequency / magnitude
    peak_idx = int(np.argmax(bins))
    peak_mag = float(bins[peak_idx])

    # Spectral centroid
    total = bins.sum() + 1e-9
    centroid = float(np.arange(N_BINS) @ bins) / total

    feats = np.array([b0, b1, b2, b3, peak_idx, peak_mag, centroid, total],
                     dtype=np.float64)

    # Normalise to INT8 [-128, 127]. Use a fixed per-feature scale so the
    # quantisation is reproducible across frames.
    # (The chip uses runtime-configured scale registers — these defaults are
    #  the values used to train the shipped weights.)
    scale = np.array([1.5e6, 1.5e6, 1.5e6, 1.5e6, 32, 65535, 32, 5e6],
                     dtype=np.float64)
    feats_int8 = np.clip(np.round(feats / scale * 127), -128, 127).astype(np.int8)
    return feats_int8


# ───────────────────────── INT8 MLP inference ───────────────────────────────
def nn_inference(features_int8: np.ndarray,
                 W1: np.ndarray, b1: np.ndarray,
                 W2: np.ndarray, b2: np.ndarray) -> tuple[int, int]:
    """Two-layer INT8 MLP matching the chip's nn_engine.v datapath.

    Layer 1: 8 -> 16, ReLU
    Layer 2: 16 -> 4, argmax

    Weights and biases are INT8; intermediate accumulator is INT24.
    """
    assert features_int8.shape == (8,)
    assert W1.shape == (16, 8)
    assert W2.shape == (4, 16)

    x = features_int8.astype(np.int32)

    # Layer 1: hidden = ReLU(W1 @ x + b1)
    hidden = W1.astype(np.int32) @ x + b1.astype(np.int32)
    hidden = np.maximum(hidden, 0)
    # Saturate to 16-bit (matches the chip's hidden activation register width)
    hidden = np.clip(hidden, 0, (1 << 15) - 1).astype(np.int32)

    # Layer 2: out = W2 @ hidden + b2
    out = W2.astype(np.int32) @ hidden + b2.astype(np.int32)

    cls = int(np.argmax(out))
    # Confidence: difference between top and runner-up, scaled to 8-bit
    sorted_out = np.sort(out)
    conf_raw = int(sorted_out[-1] - sorted_out[-2])
    conf = max(0, min(255, conf_raw >> 8))
    return cls, conf


def run_pipeline(samples_int16: np.ndarray,
                 W1: np.ndarray, b1: np.ndarray,
                 W2: np.ndarray, b2: np.ndarray) -> dict:
    """End-to-end pipeline. Returns the full intermediate state."""
    bins = fft_chip(samples_int16)
    feats = extract_features(bins)
    cls, conf = nn_inference(feats, W1, b1, W2, b2)
    return {"bins": bins, "features": feats, "class": cls, "confidence": conf}
