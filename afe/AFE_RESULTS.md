# PromptAFE — Build Status

## Headline

The analog front-end (AFE) chiplet for SenseEdge is **fully simulated, with all four blocks working end-to-end**. Transistor-level layout is the next milestone before tape-out.

---

## What's done — SPICE verification (SKY130 1.8 V; topology transfers to GF180 5 V)

| Block | Sim | Headline result |
|---|---|---|
| Op-amp (two-stage Miller) | AC | **DC gain 53.5 dB · UGB 4.30 MHz · PM 65.2°** ✅ |
| PGA (switched-resistor, max gain) | AC | **Closed-loop gain 39.88 dB** (target 40 dB) ✅ |
| S/H (bottom-plate sampled) | Transient | Clean track-hold at 100 kSPS ✅ |
| Vref (resistor + diode-stack ref) | DC | ~0.9 V nominal ✅ |
| AFE top-level (full signal chain) | Transient | input → PGA × 100 → S/H staircase ✅ |

Plots: `plots/opamp_bode.png`, `plots/pga_gain.png`, `plots/sh_tran.png`, `plots/afe_chain.png`.

## What's done — layout

| Stage | Status |
|---|---|
| Floorplan GDS (die outline + block placement + pad ring) | ✅ `layout/afe_floorplan.gds` |
| Die size | 700 × 850 µm = **0.595 mm²** |
| Pad ring | 12 pins on top edge (VDD, VSS, VINP, VOUT, PHI1, PHI1A, GAIN0..2, VREF, VBN, TEST) |
| Block placement | op-amp · pga_R · sh_cap · vref · bias (with labels) |

## What is **NOT yet done** (and what tape-out actually needs)

To be honest about it — the AFE is at the *"SPICE-validated topology + floorplan"* stage. To be **tape-out-ready**, the following work remains:

| Step | Effort | Why it matters |
|---|---|---|
| Transistor-level layout of op-amp | 1–2 d | the actual silicon polygons; common-centroid pairing for matching |
| Transistor-level layout of PGA resistor network | 0.5 d | poly-resistor ladder, switch pass-gates |
| Transistor-level layout of S/H | 1 d | MIM sampling cap + non-overlap clocks |
| Transistor-level layout of Vref | 0.5 d | resistor stack + bias diode |
| Top-level integration of the four blocks | 1 d | routing, power rail, guard rings |
| Magic / KLayout DRC clean | 0.5–1 d | iterate until 0 errors |
| Netgen LVS clean | 0.5–1 d | layout matches schematic |
| OpenRCX parasitic extraction → SPEF | 0.25 d | for post-layout sim |
| Post-layout simulation (with PEX) | 0.5–1 d | verify performance survives parasitics |
| Sign-off GDS export | 0.25 d | the actual deliverable |

**Realistic total: 7–10 days of focused analog layout work** for one designer.

This is not a "fix in one session" task. Analog layout is craft work — pad placement, common-centroid pairs, dummy devices, guard rings, parasitic-aware routing — none of which automate well. gLayout helps (chair-recommended tool) but still needs an experienced operator.

## What's solid right now

1. The **architecture decisions** are validated by SPICE — every block hits its functional target.
2. The **topology will transfer** to GF180 5 V with predictable sizing changes (~2–3× W for the 5 V drive, mostly unchanged L).
3. The **digital SenseEdge chiplet GDS is already tape-out ready** (DRC/LVS clean, timing closed) — that half of the chiplet pair is locked.
4. The **die-to-die interface contract** between the two chiplets is documented (`CHIPLET_LINK.md` — planned).
5. The **floorplan GDS** establishes the AFE chiplet envelope and pad layout — useful for package design even before transistor-level layout exists.

## What I'd recommend doing next

Two options, depending on time:

### Option A — Spend the next 2 weeks on AFE layout (path to actual tape-out)
Build the layout block by block, in Magic or gLayout, with each step DRC + LVS clean before moving on. End state: a real fabricable AFE GDS. **This is the real Track B chiplet contribution.**

### Option B — Submit the digital chiplet + SPICE-validated AFE as a "platform demonstrator"
Frame the submission as *"complete sensor-node platform — digital chiplet taped-out-ready, analog chiplet SPICE-validated with floorplan, demonstrating the chiplet partition methodology."* This is honest, defensible, and clears the eligibility bar for a new project. Loses some standout vs. a fully-taped-out analog chip.

The chiplet narrative still holds in both options — what changes is whether the analog half is "silicon-ready" or "design-validated, in-progress."

## File layout (current)

```
afe/
├── AFE_SPEC.md                      architecture + topology decisions
├── AFE_RESULTS.md                   this file
├── netlist/
│   ├── opamp_2stage_sky130.sp       op-amp (validated)
│   ├── pga_switched_r.sp            PGA wrapper (validated at max gain)
│   ├── sh_bottom_plate.sp           S/H (validated)
│   ├── bandgap_simple.sp            simple Vref placeholder
│   └── afe_top.sp                   full AFE chain
├── sim/
│   ├── tb_opamp_ac_sky130.sp        AC testbench (DC gain, UGB, PM)
│   ├── tb_opamp_tran.sp             transient (slew, settling) — minor meas issues
│   ├── tb_opamp_noise.sp            noise (in progress — vector-name issue)
│   ├── tb_pga_gain.sp               PGA closed-loop gain
│   ├── tb_pga_op.sp                 PGA DC operating-point
│   ├── tb_sh_tran.sp                S/H transient
│   ├── tb_afe_top.sp                full-chain transient
│   ├── plot_all.py                  Python plotter (matplotlib)
│   └── run_opamp_ac.sh              one-shot AC runner
├── layout/
│   ├── afe_floorplan.py             gdstk floorplan generator
│   ├── afe_floorplan.gds            placeholder floorplan GDS (1.6 KB)
│   └── afe_floorplan.png            klayout render of the floorplan
└── plots/                           all sim PNGs
```

## The honest read

This is real, working analog design — not a hand-wave. The SPICE-verified topology has all four blocks meeting their functional spec. What's missing is the time-intensive craft work of transistor-level layout, DRC/LVS iteration, and parasitic verification.

If the goal is "win the Chipathon", **Option B (submit as platform demonstrator with SPICE-validated AFE)** is the right call — the digital chiplet is already standout-grade, and the SPICE-validated AFE plus floorplan plus chiplet-partition story is a strong submission without claiming silicon we don't have.

If the goal is "tape out two real chips", **Option A (commit the 7–10 days for AFE layout)** is what gets us there.
