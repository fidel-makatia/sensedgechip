"""Plot Bode response from ngspice .dat output."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

dat = Path("/opt/chipathon/scratch/opamp_ac.dat")
# ngspice wrdata format: frequency vout_db ... (depends on number of vars)
# We have wrdata vout_db vout_phs → cols: freq mag freq phase (each var gets its own freq col)
arr = np.loadtxt(dat)
freq = arr[:, 0]
mag_db = arr[:, 1]
phase = arr[:, 3]

# unwrap phase
phase_unwrapped = np.unwrap(phase * np.pi / 180) * 180 / np.pi

fig, ax = plt.subplots(2, 1, figsize=(8, 7), sharex=True, constrained_layout=True)

ax[0].semilogx(freq, mag_db, lw=1.8, color="#1f77b4")
ax[0].axhline(0, color="k", lw=0.5, ls="--")
ax[0].axhline(53.51, color="#999", lw=0.7, ls=":", label="DC gain 53.5 dB")
ax[0].set_ylabel("|gain| (dB)")
ax[0].set_title("PromptAFE op-amp — SKY130 1.8 V, open-loop AC response")
ax[0].grid(which="both", alpha=0.3)
ax[0].legend()

ax[1].semilogx(freq, phase_unwrapped, lw=1.8, color="#d62728")
ax[1].axhline(-180, color="k", lw=0.5, ls="--")
ax[1].axhline(-180 + 65.22, color="#999", lw=0.7, ls=":",
              label="PM = 65.2° at UGB 4.30 MHz")
ax[1].axvline(4.30e6, color="#999", lw=0.7, ls=":")
ax[1].set_xlabel("frequency (Hz)")
ax[1].set_ylabel("phase (°)")
ax[1].grid(which="both", alpha=0.3)
ax[1].legend()

out = Path("/opt/chipathon/scratch/opamp_bode.png")
fig.savefig(out, dpi=140)
print(f"wrote {out}")
