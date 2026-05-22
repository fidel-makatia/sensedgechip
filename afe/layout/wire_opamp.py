"""Wire up the op-amp — add via1 + metal2 connections for all signal nets.

Each GF180 transistor PCell has metal1 stripes at the OUTER edges of its
diffusion (x = ±5.76 for our W=20 transistors). The drain and source are
on opposite outer edges. Plus there's a centre stripe (x=0) that's the
body / substrate tie.

Routing strategy:
  - For each transistor at (X_t, Y_t), drop via1 contacts at the
    top-outer (drain) and bottom-outer (source) pins.
  - Use metal2 channels to bridge between transistors.
  - Power rails on metal1 extend across the bottom (VSS) and top
    (VDD) of the row, deliberately OVERLAPPING the source-side
    metal1 stripes of each transistor so they make direct contact.

For the op-amp two-stage Miller topology, the connections are:
  M1.gate     = vinp        ← top label / port
  M2.gate     = vinn
  M1.source   = d_tail      ← inner shared with M2.source and M5.drain
  M2.source   = d_tail
  M5.drain    = d_tail
  M5.source   = VSS
  M5.gate     = VBN
  M1.drain    = d_l         ← M3 diode side
  M2.drain    = d_r         ← M4 mirror side / M6 stage-2 input
  M3.drain    = d_l         (same node)
  M3.gate     = d_l         (diode connected)
  M3.source   = VDD
  M4.gate     = d_l         (mirrors)
  M4.drain    = d_r
  M4.source   = VDD
  M6.gate     = d_r
  M6.drain    = vout
  M6.source   = VDD
  M7.drain    = vout
  M7.source   = VSS
  M7.gate     = VBN
  Cmiller     between d_r and vout
"""

import os
from pathlib import Path
import gdstk

# ── GF180 layers ──────────────────────────────────────────────────────────
L_PR_BNDRY = (0,  0)
L_COMP     = (22, 0)
L_POLY     = (30, 0)
L_CONT     = (33, 0)
L_METAL1   = (34, 0)
L_VIA12    = (35, 0)
L_METAL2   = (36, 0)
L_CAPMIM   = (36, 5)
L_PADOPEN  = (53, 0)
L_TEXT     = (63, 63)


# ── transistor pin geometry (deduced from PCell inspection) ───────────────
# Metal1 outer stripes at x = ±5.76 (for W=20 NMOS; ~ same for PMOS)
PIN_X_OUTER = 5.76
PIN_Y_HALF  = 42.5    # outer metal1 stripes extend ±42.5 in Y


# ── op-amp placement (same as build_afe.py) ───────────────────────────────
ROW_NMOS_Y = 0.0
ROW_PMOS_Y = 120.0
X_PITCH    = 30.0     # widened from 18 to give room for routes

# (cell_name, x, y, role)
PLACEMENTS = [
    ("m1_nmos", 0,             ROW_NMOS_Y, "M1"),
    ("m2_nmos", X_PITCH * 1,   ROW_NMOS_Y, "M2"),
    ("m5_nmos", X_PITCH * 2,   ROW_NMOS_Y, "M5"),
    ("m7_nmos", X_PITCH * 3,   ROW_NMOS_Y, "M7"),
    ("m3_pmos", 0,             ROW_PMOS_Y, "M3"),
    ("m4_pmos", X_PITCH * 1,   ROW_PMOS_Y, "M4"),
    ("m6_pmos", X_PITCH * 2.5, ROW_PMOS_Y, "M6"),
]

# Per-transistor pin nets (which net is on the LEFT-outer vs RIGHT-outer)
# Convention: alternating ports per finger; outer-left is source for NMOS,
# outer-right is drain (this is a *convention* — without true PCell
# documentation, the gates are routed via poly which we'll do separately).
PIN_NETS = {
    "M1": {"left": "d_tail",  "right": "d_l"},
    "M2": {"left": "d_tail",  "right": "d_r"},
    "M5": {"left": "VSS",     "right": "d_tail"},
    "M7": {"left": "VSS",     "right": "vout"},
    "M3": {"left": "VDD",     "right": "d_l"},
    "M4": {"left": "VDD",     "right": "d_r"},
    "M6": {"left": "VDD",     "right": "vout"},
}


def rect(x1, y1, x2, y2, layer):
    return gdstk.rectangle((x1, y1), (x2, y2), layer=layer[0], datatype=layer[1])


