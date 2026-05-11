# sensedgechip — Open Modular Sensor-Node Platform on GF180MCU

A two-chiplet open-source IC platform for industrial predictive maintenance.

- **Digital chiplet (this repo, [`chip/`](chip/)):** complete vibration-analysis pipeline — FFT → features → on-die INT8 neural-network classifier → alarm. Fully signed off on GF180MCU 5LM. Clean GDS, DRC-clean, LVS-clean, timing closed at 4 MHz.
- **Analog chiplet (this repo, [`afe/`](afe/)):** programmable-gain amplifier + sample-and-hold + voltage reference. SPICE-validated topology with floorplan; transistor-level layout in progress.
- **Behavioral simulation (this repo, [`sim/`](sim/)):** Python golden model bit-accurate to the chip RTL. 92.05 % classification accuracy on synthetic 4-class fault dataset.

Submitted to **IEEE SSCS Chipathon 2026 — Track B (Circuits for Sensors)** as a chiplet-architected platform.

---

## Headline numbers

### Digital chiplet (`chip/`)

| Metric | Value |
|---|---|
| Process | GF180MCU 5LM, 9-track 5 V std cells |
| Die area | 9.00 mm² (3.0 × 3.0 mm) |
| Cell area | 8.84 mm² |
| Utilisation | 26.19 % |
| Cell instances | 265,015 |
| **Clock** | **4 MHz (250 ns)** |
| **Setup worst slack** | **+31.86 ns** ✅ |
| **Hold worst slack** | **+0.184 ns** ✅ |
| **LVS errors** | **0** ✅ |
| **DRC errors** (Magic + Route) | **0** ✅ |
| Wirelength | 5.13 m |
| Flow | LibreLane v3.0.2 Classic |

### Analog AFE chiplet (`afe/`)

| Block | Sim | Result |
|---|---|---|
| Op-amp (two-stage Miller) | AC | DC gain 53.5 dB · UGB 4.30 MHz · PM 65.2° ✅ |
| PGA at max gain (×100) | AC | closed-loop gain 39.88 dB (target 40) ✅ |
| Sample-and-hold | Transient | 100 kSPS clean track-hold ✅ |
| Full chain | Transient | input → PGA × 100 → S/H staircase ✅ |

Target envelope: 0.595 mm² (700 × 850 µm) GF180MCU. Floorplan GDS present; transistor-level layout is the next milestone.

### Behavioral validation (`sim/`)

| Metric | Value |
|---|---|
| Overall classification accuracy (INT8) | **92.05 %** |
| Healthy / Bearing wear / Imbalance / Misalignment | 99.8 / 95.0 / 96.6 / 76.8 % |
| High-confidence (conf > 64/255) accuracy | 97.4 % |
| End-to-end inference latency | ≈ 96 µs |

---

## Architecture

```
       MEMS accelerometer
              │
              │ differential mV-class signal
              ▼
  ┌──────────────────────┐  BoW-Lite die-to-die  ┌────────────────────────┐
  │                      │ ◄────────────────────►│                        │
  │   AFE chiplet        │                       │   Digital chiplet      │
  │   (afe/)             │                       │   (chip/)              │
  │                      │   sampled ADC code    │                        │
  │  - PGA  (0..40 dB)   │ ─────────────────────►│  - 64-pt radix-2 FFT   │
  │  - S/H  (100 kSPS)   │                       │  - feature extractor   │
  │  - Vref / bias       │ ◄────── PHI1, PHI1A ──│  - 8→16→4 INT8 NN      │
  │                      │ ◄────── GAIN_SEL[2:0] │  - alarm logic + IRQ   │
  │  GF180, 0.6 mm²      │                       │  GF180, 9 mm²          │
  │  (SPICE-validated)   │                       │  ✅ tape-out ready GDS  │
  └──────────────────────┘                       └────────────────────────┘
            │                                                │
            │              wire-bonded on shared PCBA        │
            └────────────────────────────────────────────────┘
                              │
                              ▼
                       4-class machine health output
                       Healthy / Bearing wear / Imbalance / Misalignment
```

---

## Repository layout

```
sensedgechip/
├── README.md                            this file
├── LICENSE                              Apache 2.0
├── chip/                                digital chiplet (GF180)
│   ├── CHIP.md                          datasheet-style chip description
│   ├── SUMMARY.md                       build log + final metrics
│   ├── metrics.json / metrics.csv       full sign-off metrics
│   ├── gds/senseedge_top.gds            84 MB — the chip
│   ├── lef/senseedge_top.lef            abstract for system integration
│   ├── lib/                             corner timing libraries
│   ├── render/senseedge_top.png         placed-and-routed visualization
│   └── openlane/
│       ├── config.json                  LibreLane configuration
│       └── launch.sh                    one-shot runner
├── sim/                                 behavioral validation
│   ├── README.md
│   ├── requirements.txt
│   ├── vibration_gen.py                 synthetic vibration generator (4 fault classes)
│   ├── golden_model.py                  bit-accurate chip pipeline in Python
│   ├── train_classifier.py              INT8 MLP training + quantisation
│   ├── run_validation.py                end-to-end validation + plots
│   └── artifacts/                       weights, validation set, results
└── afe/                                 analog companion chiplet
    ├── AFE_SPEC.md                      architecture + topology decisions
    ├── AFE_RESULTS.md                   simulation results + tape-out path
    ├── netlist/                         SPICE netlists for each block
    ├── sim/                             testbenches + plot scripts
    ├── plots/                           Bode, gain, S/H, chain plots
    └── layout/                          floorplan GDS (transistor-level WIP)
```

