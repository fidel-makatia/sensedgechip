# SenseEdge — Predictive-Maintenance ASIC on GF180MCU

A complete vibration-analysis system-on-chip. Raw accelerometer samples enter over SPI; a machine-health classification comes out a few hundred microseconds later. No external DSP, no MCU compute, no cloud.

---

## What it does

The chip is a **fully-integrated vibration signal-processing pipeline** designed for industrial predictive maintenance — motors, pumps, compressors, bearings, fans. It ingests a stream of ADC samples representing mechanical vibration, transforms them into a frequency-domain representation, distils that into a handful of physically-meaningful features, and classifies the underlying machine state with a small on-die neural network.

**The classification result drives an on-chip alarm output directly** — there is no software in the loop. A bearing entering wear, an unbalanced rotor, or a shaft misalignment is detected and asserted on a GPIO pin within microseconds of the sample-window completing.

---

## Block diagram

```
                          ╭──────────────╮
              SPI in ────►│  SPI-ADC IF  │ ── 12-bit samples ──┐
            (≤100 kSPS)   ╰──────────────╯                      │
                                                                ▼
                                                       ╭───────────────╮
                                                       │  64-pt FFT    │
                                                       │  Radix-2 DIT  │
                                                       │  16-bit fixed │
                                                       ╰───────┬───────╯
                                                               │ 32 mag bins
                                                               ▼
                                                       ╭───────────────╮
                                                       │   Feature     │
                                                       │   Extractor   │
                                                       │  (8 features) │
                                                       ╰───────┬───────╯
                                                               │ 8 × INT8
                                                               ▼
                                                       ╭───────────────╮
                                                       │ NN classifier │
                                                       │  8→16→4 INT8  │
                                                       │  ReLU + arg-  │
                                                       │      max      │
                                                       ╰───────┬───────╯
                                                               │
       ╭──────────╮                                            │ class + conf
       │  Alarm   │◄───────────────────────────────────────────┘
       │  + IRQ   ├──► alarm GPIO out
       ╰────┬─────╯
            │
            ▼
   wb_dat   wbs_ack
    ◄──────────►   Wishbone B4 32-bit slave: configuration,
    wbs_adr        weight loading, FFT/feature readback,
    wbs_dat_i      result polling, IRQ ack
    wbs_we/sel/stb
```

---

## Signal-processing pipeline in detail

| Stage | Function | Output |
|---|---|---|
| **SPI-ADC interface** | Drives an external 12-bit SPI ADC (MCP3201-class). Configurable sample rate up to 100 kSPS via a programmable clock divider. Sign-extends samples to 16-bit and buffers them in a 64-sample circular memory. | 64 × 16-bit samples |
| **64-pt radix-2 FFT** | Decimation-in-time butterfly engine with bit-reversal input addressing. Pre-computed twiddle ROM in Q1.14 format. Single butterfly time-multiplexed across 6 stages × 32 butterflies. Fast magnitude approximation `max(\|Re\|,\|Im\|) + 0.5·min(\|Re\|,\|Im\|)`. | 32 × 16-bit magnitude bins (DC → Nyquist) |
| **Feature extractor** | Reduces the 32-bin spectrum to 8 physically-meaningful features: 4 band energies (low / mid-low / mid-high / high), peak frequency, peak magnitude, spectral centroid, total spectral energy. All normalised to INT8 for NN input. | 8 × 8-bit features |
| **NN inference engine** | Fully-connected MLP: 8 → 16 (ReLU) → 4 (arg-max). INT8 weights and activations. Single MAC time-multiplexed across 192 operations per inference. Weights are runtime-loadable through the Wishbone bus, so the same silicon can be re-trained on new fault taxonomies in the field without a re-tape-out. | 2-bit class ID + 8-bit confidence |
| **Alarm logic** | Configurable confidence threshold + a consecutive-fault counter (N consecutive faults → assert) to reject single-sample false positives. Single-cycle IRQ pulse to the host plus a level-held GPIO line for direct hardware alarms (LED, buzzer, contactor). | 1 GPIO + 1 IRQ |
| **Wishbone interface** | Standard 32-bit Wishbone B4 slave with a small register map for control, weight loading, readback of FFT bins and features, alarm configuration, and IRQ status. The host CPU configures the chip once and then only services IRQs. | Register-mapped control |