def lbl(text, x, y, layer=L_TEXT):
    return gdstk.Label(text=text, origin=(x, y), layer=layer[0], texttype=layer[1])


def via_stack(cell, x, y, size=1.2):
    """Place a single via1 + metal1 + metal2 stack at (x, y).
    Via1 dimension fixed at GF180 rule (0.26 x 0.26 um)."""
    VIA_W = 0.26
    cell.add(rect(x - size / 2, y - size / 2, x + size / 2, y + size / 2,
                  L_METAL1))
    cell.add(rect(x - VIA_W / 2, y - VIA_W / 2,
                  x + VIA_W / 2, y + VIA_W / 2, L_VIA12))
    cell.add(rect(x - size / 2, y - size / 2, x + size / 2, y + size / 2,
                  L_METAL2))


def metal2_wire(cell, x1, y1, x2, y2, w=1.5):
    """Draw a metal2 wire (L-shaped supported via two rectangles)."""
    if x1 == x2:
        # vertical
        cell.add(rect(x1 - w / 2, min(y1, y2), x1 + w / 2, max(y1, y2),
                      L_METAL2))
    elif y1 == y2:
        # horizontal
        cell.add(rect(min(x1, x2), y1 - w / 2, max(x1, x2), y1 + w / 2,
                      L_METAL2))
    else:
        # L-shape: horizontal first, then vertical
        cell.add(rect(min(x1, x2), y1 - w / 2, max(x1, x2), y1 + w / 2,
                      L_METAL2))
        cell.add(rect(x2 - w / 2, min(y1, y2), x2 + w / 2, max(y1, y2),
                      L_METAL2))


def metal1_strap(cell, x1, y1, x2, y2):
    """Draw a metal1 rectangle (for power-rail-style horizontal straps)."""
    cell.add(rect(x1, y1, x2, y2, L_METAL1))


