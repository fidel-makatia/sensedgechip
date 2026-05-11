# PromptAFE — Analog Front-End Chiplet for SenseEdge

A 5 V analog companion die that conditions a MEMS accelerometer (or similar low-level vibration sensor) and presents a clean, ADC-ready signal to the SenseEdge digital chiplet.

**Process:** GF180MCU 5LM, 5 V.
**Target area:** ≤ 0.6 mm² (≤ 700 × 850 µm core).
**Role in the modular sensor node:** the analog half. The SenseEdge digital chiplet does FFT / features / classification on the sampled output of this die.

---

## Functional block diagram

```
  IN+ ──╮                            ╭─ Vref (1.25 V bandgap)
  IN- ──┤                            │
        │   ┌──────────────┐         │   ┌──────────┐
        ╰──►│   Switched-  │   Vmid  ╰──►│   S/H    │── OUT
            │   Resistor   ├────────────►│  (track  │── (to ext. SAR ADC)
            │   PGA        │             │   /hold) │
            └──────────────┘             └──────────┘
                  ▲                            ▲
                  │                            │
              GAIN_SEL[2:0]            SAMPLE_CLK
              (3 bits, 8 levels)       (10–100 kHz)
                  │                            │
                  │                            │
                  ╰─────── BoW-Lite chiplet bus ╯
                            (from SenseEdge digital)
```

The interface to the digital chiplet is documented separately in
`CHIPLET_LINK.md`.

---

## Target specifications

| | Value | Notes |
|---|---|---|
| Supply (VDD) | 5.0 V ± 5 % | Single-supply, no charge pump |
| Quiescent current | < 800 µA total | Includes bias + PGA + S/H + bandgap |
| Input range (differential) | ±10 mV to ±1 V | Configurable via GAIN_SEL |
| Output range | 0.5 V – 4.5 V (rail-to-rail nearly) | Single-ended, to ext. SAR |
| Programmable gain | **0, 6, 12, 18, 24, 30, 36, 40 dB** (8 levels) | Switched poly-resistor feedback |
| -3 dB bandwidth | > 5 kHz at G = 40 dB | Plenty for vibration (<2 kHz) |
| Slew rate | > 0.5 V/µs | At gain ≤ 12 dB |
| Input-referred noise (10 Hz – 1 kHz) | < 200 nV/√Hz (target 100) | At G = 40 dB |
| CMRR @ DC | > 70 dB | Diff input topology limits |
| PSRR @ DC | > 60 dB | |
| THD @ 1 V_pp output, 1 kHz | < −60 dB | At gain ≤ 30 dB |
| S/H sample rate | 10 – 100 kSPS | SAMPLE_CLK from digital chiplet |
| S/H aperture jitter | < 5 ns | At 100 kSPS |
| S/H droop rate | < 5 mV / ms (worst case) | Acquisition cap + leakage |
| Temperature range | -40 °C to +125 °C | Industrial / automotive |

These are first-tape-out targets, comfortably inside what GF180 5 V analog
practice can hit with conservative sizing.

---

## Topology decisions

### 1. PGA — single-op-amp switched-resistor feedback

| Option | Pros | Cons | Decision |
|---|---|---|---|
| 3-op-amp instrumentation amp | best CMRR (>100 dB), classic | 3× op-amp area, more current | rejected |
| **Single-op-amp switched-R PGA** | minimal area, fewer pins | CMRR depends on R-matching | **chosen** |
| Switched-cap PGA | true DC accuracy, low offset | needs non-overlapping clocks, kT/C noise | deferred to v2 |

The switched-resistor topology hits the application bandwidth (5 kHz) easily
on a single 2-stage op-amp. CMRR target (70 dB) is achievable with matched
poly resistor pairs in a common-centroid layout.

### 2. Op-amp — two-stage Miller compensated

Classic textbook topology, very well-characterised on GF180 5V:

- **Stage 1:** NMOS differential pair (M1, M2) with PMOS current-mirror load (M3, M4), tail current source M5
- **Stage 2:** Common-source PMOS (M6) with NMOS current source load (M7)
- **Compensation:** Miller capacitor Cc between gate and drain of M6, with optional series nulling resistor Rz to push the right-half-plane zero into the left half plane (or eliminate it)

Target performance for the op-amp alone:
- DC open-loop gain: > 70 dB
- Unity-gain BW: > 5 MHz at C_load = 5 pF
- Phase margin: > 60 ° at PGA's lowest closed-loop gain (×1)
- Slew rate: > 5 V/µs

### 3. S/H — bottom-plate sampled capacitor

| Option | Pros | Cons | Decision |
|---|---|---|---|
| Top-plate sampling | simpler | clock feedthrough degrades SNR | rejected |
| **Bottom-plate sampling** | charge-injection cancelled by timing | needs Φ1 and Φ1a non-overlap | **chosen** |
| Flip-around S/H | full-range out, no buffer needed | only useful if differential out | not needed (single-ended out) |

10 pF sampling cap on MIM. Φ1 ≥ 1 µs for full settling at 100 kSPS. Φ1a
opens slightly before Φ1 to break the input path before injection.

### 4. Voltage reference — simple bandgap

5 V GF180 supports a textbook Brokaw or Banba bandgap. Target: 1.25 V ± 1 %
across PVT. Used to bias the PGA mid-rail and to provide Vref to the
external ADC.

---

## Why this AFE specifically

This is the smallest credible analog chiplet that solves the *real* SenseEdge
problem: industrial MEMS accelerometers produce millivolt-level signals that
must be conditioned, amplified, and held for a SAR ADC. Without this, the
digital chiplet has nothing useful to FFT. With it, you have a complete
sensor-node platform on two open-source GF180 dies.

**On Track B's "chiplet integration" bullet:** this die is the analog
chiplet in a documented partition; the SenseEdge die is the DSP/ML chiplet.
The same wire-bond shuttle slot can host both.

**On Track D's "AI-assisted circuits":** this same circuit is the worked
example of the PromptAFE agentic flow — a 70B analog-specialist LLM (distilled
from Claude Opus traces) iteratively designs the topology, sizes the
transistors, runs ngspice, and refines until specs close. The methodology is
the headline contribution; this circuit is the proof.

---

## Open questions to resolve at kickoff

- Shuttle slot share: can two dies (digital + analog) share one
  Chipathon-2026 shuttle position, or do they need separate slots?
- Co-tape-out pad-ring constraints: are pads pooled across both dies on the
  shuttle die, or independent?
- Floor-plan template: is there a chair-recommended cell-grid template for
  GF180 analog blocks like this AFE?

---

## File layout (planned)

```
afe/
├── AFE_SPEC.md                    this document
├── netlist/
│   ├── opamp_2stage.sp            op-amp transistor-level netlist
│   ├── pga_switched_r.sp          PGA wrapper with feedback resistor network
│   ├── sh_bottom_plate.sp         S/H with non-overlapping phase generation
│   ├── bandgap_brokaw.sp          bandgap reference
│   └── afe_top.sp                 top-level connecting all of the above
├── sim/
│   ├── tb_opamp_ac.sp             AC response, phase margin, UGB
│   ├── tb_opamp_tran.sp           slew rate, settling
│   ├── tb_opamp_noise.sp          input-referred noise
│   ├── tb_pga_gain.sp             gain step response across GAIN_SEL
│   ├── tb_pga_thd.sp              THD at full-scale
│   ├── tb_sh_aperture.sp          S/H aperture jitter, droop
│   └── run_all.py                 orchestrator + plot generator
├── plots/                         output PNGs from sim/run_all.py
├── layout/                        magic / gLayout outputs (later)
└── CHIPLET_LINK.md                die-to-die interface spec (separate)
```
