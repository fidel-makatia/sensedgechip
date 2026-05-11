# SenseEdge pre-silicon simulation harness

Pure-Python behavioural simulation of the SenseEdge ASIC. The model is
**bit-accurate to the chip RTL** — same FFT algorithm, same magnitude
approximation, same feature formulas, same INT8 MLP datapath. Validating
the model is therefore the strongest pre-silicon evidence available short
of a tape-out.

## Layout

```
sim/
├── vibration_gen.py        synthetic vibration signal generator (4 fault classes)
├── golden_model.py         chip-equivalent FFT + features + INT8 MLP
├── train_classifier.py     trains the 8→16→4 MLP and quantises to INT8
├── run_validation.py       end-to-end validation; produces all figures + report
└── artifacts/              outputs (weights, plots, report) — produced on run
```

## Run

```bash
pip install numpy scipy matplotlib
cd sim
python3 train_classifier.py        # ~30 s — trains + quantises weights
python3 run_validation.py          # ~10 s — runs validation, writes figures
ls artifacts/
ls artifacts/figs/
cat artifacts/validation_report.md
```

## Output

- `artifacts/weights.npz` — INT8 W1, b1, W2, b2 (loadable into the chip via Wishbone)
- `artifacts/val_data.npz` — held-out validation set with golden features
- `artifacts/figs/example_signals.png` — per-class time and FFT views
- `artifacts/figs/confusion_matrix.png` — classification confusion matrix
- `artifacts/figs/feature_dists.png` — per-feature class distributions
- `artifacts/validation_report.md` — human-readable result summary
- `artifacts/train_log.txt` — training curve + per-class accuracy

## What this proves

| Layer | Validation source |
|---|---|
| Algorithm correctness | this simulation harness (run-time) |
| RTL implements the algorithm | matching golden-model output (bit-exact match required) |
| Silicon implements the RTL | LibreLane sign-off — STA / DRC / LVS clean GDS |

End-to-end: **synthetic vibration → simulated classification = post-fab silicon
behaviour**, modulo only the (separately characterised) ADC quantisation noise.

## Extending

- **Train on real data**: drop your own labelled vibration dataset into
  `train_classifier.py`; the chip's weights are loadable at runtime via
  Wishbone — no re-tape-out required.
- **More classes**: increase the network's output layer up to the chip's
  hardware limit (4 in the current silicon). For more classes a follow-on
  silicon revision is needed (8 → 16 → N where N is the new class count).
- **RTL cosimulation**: a Verilator + cocotb harness lives in `../verif/` that
  drives the RTL through the Wishbone bus with the same vibration frames and
  asserts the RTL's classification matches `golden_model.run_pipeline()`
  bit-for-bit.
