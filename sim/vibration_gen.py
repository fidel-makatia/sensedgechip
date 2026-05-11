"""Synthetic vibration signal generator for SenseEdge ASIC validation.

Models 4 machine-health classes with realistic spectral signatures:
    0 - Healthy        : fundamental at running speed + low broadband
    1 - Bearing wear   : BPFO/BPFI tone families in mid/high band + sidebands
    2 - Rotor imbalance: dominant fundamental, low harmonics
    3 - Misalignment   : 2x fundamental harmonic elevated

All signals are 12-bit signed ADC samples (matching the chip's SPI ADC input
range). Sample rate matches the chip's 100 kSPS max.
"""

from dataclasses import dataclass
import numpy as np

FS_HZ = 1024.0          # 1 kSPS — gives 16 Hz bin spacing with a 64-pt FFT,
                        # which resolves rotor-harmonic series (1x, 2x, 3x at
                        # 20-80 Hz fundamentals) into separate bins. The chip
                        # supports up to 100 kSPS for higher-frequency
                        # bearing-fault analysis (BPFO/BPFI) when needed.
N_FRAME = 64            # FFT frame length (matches fft_engine.v)
ADC_MAX = 2**11 - 1     # 12-bit signed ADC max code


@dataclass
class MachineParams:
    """Physical machine parameters for synthetic signal generation."""
    f_rot_hz: float          # rotor speed (Hz)
    n_balls: int             # bearing ball count (for BPFO/BPFI calc)
    pitch_diameter: float    # bearing pitch dia (mm)
    ball_diameter: float     # bearing ball dia (mm)
    contact_angle_deg: float = 0.0


def bpfo(p: MachineParams) -> float:
    """Ball-pass frequency, outer race."""
    return (p.n_balls / 2) * p.f_rot_hz * (1 - p.ball_diameter / p.pitch_diameter
                                            * np.cos(np.deg2rad(p.contact_angle_deg)))


def bpfi(p: MachineParams) -> float:
    """Ball-pass frequency, inner race."""
    return (p.n_balls / 2) * p.f_rot_hz * (1 + p.ball_diameter / p.pitch_diameter
                                            * np.cos(np.deg2rad(p.contact_angle_deg)))


def _make_t() -> np.ndarray:
    return np.arange(N_FRAME) / FS_HZ


def gen_healthy(p: MachineParams, rng: np.random.Generator) -> np.ndarray:
    """Clean fundamental at rotor speed, low broadband noise floor."""
    t = _make_t()
    amp = rng.uniform(0.4, 0.6) * ADC_MAX
    phase = rng.uniform(0, 2 * np.pi)
    signal = amp * np.sin(2 * np.pi * p.f_rot_hz * t + phase)
    signal += rng.normal(0, 0.02 * ADC_MAX, N_FRAME)   # low broadband noise
    return signal


def gen_bearing_wear(p: MachineParams, rng: np.random.Generator) -> np.ndarray:
    """BPFO + BPFI tones + sidebands at rotor speed; broadband shock content."""
    t = _make_t()
    # Underlying rotor tone (still there, lower amp)
    amp_rot = rng.uniform(0.2, 0.4) * ADC_MAX
    sig = amp_rot * np.sin(2 * np.pi * p.f_rot_hz * t + rng.uniform(0, 2 * np.pi))

    # BPFO and BPFI fault tones — clip to Nyquist
    for f_fault in [bpfo(p), bpfi(p)]:
        if f_fault < FS_HZ / 2:
            sig += rng.uniform(0.3, 0.5) * ADC_MAX * np.sin(
                2 * np.pi * f_fault * t + rng.uniform(0, 2 * np.pi))
            # rotor-speed sidebands
            for sb in (-1, 1):
                f_sb = f_fault + sb * p.f_rot_hz
                if 0 < f_sb < FS_HZ / 2:
                    sig += rng.uniform(0.1, 0.2) * ADC_MAX * np.sin(
                        2 * np.pi * f_sb * t + rng.uniform(0, 2 * np.pi))

    # Impulsive shock content (broadband)
    sig += rng.normal(0, 0.08 * ADC_MAX, N_FRAME)
    return sig


def gen_imbalance(p: MachineParams, rng: np.random.Generator) -> np.ndarray:
    """Dominant fundamental, low harmonics, low broadband."""
    t = _make_t()
    amp = rng.uniform(0.7, 0.9) * ADC_MAX
    sig = amp * np.sin(2 * np.pi * p.f_rot_hz * t + rng.uniform(0, 2 * np.pi))
    # Slight 2x harmonic
    sig += rng.uniform(0.05, 0.10) * ADC_MAX * np.sin(
        2 * np.pi * 2 * p.f_rot_hz * t + rng.uniform(0, 2 * np.pi))
    sig += rng.normal(0, 0.03 * ADC_MAX, N_FRAME)
    return sig


def gen_misalignment(p: MachineParams, rng: np.random.Generator) -> np.ndarray:
    """2x fundamental harmonic elevated, some 3x."""
    t = _make_t()
    amp1 = rng.uniform(0.3, 0.5) * ADC_MAX
    amp2 = rng.uniform(0.5, 0.8) * ADC_MAX
    amp3 = rng.uniform(0.10, 0.20) * ADC_MAX
    sig  = amp1 * np.sin(2 * np.pi *     p.f_rot_hz * t + rng.uniform(0, 2 * np.pi))
    sig += amp2 * np.sin(2 * np.pi * 2 * p.f_rot_hz * t + rng.uniform(0, 2 * np.pi))
    sig += amp3 * np.sin(2 * np.pi * 3 * p.f_rot_hz * t + rng.uniform(0, 2 * np.pi))
    sig += rng.normal(0, 0.04 * ADC_MAX, N_FRAME)
    return sig


GENERATORS = {
    0: gen_healthy,
    1: gen_bearing_wear,
    2: gen_imbalance,
    3: gen_misalignment,
}

CLASS_NAMES = {
    0: "Healthy",
    1: "Bearing wear",
    2: "Imbalance",
    3: "Misalignment",
}


def random_machine(rng: np.random.Generator) -> MachineParams:
    """Random plausible industrial machine parameters."""
    return MachineParams(
        f_rot_hz=rng.uniform(30.0, 80.0),          # 1800-4800 RPM
        n_balls=int(rng.integers(7, 13)),
        pitch_diameter=rng.uniform(20.0, 45.0),
        ball_diameter=rng.uniform(5.0, 10.0),
        contact_angle_deg=rng.uniform(0.0, 15.0),
    )


def generate_dataset(n_per_class: int, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Returns X[n_samples, 64] int16 ADC codes, y[n_samples] class labels."""
    rng = np.random.default_rng(seed)
    n_total = n_per_class * len(GENERATORS)
    X = np.zeros((n_total, N_FRAME), dtype=np.int16)
    y = np.zeros(n_total, dtype=np.int8)
    idx = 0
    for cls, gen in GENERATORS.items():
        for _ in range(n_per_class):
            p = random_machine(rng)
            sig = gen(p, rng)
            X[idx] = np.clip(np.round(sig), -ADC_MAX - 1, ADC_MAX).astype(np.int16)
            y[idx] = cls
            idx += 1
    # Shuffle
    perm = rng.permutation(n_total)
    return X[perm], y[perm]


if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    X, y = generate_dataset(n)
    print(f"X: {X.shape} {X.dtype}, y: {y.shape}")
    for cls, name in CLASS_NAMES.items():
        mask = y == cls
        print(f"  class {cls} ({name}): {mask.sum()} samples, "
              f"signal range [{X[mask].min()}, {X[mask].max()}]")
