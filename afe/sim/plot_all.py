"""Plot all AFE sim results — Bode, PGA gain, S/H transient, AFE chain."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

PLOTS = Path("/Users/fidelmakatia/Desktop/IEEE/afe/plots")

# Op-amp Bode already generated locally; just re-do PGA, S/H, AFE-top plots
# ── PGA AC gain ─────────────────────────────────────────────────────────────
pga = np.loadtxt(PLOTS / "pga_ac.dat")
fig, ax = plt.subplots(figsize=(8, 4.5), constrained_layout=True)
ax.semilogx(pga[:, 0], pga[:, 1], lw=1.8)
ax.axhline(40, color="#999", ls=":", label="target gain 40 dB")
ax.set_xlabel("frequency (Hz)")
ax.set_ylabel("|gain| (dB)")
ax.set_title("PGA closed-loop gain (Rf=99 kΩ, target ×100 = 40 dB)")
ax.grid(which="both", alpha=0.3)
ax.legend()
fig.savefig(PLOTS / "pga_gain.png", dpi=130)
plt.close(fig)
print("wrote pga_gain.png")

# ── S/H transient — input + sampled output + clock ──────────────────────────
sh = np.loadtxt(PLOTS / "sh_tran.dat")
fig, ax = plt.subplots(2, 1, figsize=(10, 6), sharex=True, constrained_layout=True)
ax[0].plot(sh[:, 0] * 1e6, sh[:, 1], lw=1.2, label="vin (1 kHz sine)")
ax[0].plot(sh[:, 2] * 1e6, sh[:, 3], lw=1.2, label="vout (sampled)", color="#d62728")
ax[0].set_ylabel("voltage (V)")
ax[0].grid(alpha=0.3)
ax[0].legend(loc="upper right")
ax[0].set_title("Bottom-plate S/H — input track and sampled output")

ax[1].plot(sh[:, 4] * 1e6, sh[:, 5], lw=1.0, label="phi1")
ax[1].plot(sh[:, 6] * 1e6, sh[:, 7], lw=1.0, label="phi1a", color="#ff7f0e")
ax[1].set_xlabel("time (µs)")
ax[1].set_ylabel("clock (V)")
ax[1].grid(alpha=0.3)
ax[1].legend(loc="upper right")
ax[1].set_title("Non-overlapping sample clocks (Φ1a opens 0.5 µs before Φ1)")
fig.savefig(PLOTS / "sh_tran.png", dpi=130)
plt.close(fig)
print("wrote sh_tran.png")

# ── AFE top transient — input → PGA out → sampled output ────────────────────
afe = np.loadtxt(PLOTS / "afe_tran.dat")
fig, ax = plt.subplots(3, 1, figsize=(11, 7.5), sharex=True, constrained_layout=True)

ax[0].plot(afe[:, 0] * 1e6, afe[:, 1], lw=1.0, color="#1f77b4")
ax[0].set_ylabel("VINP (V)")
ax[0].set_title("AFE top-level signal chain — input → PGA → S/H")
ax[0].grid(alpha=0.3)

ax[1].plot(afe[:, 2] * 1e6, afe[:, 3], lw=1.0, color="#2ca02c")
ax[1].set_ylabel("PGA out (V)")
ax[1].grid(alpha=0.3)

ax[2].plot(afe[:, 4] * 1e6, afe[:, 5], lw=1.0, color="#d62728")
ax[2].set_xlabel("time (µs)")
ax[2].set_ylabel("VOUT (sampled, V)")
ax[2].grid(alpha=0.3)
fig.savefig(PLOTS / "afe_chain.png", dpi=130)
plt.close(fig)
print("wrote afe_chain.png")
