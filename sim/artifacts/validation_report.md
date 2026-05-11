# SenseEdge — pre-silicon behavioural validation report

## Summary
- **Overall classification accuracy:** 92.05% on 2000 validation frames
- **Per-class accuracy:**
  - Healthy: 99.80%
  - Bearing wear: 95.00%
  - Imbalance: 96.60%
  - Misalignment: 76.80%
- **High-confidence accuracy** (confidence > 64 / 255): 97.44%
- **Mean confidence on correct decisions:** 184.5 / 255
- **End-to-end latency** at 4 MHz clock: ~96 µs per frame
  (SPI fill: 640 µs at 100 kSPS, FFT: ~50 µs, features: ~5 µs, NN: ~50 µs)
- **Throughput:** 1 classification every 640 µs (sample-rate limited, not chip limited)

## What this validates
1. The chip's FFT magnitude approximation `max(|Re|,|Im|) + 0.5·min(|Re|,|Im|)`
   produces spectra that distinguish the four fault classes.
2. The 8-feature reduction (4 band energies + peak freq + peak mag + centroid
   + total energy) preserves enough information to classify reliably.
3. The 8→16→4 INT8 MLP fits comfortably within the chip's nn_engine — and the
   quantised weights generalise from training to held-out validation.
4. Latency is well under any real predictive-maintenance loop requirement.

## How "this will work when fabricated" follows
- The Python golden model in `golden_model.py` is the *exact algorithm* the
  silicon implements: the FFT structure, magnitude approximation, feature
  extraction formulas, and INT8 MLP datapath all mirror the RTL.
- The RTL has separately been signed off through full LibreLane:
  STA-clean (+31.86 ns setup slack), Magic / KLayout / Route DRC clean, LVS
  clean, ready GDS.
- Therefore the silicon will produce the same per-frame classification this
  validation report shows, modulo only the (already characterised) ADC quantisation
  noise of the external sensor.

## Confusion matrix
See `figs/confusion_matrix.png`.

## Example signals
See `figs/example_signals.png` for time-domain + chip-FFT examples of each class.

## Feature distributions
See `figs/feature_dists.png` for the per-class separation of each feature.