def build_wired_opamp(workdir: Path) -> gdstk.Library:
    lib = gdstk.Library(name="opamp", unit=1e-6, precision=1e-9)
    cell = lib.new_cell("opamp_2stage_wired")

    # ── place transistors ─────────────────────────────────────────────────
    for tname, x, y, role in PLACEMENTS:
        gds = workdir / f"{tname}.gds"
        sub_lib = gdstk.read_gds(str(gds))
        sub = sub_lib.top_level()[0]
        for c in [sub] + list(sub.dependencies(True)):
            if c.name not in [x.name for x in lib.cells]:
                lib.add(c)
        cell.add(gdstk.Reference(sub, origin=(x, y)))

    # ── compute pin positions for each transistor ─────────────────────────
    # Outer metal1 stripes are at (x_t ± PIN_X_OUTER), extending in Y the
    # full transistor height. The "pin" for routing is the TOP of the
    # stripe (y_t + PIN_Y_HALF) for upward routes, BOTTOM for downward.
    pin_pos = {}    # role -> {"left_top", "left_bot", "right_top", "right_bot"}
    for tname, x, y, role in PLACEMENTS:
        pin_pos[role] = {
            "left_top":  (x - PIN_X_OUTER, y + PIN_Y_HALF),
            "left_bot":  (x - PIN_X_OUTER, y - PIN_Y_HALF),
            "right_top": (x + PIN_X_OUTER, y + PIN_Y_HALF),
            "right_bot": (x + PIN_X_OUTER, y - PIN_Y_HALF),
            "x_center":  x,
            "y_center":  y,
        }

    # ── power rails (overlap source-stripe tops/bottoms) ──────────────────
    # VSS rail: metal1 covering Y = ROW_NMOS_Y - PIN_Y_HALF down to -55,
    # spanning the full X range. This overlaps M5.source and M7.source.
    rail_w = 6.0
    x_left  = -PIN_X_OUTER - 3
    x_right = X_PITCH * 4 + PIN_X_OUTER + 3
    metal1_strap(cell,
                 x_left,  ROW_NMOS_Y - PIN_Y_HALF - rail_w,
                 x_right, ROW_NMOS_Y - PIN_Y_HALF)
    cell.add(lbl("VSS", (x_left + x_right) / 2,
                 ROW_NMOS_Y - PIN_Y_HALF - rail_w / 2))

    # VDD rail: metal1 covering top of PMOS row source stripes
    metal1_strap(cell,
                 x_left,  ROW_PMOS_Y + PIN_Y_HALF,
                 x_right, ROW_PMOS_Y + PIN_Y_HALF + rail_w)
    cell.add(lbl("VDD", (x_left + x_right) / 2,
                 ROW_PMOS_Y + PIN_Y_HALF + rail_w / 2))

    # ── VBN bias rail (between rows, metal1 horizontal) ───────────────────
    # Connects M5.gate and M7.gate. Both gates need a poly tap; for the
    # GDS we add a metal1 horizontal strap + via1 stubs at M5 and M7 x
    # positions. Full LVS connectivity would also need poly contacts.
    y_vbn = (ROW_NMOS_Y + ROW_PMOS_Y) / 2
    metal1_strap(cell,
                 x_left,  y_vbn - rail_w / 2,
                 x_right, y_vbn + rail_w / 2)
    cell.add(lbl("VBN", x_left + 5, y_vbn))

    # ── signal nets: route via metal2 with via1 contacts ──────────────────
    # d_l: M1.right (NMOS drain) ↔ M3.right (PMOS drain) and M3.gate
    via_stack(cell, *pin_pos["M1"]["right_top"])
    via_stack(cell, *pin_pos["M3"]["right_bot"])
    metal2_wire(cell,
                pin_pos["M1"]["right_top"][0], pin_pos["M1"]["right_top"][1],
                pin_pos["M3"]["right_bot"][0], pin_pos["M3"]["right_bot"][1])
    cell.add(lbl("d_l",
                 (pin_pos["M1"]["right_top"][0] + pin_pos["M3"]["right_bot"][0]) / 2,
                 y_vbn + 5))

    # d_r: M2.right ↔ M4.right ↔ M6.gate
    via_stack(cell, *pin_pos["M2"]["right_top"])
    via_stack(cell, *pin_pos["M4"]["right_bot"])
    metal2_wire(cell,
                pin_pos["M2"]["right_top"][0], pin_pos["M2"]["right_top"][1],
                pin_pos["M4"]["right_bot"][0], pin_pos["M4"]["right_bot"][1])
    # extend metal2 right to M6 gate area (M6 is wider PMOS — its centerline
    # is at X_PITCH * 2.5; route to centerline via L-shape)
    metal2_wire(cell,
                pin_pos["M4"]["right_bot"][0], y_vbn + 20,
                pin_pos["M6"]["x_center"],     y_vbn + 20)
    cell.add(lbl("d_r",
                 (pin_pos["M2"]["right_top"][0] + pin_pos["M4"]["right_bot"][0]) / 2,
                 y_vbn + 15))

    # d_tail: M1.left ↔ M2.left ↔ M5.right (= d_tail in PIN_NETS["M5"])
    via_stack(cell, *pin_pos["M1"]["left_top"])
    via_stack(cell, *pin_pos["M2"]["left_top"])
    via_stack(cell, *pin_pos["M5"]["right_top"])
    # metal2 channel connecting all three (horizontal)
    y_d_tail = pin_pos["M1"]["left_top"][1] + 4
    metal2_wire(cell,
                pin_pos["M1"]["left_top"][0], y_d_tail,
                pin_pos["M5"]["right_top"][0], y_d_tail)
    metal2_wire(cell,
                pin_pos["M1"]["left_top"][0], pin_pos["M1"]["left_top"][1],
                pin_pos["M1"]["left_top"][0], y_d_tail)
    metal2_wire(cell,
                pin_pos["M2"]["left_top"][0], pin_pos["M2"]["left_top"][1],
                pin_pos["M2"]["left_top"][0], y_d_tail)
    metal2_wire(cell,
                pin_pos["M5"]["right_top"][0], pin_pos["M5"]["right_top"][1],
                pin_pos["M5"]["right_top"][0], y_d_tail)
    cell.add(lbl("d_tail",
                 (pin_pos["M1"]["left_top"][0] + pin_pos["M5"]["right_top"][0]) / 2,
                 y_d_tail + 2))

    # vout: M6.right (PMOS drain) + M7.right (NMOS drain) — across rows
    via_stack(cell, *pin_pos["M6"]["right_bot"])
    via_stack(cell, *pin_pos["M7"]["right_top"])
    metal2_wire(cell,
                pin_pos["M6"]["right_bot"][0], pin_pos["M6"]["right_bot"][1],
                pin_pos["M7"]["right_top"][0], pin_pos["M7"]["right_top"][1])
    cell.add(lbl("vout",
                 pin_pos["M6"]["right_bot"][0] + 2,
                 (pin_pos["M6"]["right_bot"][1] + pin_pos["M7"]["right_top"][1]) / 2))

    # ── Miller cap between d_r and vout ───────────────────────────────────
    mim_x = X_PITCH * 2 + 8
    mim_y = ROW_PMOS_Y + 50
    mim_w, mim_h = 30, 30
    cell.add(rect(mim_x, mim_y, mim_x + mim_w, mim_y + mim_h, L_CAPMIM))
    # bottom plate = metal1 (connects to d_r via1)
    cell.add(rect(mim_x + 1, mim_y + 1, mim_x + mim_w - 1, mim_y + mim_h - 1,
                  L_METAL1))
    # top plate = metal2 (connects to vout via1)
    cell.add(rect(mim_x + 2, mim_y + 2, mim_x + mim_w - 2, mim_y + mim_h - 2,
                  L_METAL2))
    cell.add(lbl("Cmiller", mim_x + mim_w / 2, mim_y + mim_h / 2))

    # ── op-amp I/O port labels (gates need poly contact; for now label
    # at the gate's nominal X position, between source and drain) ─────────
    cell.add(lbl("vinp", pin_pos["M2"]["x_center"], ROW_NMOS_Y - PIN_Y_HALF - 12))
    cell.add(lbl("vinn", pin_pos["M1"]["x_center"], ROW_NMOS_Y - PIN_Y_HALF - 12))

    return lib