---

## Reproducing

### Behavioral validation (3 minutes, no special tools)

```bash
cd sim
pip install -r requirements.txt
python3 train_classifier.py        # ≈ 30 s — trains + quantises INT8 weights
python3 run_validation.py          # ≈ 10 s — runs validation, writes figures
cat artifacts/validation_report.md
```

### Digital chiplet re-synthesis (needs IIC-OSIC-TOOLS docker image)

```bash
docker pull hpretl/iic-osic-tools:latest
docker run --rm -v $PWD/chip:/foss/designs/sensedge \
  hpretl/iic-osic-tools:latest --skip \
  librelane --pdk-root /foss/pdks --skip Checker.YosysSynthChecks \
  /foss/designs/sensedge/openlane/config.json
```

The RTL is **not** included in this repo by default — see "Notes on prior work" below for how to wire it back in.

### AFE block-level SPICE (needs ngspice with SKY130 PDK)

```bash
cd afe/sim
ngspice -b tb_opamp_ac_sky130.sp
ngspice -b tb_pga_gain.sp
ngspice -b tb_sh_tran.sp
python3 plot_all.py
```

---

## Notes on prior work

The RTL for the digital pipeline (FFT, feature extractor, NN engine, alarm logic, Wishbone slave) is sourced from the open-source **SenseEdge** design originally developed by the author for the ChipFoundry shuttle program. The original repo ([github.com/fidel-makatia/senseedge-asic](https://github.com/fidel-makatia/senseedge-asic)) is licensed under Apache 2.0.

What's **new in this Chipathon submission** vs. the prior work:

| | Prior (senseedge-asic) | This (sensedgechip) |
|---|---|---|
| Process | SkyWater SKY130, Caravel user area | GF180MCU 5LM, standalone die |
| Standard cell library | sky130_fd_sc_hd | gf180mcu_fd_sc_mcu9t5v0 |
| Sign-off flow | OpenLane classic (SKY130) | LibreLane v3 (GF180) |
| Floorplan / pad ring | Caravel user-area constraint | independent 3 × 3 mm die |
| **Analog companion chiplet** | none | **PromptAFE — full SPICE design** |
| **Behavioral simulation** | none | **bit-accurate Python golden model, 92 % accuracy** |
| **Chiplet partition + interface** | none | **documented die-to-die spec** |
| Documentation | implementation-focused | datasheet + tape-out package |

This repository is built **on top of** the prior open-source RTL, not as a re-submission. The contributions are the GF180 port, the analog AFE chiplet, the chiplet-partition methodology, and the pre-silicon behavioral validation.

---

## License

Everything in this repository — RTL, GDS, netlists, SPICE simulations, Python, documentation — is released under the [Apache License 2.0](LICENSE).

The original SenseEdge RTL (`chip/rtl/*.v`, if you clone it from the upstream repo) is also Apache 2.0.

The GF180MCU PDK is owned by GlobalFoundries and released under Apache 2.0 via the open-source PDK distribution.

---

## Status

| | |
|---|---|
| Digital chiplet | ✅ tape-out-ready GDS (DRC/LVS clean, timing closed) |
| Behavioral validation | ✅ 92 % classification accuracy demonstrated |
| AFE topology | ✅ all blocks SPICE-validated |
| AFE layout | 🟡 floorplan only; transistor-level layout is the next step (~7–10 days) |
| Chiplet die-to-die interface | 🟡 documented in spec; SystemVerilog model TBD |
| End-to-end multi-chiplet sim | ❌ not yet — depends on D2D model |

**`AFE/AFE_RESULTS.md` has the honest scope for what's left to do to call the AFE tape-out-ready.**

---

## Acknowledgements

- IEEE SSCS Chipathon 2026 organising committee — Mehdi Saligane (chair, TC-OSE), Track B facilitators (Sadayuki Yoshitomi, Vipul Sharma, Rui Graça, Camilo Velez).
- The IIC-OSIC-TOOLS team for the containerised open-EDA stack.
- The LibreLane / OpenROAD / Yosys / KLayout / ngspice / gdstk open-source EDA ecosystems.
- The GlobalFoundries / Google open-PDK programs.