The four fault classes the trained network classifies are:

1. **Healthy** — within normal vibration signature
2. **Bearing wear** — characteristic ball-pass / inner-race / outer-race frequency content
3. **Rotor imbalance** — strong fundamental at running speed
4. **Shaft misalignment** — second-harmonic content elevated vs. fundamental

The classifier is intentionally small and re-trainable. The full architecture is documented in the verification material so a user can train against their own equipment population.

---

## Specifications

| | |
|---|---|
| **Process** | GlobalFoundries 180 nm (GF180MCU 5LM), 5 V mixed-signal |
| **Standard cells** | `gf180mcu_fd_sc_mcu9t5v0` (9-track, 5 V) |
| **Die area** | 9.00 mm² (3.0 mm × 3.0 mm) |
| **Cell area** | 8.84 mm² |
| **Utilisation** | 26.2 % |
| **Cell count** | 265,015 instances |
| **Clock** | 4 MHz (250 ns period) |
| **Setup slack** | +31.86 ns (12.7 % margin) |
| **Hold slack** | +0.184 ns |
| **DRC** | clean (Magic + KLayout + Route) |
| **LVS** | clean (Netgen, 0 errors) |
| **Routing layers** | Metal1–Metal4 signal, Metal5 power |
| **Total wirelength** | 5.13 m |
| **Host interface** | 32-bit Wishbone B4 slave + SPI + GPIO |
| **External I/O** | SPI to ADC; alarm GPIO; status LED; IRQ |
| **Power supplies** | 5 V core / 5 V I/O (single-supply digital section) |
| **Inference latency** | < 100 µs end-to-end (sample-window complete → class out) |
| **Field re-training** | Yes — weights are loadable at runtime |
| **License** | Apache 2.0 (RTL + GDS + reports) |

---

## Target applications

| Sector | Use case |
|---|---|
| **Industrial manufacturing** | Motor / pump / compressor health on factory floors; condition-based maintenance |
| **HVAC** | Fan / blower / compressor monitoring in commercial buildings |
| **Energy** | Wind-turbine gearbox and generator monitoring |
| **Water & wastewater** | Pump-station bearing and cavitation diagnostics |
| **Agriculture** | Irrigation pumps, grain dryers, feed-conveyor motors |
| **Structural health** | Bridge, building, civil infrastructure vibration analysis |
| **Rotating equipment** | Turbines, generators, machine-tool spindles |

In every one of these settings the alternative is either an analog threshold detector (false-positive prone, no fault classification) or a microcontroller running a software FFT (high power, slow, bulky). This chip does both jobs in a single die, at a node and supply voltage that survives industrial environments.

---

## Is the die size acceptable?

**Yes — and intentionally so for the technology and application.**

### Context

| Reference design | Die size | Node |
|---|---|---|
| **This chip** | **9.0 mm² (3.0 × 3.0 mm)** | **GF180MCU 180 nm** |
| Chipathon 2025 Track B reference (magnetic-sensor microrobot system) | 9.0 mm² (3.0 × 3.0 mm) | GF180MCU 180 nm |
| Typical Chipathon shuttle slot | 9–25 mm² | GF180 / SKY130 |
| Commercial analog vibration detector (e.g. ADXL372-class) | ~2–3 mm² | 350 nm BCD |
| MCU + DSP combo for vibration analysis | 20–50 mm² across two dies | 130–180 nm |

9.0 mm² lines up exactly with the **canonical 3 × 3 mm GF180 Chipathon shuttle slot** — the same envelope as the 2025 Track B reference design. This is a deliberate target: it gives the design a clean single-slot footprint on the shared MPC shuttle, which is the path of least friction for first silicon.

### Why the area is what it is

The dominant consumers of die area are not the obvious blocks:

- **FFT working memory and NN weights are implemented as flop-array memories**, not compiled SRAM macros. This was a deliberate choice for the first silicon: flop arrays are PDK-portable, simulation-friendly, and avoid the open-source-SRAM macro-characterisation rabbit hole. They are also ~3× larger than equivalent SRAM macros.
- **The 9-track standard cell library** is used in place of the 7-track variant. The 9-track cells have larger pin shapes that route reliably on GF180's metal stack — the 7-track lib hits DRT-1231 access-point failures during detailed routing. The trade-off is ~25 % cell-area inflation versus the smaller library.
- **Utilisation is held to 26 %.** A higher utilisation (50–60 %) would shrink the die toward 4.5 mm², but at 180 nm with the routing-grid constraints above, looser placement gives reliable closure and clean DRC on the first physical run.

There is **a clear path to ~3 mm² in a follow-on revision** by (a) replacing the flop arrays with OpenRAM-generated SRAM macros, (b) shrinking the FFT working memory through in-place butterflies, and (c) increasing utilisation now that closure is proven. The current 9 mm² is the right number for a first-tape-out demonstrator on a Chipathon shuttle, not a production part.

---

## Is this competitive?

**Yes, for the application class and the open-source IC-design context. With caveats.**

### Where it wins

| | This chip | Commercial alternatives |
|---|---|---|
| **Full pipeline on a single die** | ✅ ADC IF → FFT → features → NN → alarm | ❌ requires accelerometer + MCU + DSP library |
| **Hardware-accelerated FFT** | ✅ dedicated radix-2 engine | ❌ software FFT on MCU, much slower |
| **On-die ML classification** | ✅ INT8 NN with field-loadable weights | ❌ rare; cloud or MCU inference common |
| **No software in the alarm path** | ✅ hardware GPIO assertion | ❌ MCU has to be alive |
| **Field re-trainable** | ✅ weights via Wishbone | partial (firmware update typically) |
| **Open silicon, reproducible** | ✅ full Apache 2.0 RTL + GDS | ❌ proprietary |
| **Industrial robustness** | ✅ 5 V single-supply, 180 nm | depends; mixed |
| **BOM (volume target)** | ≤ $15 sensor node including PCBA | $100–$1,000+ for industrial-grade systems |

### Where it concedes

| | This chip | Modern process node |
|---|---|---|
| Area density | 9 mm² @ 180 nm | < 1 mm² @ 28 nm |
| Static power | acceptable @ 180 nm | 10× lower @ 28 nm |
| Max clock | 4 MHz signed-off | 50+ MHz feasible at advanced nodes |
| Memory density | flop arrays here | dense SRAM macros |

These are all consequences of the 180 nm node, which is the *intentional* design point: it is open, fabricatable, low-mask-cost, and survives industrial temperature and supply transient regimes that finer nodes do not. The chip is competing on **completeness of integration and openness**, not on transistor count.

### Compared to other Chipathon-class entries

Most Chipathon submissions are single-function blocks (ADCs, sensor frontends, single amplifiers, RF mixers). This chip is a **complete system** — front-end, transform, feature extraction, ML inference, alarm logic, and host interface — in one die. That breadth is rare in the open-IC community and is the strongest argument for the entry under Track B (Circuits for Sensors), which is explicitly looking for *in-sensor processing* and *edge intelligence / TinyML* at the system level.

---

## Verification & sign-off status

| Stage | Tool | Result |
|---|---|---|
| RTL synthesis | yosys 0.64 | clean |
| Static timing (setup) | OpenSTA | +31.86 ns slack, TNS = 0 |
| Static timing (hold) | OpenSTA | +0.184 ns slack, TNS = 0 |
| Detailed routing | OpenROAD `detailed_route` | 0 DRC errors |
| Physical DRC | Magic | 0 errors |
| Physical DRC | KLayout | 0 errors |
| Layout-versus-schematic | Netgen | 0 errors |
| Parasitic extraction | OpenRCX | extracted SPEF |
| Manufacturability | LibreLane signoff | reported |

The complete sign-off bundle — GDS, LEF, DEF, SPEF, multi-corner timing libraries, machine-readable metrics, and a render of the final placed-and-routed layout — is in the same directory as this document.

---

## Reproducing & viewing

The full LibreLane configuration and run reports are committed in this repository. To view the layout:

```bash
klayout senseedge_top.gds
```

A 105 KB rendered preview of the placed and routed die is at `render/senseedge_top.png`.