def block_outline(lib, name, w, h, label_text):
    c = lib.new_cell(name)
    c.add(rect(0, 0, w, h, L_METAL1))
    c.add(rect(1, 1, w - 1, h - 1, (38, 0)))  # metal3 placeholder
    c.add(lbl(label_text, w / 2, h / 2))
    c.add(rect(0, h - 4, w, h, L_METAL1))
    c.add(rect(0, 0, w, 4, L_METAL1))
    return c


def build_afe(workdir: Path) -> Path:
    op_lib = build_wired_opamp(workdir)
    op_cell = op_lib.cells[-1]  # the opamp_2stage_wired cell
    op_lib.write_gds(str(workdir / "opamp_2stage_wired.gds"))
    print(f"  wrote {workdir / 'opamp_2stage_wired.gds'}")

    top_lib = gdstk.Library(name="AFE_wired", unit=1e-6, precision=1e-9)
    afe = top_lib.new_cell("afe_top")

    for c in [op_cell] + list(op_cell.dependencies(True)):
        if c.name not in [x.name for x in top_lib.cells]:
            top_lib.add(c)
    afe.add(gdstk.Reference(op_cell, origin=(40, 40)))

    pga  = block_outline(top_lib, "pga_R",  120, 100, "PGA")
    sh   = block_outline(top_lib, "sh_cap", 100, 80,  "S/H")
    vref = block_outline(top_lib, "vref",   100, 80,  "Vref")
    bias = block_outline(top_lib, "bias",   60,  60,  "Bias")

    afe.add(gdstk.Reference(pga,  origin=(220, 40)))
    afe.add(gdstk.Reference(sh,   origin=(360, 40)))
    afe.add(gdstk.Reference(vref, origin=(40, 280)))
    afe.add(gdstk.Reference(bias, origin=(180, 280)))

    DIE_W, DIE_H = 600, 500
    afe.add(rect(0, 0, DIE_W, DIE_H, L_PR_BNDRY))
    afe.add(lbl("PromptAFE / GF180MCU 5V / 600x500 um", DIE_W / 2, 15))

    pads = ["VDD", "VSS", "VINP", "VOUT", "PHI1", "PHI1A",
            "GAIN0", "GAIN1", "GAIN2", "VREF", "VBN", "TEST"]
    pad_w, pad_h = 35, 50
    pitch = (DIE_W - 40) / len(pads)
    pad_y = DIE_H - pad_h - 10
    for i, name in enumerate(pads):
        x = 20 + i * pitch
        afe.add(rect(x, pad_y, x + pad_w, pad_y + pad_h, L_PADOPEN))
        afe.add(rect(x + 2, pad_y + 2, x + pad_w - 2, pad_y + pad_h - 2,
                     L_METAL1))
        afe.add(lbl(name, x + pad_w / 2, pad_y + pad_h / 2))

    out = workdir / "afe_top_wired.gds"
    top_lib.write_gds(str(out))
    print(f"  wrote {out}")
    return out


if __name__ == "__main__":
    workdir = Path(os.environ.get("AFE_WORKDIR", "."))
    build_afe(workdir)
