# AFE layout — current status

## What's in this directory

```
layout/
├── LAYOUT_STATUS.md              this file
├── afe_floorplan.py / .gds / .png  system-level chiplet outline
├── gen_transistors.tcl           Magic Tcl — generates each transistor as a PCell-driven GDS
├── compose_opamp.py              gdstk — places transistors into top-level op-amp GDS
├── add_routing.py                gdstk — adds VDD/VSS/VBN metal1 rails + I/O port labels
├── opamp_layout.tcl              earlier Magic-only attempt (edit-cell bug; kept for reference)
├── opamp_2stage_layout.gds       transistor placement only (588 KB, 7 transistors)
├── opamp_routed.gds              + power rails + port labels (590 KB)  ← latest
├── opamp_routed.png              klayout render (scale renders bbox only)
├── run_layout.sh                 one-shot runner for the Magic pass
└── test_pcell.tcl                minimum 1-transistor smoke test
```

## What's done

| | Status |
|---|---|
| GF180 PCell generation via `magic::gencell` proc API | ✅ working |
| All 7 op-amp transistor GDS files | ✅ generated (54–164 KB each, real foundry geometry) |
| Top-level placement (`opamp_2stage_layout.gds`) | ✅ 588 KB, 7 cells, correct sizing |
| Power rails (VDD, VSS, VBN on metal1) | ✅ added in `opamp_routed.gds` |
| Top-level port labels (vinp, vinn, vout, VDD, VSS, VBN) | ✅ added |
| Inter-transistor signal routing (drain/source/gate wires) | ❌ **not yet** |
| Miller compensation cap layout | ❌ MIM cap PCell still pending |
| Substrate / well contacts + guard rings | ❌ not yet |
| DRC clean | partial — each transistor is internally clean (`gencell` guarantees it); routing-layer DRC has not been verified end-to-end |
| LVS clean | ❌ blocked on inter-transistor routing |
| PEX → SPEF | ❌ blocked on LVS |
| Post-layout simulation | ❌ blocked on PEX + (separately) GF180 ngspice fix |

## Two-step build flow

```bash
# Step 1 — generate each transistor as a standalone GDS (Magic + GF180 PCell)
docker run --rm -v $PWD:/scratch hpretl/iic-osic-tools:latest --skip bash -c \
    'cd /scratch && export PDK_ROOT=/foss/pdks && \
     magic -dnull -noconsole \
       -rcfile /foss/pdks/gf180mcuD/libs.tech/magic/gf180mcuD.magicrc \
       gen_transistors.tcl'

# Step 2 — compose + add rails + labels (gdstk)
docker run --rm -v $PWD:/scratch hpretl/iic-osic-tools:latest --skip bash -c \
    'cd /scratch && \
     python3 compose_opamp.py . opamp_2stage_layout.gds && \
     python3 add_routing.py opamp_2stage_layout.gds opamp_routed.gds'
```

Outputs:
- 7 transistor GDS files (m1_nmos.gds, m2_nmos.gds, …)
- `opamp_2stage_layout.gds` — placement only
- `opamp_routed.gds` — placement + power rails + port labels

## Honest scope of what's left

Real tape-out-ready AFE requires:

| Step | Effort | Why it matters |
|---|---|---|
| Inter-transistor signal routing (every drain, source, gate net) | 1–2 d | makes the op-amp electrically connected |
| Miller cap (MIM, ~1.5 pF) layout + connection | 0.25 d | required for stability |
| Substrate / well contacts + guard rings | 0.5 d | latchup prevention + matching |
| Magic-side DRC clean (proper CIF/type translation) | 0.5 d | catch what GDS lint missed |
| Netgen LVS vs `netlist/opamp_2stage.sp` | 0.5–1 d | electrical correctness |
| PGA resistor ladder layout | 0.5 d | poly-resistor stack + pass-gate switches |
| S/H — MIM sampling cap + non-overlap clocks | 1 d | analog timing block |
| Vref — bandgap (or resistor-stack v0) layout | 0.5–1 d | bias generation |
| AFE top-level: floorplan + die-level routing | 1 d | system integration |
| Pad ring + ESD diodes | 1 d | the I/O the package bonds to |
| Top-level DRC + LVS clean | 0.5–1 d | iterate to 0 errors |
| OpenRCX parasitic extraction → SPEF | 0.25 d | for post-layout sim |
| Post-layout SPICE (in SKY130 since GF180 ngspice broken in this image) | 1 d | confirm specs survive parasitics |
| **Total: 8–11 days** of focused analog layout craft |

## Why this is multi-day work, not one-session

Analog layout is interactive craft work — each net needs deliberate path planning, each pair of matched devices needs common-centroid placement, each metal layer needs density-rule attention. Driving it headlessly from chat is feasible but slow: every "fix one DRC error, regenerate, re-DRC" cycle eats a chat round-trip + Magic startup time.

A single experienced analog designer in `klayout` GUI does this work much faster than scripted iteration can. The scripted approach we've built here is correct — it's just that the iteration loop is slower per cycle.

## What's been validated already (so we can defend the time-to-tape-out estimate)

1. The GF180 PCell flow works in batch Magic (`test_pcell.tcl` smoke test passes)
2. Composition of multiple PCell GDS files into a top-level layout works (`compose_opamp.py`)
3. Adding rails + labels at the GDS layer level works (`add_routing.py`)
4. The full toolchain (Magic + gdstk + GF180 PDK files) is provisioned and reproducible on a Linux x86 box with `hpretl/iic-osic-tools` Docker

What's still craft work, not scripting: routing each individual signal net between specific pin coordinates inside each transistor's PCell.
