# AFE layout — current status

## What's in this directory

```
layout/
├── LAYOUT_STATUS.md              this file
├── afe_floorplan.py              gdstk floorplan generator
├── afe_floorplan.gds             system-level die outline + block placement
├── afe_floorplan.png             klayout render of the floorplan
├── gen_transistors.tcl           Magic Tcl — generates each GF180 transistor PCell
├── compose_opamp.py              Python — composes transistors into top-level op-amp GDS
├── opamp_layout.tcl              Magic-only attempt (left for reference; edit-cell bug)
├── opamp_2stage_layout.gds       **op-amp transistor-level GDS (588 KB, 7 transistors)**
├── opamp_2stage_layout.png       klayout render (bbox only — needs .lyp for layer colors)
├── run_layout.sh                 one-shot runner
└── test_pcell.tcl                minimal single-transistor test (proves the PCell flow)
```

## What's done at the layout level

| | Status |
|---|---|
| GF180 PCell generation via Magic gencell | ✅ working |
| Single-transistor GDS files (m1..m7) | ✅ generated (54–164 KB each, real geometry) |
| Top-level op-amp GDS with all 7 transistors placed | ✅ 588 KB |
| Common-centroid pair placement for matching | ⏭ next iteration |
| Inter-transistor routing (poly, metal1, metal2) | ❌ **not yet** |
| Power rails (VDD, VSS) | ❌ **not yet** |
| Miller compensation cap (MIM) | ❌ placeholder only |
| Substrate / well contacts + guard rings | ❌ not yet |
| DRC clean | partial — each transistor is internally clean (gencell guarantees it); top-level needs routing first |
| LVS clean | ❌ blocked on routing |
| PEX (parasitics extraction) | ❌ blocked on LVS |
| Post-layout simulation | ❌ blocked on PEX + GF180 ngspice fix |

## How to reproduce

On a machine with the IIC-OSIC tools docker image:

```bash
# Step 1 — generate each transistor as a standalone GDS
docker run --rm -v $PWD:/scratch hpretl/iic-osic-tools:latest --skip bash -c '
    cd /scratch
    export PDK_ROOT=/foss/pdks
    magic -dnull -noconsole \
        -rcfile /foss/pdks/gf180mcuD/libs.tech/magic/gf180mcuD.magicrc \
        gen_transistors.tcl
'

# Step 2 — compose the op-amp top-level GDS
docker run --rm -v $PWD:/scratch hpretl/iic-osic-tools:latest --skip bash -c '
    cd /scratch
    python3 compose_opamp.py . opamp_2stage_layout.gds
'
```

## What's actually achieved

This is **transistor-level layout** of the op-amp, not a placeholder rectangle:
- 7 GF180MCU 5 V transistor instances with correct (W, L, m, nf) sizing
- Each transistor uses the GF180 `gf180mcu::*_draw` PCell which generates
  diffusion, poly, contacts, metal, and well/substrate ties per the foundry rules
- Composed into a single top-level GDS

What it is **not**:
- It is **not** a tape-out-ready chip yet — the transistors are placed but
  not electrically connected. The next layer of work routes power and
  signals between them.

## Day-by-day plan to tape-out-ready AFE

| Day | Block | Deliverable |
|---|---|---|
| 1 | Op-amp routing | Power rails, gate/drain/source nets, Miller cap connection — DRC clean |
| 2 | Op-amp LVS + iteration | LVS against `netlist/opamp_2stage.sp`; fix any topology mismatches |
| 3 | PGA layout | Poly-resistor ladder + switch pass-gates + op-amp instance |
| 4 | S/H layout | MIM sample cap + bottom-plate switches + non-overlap clock paths |
| 5 | Vref layout | Resistor stack + diode-stack reference |
| 6 | AFE top-level integration | Block placement + die-level routing + pad ring sketches |
| 7 | Top-level DRC + LVS clean | iterate until 0 errors |
| 8 | PEX + post-layout sim | OpenRCX → SPEF → SKY130 ngspice (GF180 ngspice in this image is broken) |
| 9 | Final pad ring + ESD | I/O pads, ESD diodes, sealing ring |
| 10 | Sign-off | Final DRC/LVS clean, final GDS exported |

That's **realistic effort for one analog designer**. This is craft work — each step is iterative and benefits from interactive visualization (which `klayout` provides in GUI mode but I can't drive headless without significantly more scaffolding).

## What I'd do next session

Pick up at Day 1 of the table above:
1. Define net names on the op-amp transistor terminals
2. Add metal1 power rails (VDD top, VSS bottom)
3. Route gate connections between M1 ↔ vinp, M2 ↔ vinn
4. Route diff-pair drains: M1.drain → M3.drain (= diode node d_l)
5. Route M2.drain → M4.drain → M6.gate (= node d_r)
6. Route stage-2 output: M6.drain + M7.drain (= vout)
7. Connect Miller cap between d_r and vout
8. Add substrate/well contacts + guard ring around the diff pair

Each of those is ~15–30 min of careful Tcl in Magic. Then DRC + LVS iteration. Real but tractable.
