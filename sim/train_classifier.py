"""Train the 8→16→4 INT8 MLP on synthetic vibration data.

Produces:
  weights.npz   – INT8 W1, b1, W2, b2 for both Python golden and chip RTL
  train_log.txt – training curve + final per-class accuracy
"""

from pathlib import Path
import numpy as np

from vibration_gen import generate_dataset, CLASS_NAMES
from golden_model import fft_chip, extract_features


def build_feature_matrix(X: np.ndarray) -> np.ndarray:
    """Run the chip's front-end (FFT + features) on each frame."""
    feats = np.zeros((X.shape[0], 8), dtype=np.int8)
    for i, frame in enumerate(X):
        bins = fft_chip(frame)
        feats[i] = extract_features(bins)
    return feats


def quantize_to_int8(arr: np.ndarray) -> tuple[np.ndarray, float]:
    """Symmetric INT8 quantisation. Returns (q_arr, scale)."""
    m = max(np.abs(arr).max(), 1e-8)
    scale = m / 127.0
    q = np.clip(np.round(arr / scale), -128, 127).astype(np.int8)
    return q, scale


def softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def main() -> None:
    np.random.seed(0)
    out_dir = Path(__file__).parent / "artifacts"
    out_dir.mkdir(exist_ok=True)

    # ── Generate data ──
    print("Generating 2000 samples/class...")
    X_train, y_train = generate_dataset(n_per_class=2000, seed=0)
    X_val,   y_val   = generate_dataset(n_per_class=500,  seed=1)

    print("Extracting features through the chip's front-end (FFT + extractor)...")
    F_train = build_feature_matrix(X_train)
    F_val   = build_feature_matrix(X_val)
    print(f"  F_train: {F_train.shape} {F_train.dtype}, "
          f"range [{F_train.min()}, {F_train.max()}]")

    # ── FP32 MLP training with Adam (then INT8 quantise) ──
    # 8 -> 16 -> 4. Small enough to train without PyTorch.
    rng = np.random.default_rng(42)
    # He init for ReLU (variance = 2/fan_in)
    W1f = rng.normal(0, np.sqrt(2.0 / 8),  (16, 8))
    b1f = np.zeros(16)
    W2f = rng.normal(0, np.sqrt(2.0 / 16), (4, 16))
    b2f = np.zeros(4)

    # Center features around 0 so dot products aren't biased.
    # Features are INT8 in [0, 127] -> shift to [-1, 1].
    def _norm(F):
        return (F.astype(np.float32) - 63.5) / 63.5

    F_tr_f = _norm(F_train)
    F_va_f = _norm(F_val)

    # Standardize per-feature on the training set for stable gradients
    mu  = F_tr_f.mean(axis=0)
    std = F_tr_f.std(axis=0) + 1e-6
    F_tr_f = (F_tr_f - mu) / std
    F_va_f = (F_va_f - mu) / std

    # Adam optimizer
    lr = 0.01
    beta1, beta2, eps = 0.9, 0.999, 1e-8
    mW1, vW1 = np.zeros_like(W1f), np.zeros_like(W1f)
    mb1, vb1 = np.zeros_like(b1f), np.zeros_like(b1f)
    mW2, vW2 = np.zeros_like(W2f), np.zeros_like(W2f)
    mb2, vb2 = np.zeros_like(b2f), np.zeros_like(b2f)

    epochs = 300
    y_tr_oh = np.eye(4)[y_train]
    log_lines = []

    for ep in range(1, epochs + 1):
        # Forward
        h_pre = F_tr_f @ W1f.T + b1f
        h     = np.maximum(h_pre, 0)
        z     = h @ W2f.T + b2f
        p     = softmax(z)
        loss  = -np.log(p[np.arange(len(y_train)), y_train] + 1e-9).mean()

        # Backward
        dz = (p - y_tr_oh) / len(y_train)
        dW2 = dz.T @ h
        db2 = dz.sum(axis=0)
        dh  = dz @ W2f
        dh_pre = dh * (h_pre > 0)
        dW1 = dh_pre.T @ F_tr_f
        db1 = dh_pre.sum(axis=0)

        # Adam update
        for (param, grad, m, v) in [
            (W1f, dW1, mW1, vW1),
            (b1f, db1, mb1, vb1),
            (W2f, dW2, mW2, vW2),
            (b2f, db2, mb2, vb2),
        ]:
            m[:] = beta1 * m + (1 - beta1) * grad
            v[:] = beta2 * v + (1 - beta2) * (grad * grad)
            m_hat = m / (1 - beta1 ** ep)
            v_hat = v / (1 - beta2 ** ep)
            param -= lr * m_hat / (np.sqrt(v_hat) + eps)

        if ep % 25 == 0 or ep == epochs:
            h_v = np.maximum(F_va_f @ W1f.T + b1f, 0)
            z_v = h_v @ W2f.T + b2f
            acc = (z_v.argmax(axis=1) == y_val).mean()
            line = f"epoch {ep:4d}  loss={loss:.4f}  val_acc={acc:.4f}"
            print(line)
            log_lines.append(line)

    # The per-feature standardisation needs to fold into the chip's INT8
    # weights. We accomplish this by absorbing (mu, std) into the first
    # layer's weights and biases.
    # The chip computes: hidden = W1 @ x_int8 + b1
    # We want:           hidden = W1f @ ((x_int8 - 63.5)/63.5 - mu) / std
    # Expand:            hidden = (W1f / std) @ (x_int8/63.5) - (W1f / std) @ (1/63.5 + mu) + ...
    # This is fiddly. Simpler: re-train weights so the chip can use raw
    # INT8 features directly. Below we transform W1, b1 to do that.
    # Final form:   hidden = W1_chip @ x_int8 + b1_chip
    # where x_int8 in [0, 127], and the transform is applied implicitly.
    # input_to_layer = (x_int8/63.5 - 1 - mu) / std
    # W1f @ input_to_layer = W1f / (63.5 * std) @ x_int8  -  W1f @ ((1 + mu)/std)
    W1_eff = W1f / (63.5 * std)
    b1_eff = b1f - W1f @ ((1.0 + mu) / std)

    # ── Quantise to INT8 using the *effective* W1, b1 (absorbing input normalization) ──
    W1_q, s_W1 = quantize_to_int8(W1_eff)
    W2_q, s_W2 = quantize_to_int8(W2f)

    b1_q = np.clip(np.round(b1_eff / s_W1), -32768, 32767).astype(np.int16)
    b2_q = np.clip(np.round(b2f    / s_W2), -32768, 32767).astype(np.int16)

    # ── INT8 validation accuracy ──
    from golden_model import nn_inference
    int8_preds = np.zeros(len(y_val), dtype=np.int8)
    for i, feats in enumerate(F_val):
        cls, _ = nn_inference(feats, W1_q, b1_q, W2_q, b2_q)
        int8_preds[i] = cls
    int8_acc = (int8_preds == y_val).mean()
    line = f"\nINT8 quantised val accuracy: {int8_acc:.4f}"
    print(line); log_lines.append(line)

    # Per-class accuracy
    print("\nPer-class accuracy (INT8):")
    log_lines.append("\nPer-class accuracy (INT8):")
    for cls, name in CLASS_NAMES.items():
        mask = y_val == cls
        acc = (int8_preds[mask] == cls).mean()
        line = f"  {cls} {name:15s}  acc={acc:.4f}  (n={mask.sum()})"
        print(line); log_lines.append(line)

    # ── Save ──
    np.savez(out_dir / "weights.npz",
             W1=W1_q, b1=b1_q, W2=W2_q, b2=b2_q,
             W1_scale=s_W1, W2_scale=s_W2)
    (out_dir / "train_log.txt").write_text("\n".join(log_lines))

    # Save validation set for downstream use
    np.savez(out_dir / "val_data.npz", X=X_val, y=y_val, features=F_val)

    print(f"\nSaved → {out_dir}/")


if __name__ == "__main__":
    main()
