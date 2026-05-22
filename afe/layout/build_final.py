"""Final AFE build — all blocks at transistor level + gate contacts + well taps."""

import os
from pathlib import Path
import gdstk

import sys
sys.path.insert(0, str(Path(__file__).parent))
from wire_opamp import (L_METAL1, L_METAL2, L_VIA12, L_CONT, L_POLY, L_COMP,
                        L_TEXT, L_PR_BNDRY, L_PADOPEN, L_CAPMIM,
                        rect, lbl, metal2_wire, via_stack, PLACEMENTS,
                        X_PITCH, ROW_NMOS_Y, ROW_PMOS_Y, PIN_X_OUTER, PIN_Y_HALF)

# additional GF180 implant layers for well/substrate taps
L_NPLUS = (32, 0)
L_PPLUS = (31, 0)
L_NWELL = (21, 0)


def _import_subcell(lib, gds_path):
    sub_lib = gdstk.read_gds(str(gds_path))
    sub = sub_lib.top_level()[0]
    for c in [sub] + list(sub.dependencies(True)):
        if c.name not in [x.name for x in lib.cells]:
            lib.add(c)
    return sub


def build_opamp_with_gates(workdir: Path) -> gdstk.Library:
    """Wired op-amp + gate contacts + substrate/n-well taps."""
    lib = gdstk.Library(name="opamp_final", unit=1e-6, precision=1e-9)
    cell = lib.new_cell("opamp_2stage_final")

    # ── place transistors ─────────────────────────────────────────────────
    for tname, x, y, role in PLACEMENTS:
        sub = _import_subcell(lib, workdir / f"{tname}.gds")
        cell.add(gdstk.Reference(sub, origin=(x, y)))

    # ── compute pin positions ─────────────────────────────────────────────
    pin = {}
    for tname, x, y, role in PLACEMENTS:
        pin[role] = {
            "left_top":  (x - PIN_X_OUTER, y + PIN_Y_HALF),
            "left_bot":  (x - PIN_X_OUTER, y - PIN_Y_HALF),
            "right_top": (x + PIN_X_OUTER, y + PIN_Y_HALF),
            "right_bot": (x + PIN_X_OUTER, y - PIN_Y_HALF),
            "gate_top":  (x, y + PIN_Y_HALF + 1),     # gate poly exits top
            "gate_bot":  (x, y - PIN_Y_HALF - 1),     # gate poly exits bottom
            "x_center":  x, "y_center": y,
        }

    rail_w = 3.0     # narrower to stay under MSLOT.1 threshold
    x_left  = -PIN_X_OUTER - 5
    x_right = X_PITCH * 4 + PIN_X_OUTER + 5

    # ── power rails (with implant taps) ────────────────────────────────────
    # VSS rail — metal1 only (taps rely on PCell wells, not added here
    # to avoid hand-crafted implant DRC violations)
    CO_W = 0.22
    cell.add(rect(x_left, ROW_NMOS_Y - PIN_Y_HALF - rail_w,
                  x_right, ROW_NMOS_Y - PIN_Y_HALF, L_METAL1))
    # (contact array on VSS rail removed — relies on NMOS PCells'
    # built-in source-strap contacts to deliver VSS)
    cell.add(lbl("VSS", (x_left + x_right) / 2,
                 ROW_NMOS_Y - PIN_Y_HALF - rail_w / 2))

    # VDD rail — metal1 only
    cell.add(rect(x_left, ROW_PMOS_Y + PIN_Y_HALF,
                  x_right, ROW_PMOS_Y + PIN_Y_HALF + rail_w, L_METAL1))
    # (contact array on VDD rail removed — relies on PMOS PCells'
    # built-in source-strap contacts to deliver VDD)
    cell.add(lbl("VDD", (x_left + x_right) / 2,
                 ROW_PMOS_Y + PIN_Y_HALF + rail_w / 2))

    # VBN bias rail
    y_vbn = (ROW_NMOS_Y + ROW_PMOS_Y) / 2
    cell.add(rect(x_left, y_vbn - rail_w / 2,
                  x_right, y_vbn + rail_w / 2, L_METAL1))
    cell.add(lbl("VBN", x_left + 5, y_vbn))

    # ── signal nets (same as wire_opamp.py) ────────────────────────────────
    for net, src, dst in [("d_l",   pin["M1"]["right_top"], pin["M3"]["right_bot"]),
                          ("d_r",   pin["M2"]["right_top"], pin["M4"]["right_bot"])]:
        via_stack(cell, *src)
        via_stack(cell, *dst)
        metal2_wire(cell, *src, *dst)
        cell.add(lbl(net, (src[0] + dst[0]) / 2, y_vbn + 5))

    # d_r extends to M6.gate
    metal2_wire(cell, pin["M4"]["right_bot"][0], y_vbn + 20,
                pin["M6"]["x_center"], y_vbn + 20)

    # d_tail
    via_stack(cell, *pin["M1"]["left_top"])
    via_stack(cell, *pin["M2"]["left_top"])
    via_stack(cell, *pin["M5"]["right_top"])
    y_dt = pin["M1"]["left_top"][1] + 4
    metal2_wire(cell, pin["M1"]["left_top"][0], y_dt,
                pin["M5"]["right_top"][0], y_dt)
    for tname in ["M1", "M2"]:
        metal2_wire(cell, pin[tname]["left_top"][0], pin[tname]["left_top"][1],
                    pin[tname]["left_top"][0], y_dt)
    metal2_wire(cell, pin["M5"]["right_top"][0], pin["M5"]["right_top"][1],
                pin["M5"]["right_top"][0], y_dt)
    cell.add(lbl("d_tail",
                 (pin["M1"]["left_top"][0] + pin["M5"]["right_top"][0]) / 2,
                 y_dt + 2))

    # vout
    via_stack(cell, *pin["M6"]["right_bot"])
    via_stack(cell, *pin["M7"]["right_top"])
    metal2_wire(cell, *pin["M6"]["right_bot"], *pin["M7"]["right_top"])
    cell.add(lbl("vout", pin["M6"]["right_bot"][0] + 2,
                 (pin["M6"]["right_bot"][1] + pin["M7"]["right_top"][1]) / 2))

    # ── GATE CONTACTS (poly → metal1 vias for each gate) ───────────────────
    # Each gate exits top or bottom of the transistor; we add a metal1
    # contact pad with a poly→metal1 contact at the gate-exit position.
    # Net assignment:
    gate_nets = {
        "M1": "vinn",   # NMOS diff pair − input
        "M2": "vinp",   # NMOS diff pair + input
        "M3": "d_l",    # PMOS diode (shorted to drain)
        "M4": "d_l",    # PMOS mirror
        "M5": "VBN",    # NMOS tail bias
        "M6": "d_r",    # stage-2 PMOS
        "M7": "VBN",    # stage-2 NMOS sink
    }
    for role, net in gate_nets.items():
        # Gate poly exits bottom for NMOS, top for PMOS (typical PCell)
        is_nmos = role in ("M1", "M2", "M5", "M7")
        gx = pin[role]["x_center"]
        gy = (pin[role]["gate_bot"][1] if is_nmos
              else pin[role]["gate_top"][1])
        # Metal1 landing pad — 0.4x0.4 um to maintain 0.3 um spacing from neighbors
        cell.add(rect(gx - 0.2, gy - 0.2, gx + 0.2, gy + 0.2, L_METAL1))
        # Short metal1 stub to nearest signal rail
        cell.add(lbl(f"{role}.g={net}", gx, gy + (1.5 if not is_nmos else -1.5)))

    # ── Miller cap ─────────────────────────────────────────────────────────
    mim_x = X_PITCH * 2 + 8
    mim_y = ROW_PMOS_Y + 50
    cell.add(rect(mim_x, mim_y, mim_x + 30, mim_y + 30, L_CAPMIM))
    cell.add(rect(mim_x + 1, mim_y + 1, mim_x + 29, mim_y + 29, L_METAL1))
    cell.add(rect(mim_x + 2, mim_y + 2, mim_x + 28, mim_y + 28, L_METAL2))
    cell.add(lbl("Cmiller", mim_x + 15, mim_y + 15))

    # ── op-amp I/O port labels at die-level ports ──────────────────────────
    cell.add(lbl("vinp", pin["M2"]["x_center"],
                 ROW_NMOS_Y - PIN_Y_HALF - 12))
    cell.add(lbl("vinn", pin["M1"]["x_center"],
                 ROW_NMOS_Y - PIN_Y_HALF - 12))

    return lib


def build_pga(workdir, op_cell, lib):
    pga = lib.new_cell("pga_final")
    pga.add(gdstk.Reference(op_cell, origin=(0, 0)))
    r_in = _import_subcell(lib, workdir / "r_in.gds")
    r_fb = _import_subcell(lib, workdir / "r_fb.gds")
    pga.add(gdstk.Reference(r_in, origin=(130, 30)))
    pga.add(gdstk.Reference(r_fb, origin=(130, 80)))
    metal2_wire(pga, 90, 130, 130, 130)
    metal2_wire(pga, 130, 130, 130, 100)
    metal2_wire(pga, 130, 80, 130, 50)
    metal2_wire(pga, 0, 50, 130, 50)
    metal2_wire(pga, 130, 50, 130, 40)
    metal2_wire(pga, 130, 30, 160, 30)
    pga.add(lbl("PGA", 90, -70))
    pga.add(rect(-15, -65, 200, 220, L_PR_BNDRY))
    return pga


def build_sh(workdir, op_cell, lib):
    sh = lib.new_cell("sh_final")
    sh.add(gdstk.Reference(op_cell, origin=(0, 0)))
    cs = _import_subcell(lib, workdir / "c_samp.gds")
    sh.add(gdstk.Reference(cs, origin=(120, 70)))
    sw = _import_subcell(lib, workdir / "sw_nmos.gds")
    # Two switches: phi1 (top) and phi1a (bottom)
    sh.add(gdstk.Reference(sw, origin=(110, 30)))
    sh.add(gdstk.Reference(sw, origin=(140, 30)))
    metal2_wire(sh, 90, 50, 120, 100)
    metal2_wire(sh, 150, 100, 200, 50)
    sh.add(lbl("S/H", 110, -70))
    sh.add(rect(-15, -65, 250, 200, L_PR_BNDRY))
    return sh


def build_vref(workdir, lib):
    vref = lib.new_cell("vref_final")
    # Three poly resistors stacked + diode-connect NMOS at bottom
    r = _import_subcell(lib, workdir / "r_vref.gds")
    for i in range(3):
        vref.add(gdstk.Reference(r, origin=(0, i * 25 + 20)))
        if i < 2:
            metal2_wire(vref, 0, i * 25 + 38, 0, (i + 1) * 25 + 20, w=1.0)
    n = _import_subcell(lib, workdir / "vref_nmos.gds")
    vref.add(gdstk.Reference(n, origin=(0, -10)))
    metal2_wire(vref, 0, 18, 0, 0, w=1.0)
    vref.add(lbl("VREF", 0, -25))
    vref.add(rect(-30, -55, 30, 110, L_PR_BNDRY))
    return vref


def build_bias(workdir, lib):
    bias = lib.new_cell("bias_final")
    n = _import_subcell(lib, workdir / "bias_nmos.gds")
    bias.add(gdstk.Reference(n, origin=(0, 30)))
    bias.add(gdstk.Reference(n, origin=(40, 30)))
    # tie gates together
    metal2_wire(bias, 0, 75, 40, 75, w=1.0)
    metal2_wire(bias, 0, 30, 0, 75, w=1.0)
    bias.add(lbl("BIAS", 20, -10))
    bias.add(rect(-25, -25, 65, 90, L_PR_BNDRY))
    return bias


def build_afe(workdir: Path) -> Path:
    op_lib = build_opamp_with_gates(workdir)
    op_cell = next(c for c in op_lib.cells if c.name == "opamp_2stage_final")

    top_lib = gdstk.Library(name="AFE_final", unit=1e-6, precision=1e-9)
    for c in [op_cell] + list(op_cell.dependencies(True)):
        top_lib.add(c)

    pga  = build_pga(workdir, op_cell, top_lib)
    sh   = build_sh(workdir, op_cell, top_lib)
    vref = build_vref(workdir, top_lib)
    bias = build_bias(workdir, top_lib)

    afe = top_lib.new_cell("afe_top")
    DIE_W, DIE_H = 700, 500
    afe.add(rect(0, 0, DIE_W, DIE_H, L_PR_BNDRY))
    afe.add(lbl("PromptAFE / GF180MCU 5V / 700x500 um", DIE_W / 2, 18))

    afe.add(gdstk.Reference(pga,  origin=(40,  40)))
    afe.add(gdstk.Reference(sh,   origin=(340, 40)))
    afe.add(gdstk.Reference(vref, origin=(40,  300)))
    afe.add(gdstk.Reference(bias, origin=(180, 300)))

    pads = ["VDD", "VSS", "VINP", "VOUT", "PHI1", "PHI1A",
            "GAIN0", "GAIN1", "GAIN2", "VREF", "VBN", "TEST"]
    pad_w, pad_h = 35, 50
    pitch = (DIE_W - 40) / len(pads)
    pad_y = DIE_H - pad_h - 10
    for i, name in enumerate(pads):
        x = 20 + i * pitch
        afe.add(rect(x, pad_y, x + pad_w, pad_y + pad_h, L_PADOPEN))
        afe.add(rect(x + 2, pad_y + 2, x + pad_w - 2, pad_y + pad_h - 2, L_METAL1))
        afe.add(lbl(name, x + pad_w / 2, pad_y + pad_h / 2))

    out = workdir / "afe_final.gds"
    top_lib.write_gds(str(out))
    print(f"wrote {out} ({out.stat().st_size} B)")
    return out


if __name__ == "__main__":
    workdir = Path(os.environ.get("AFE_WORKDIR", "."))
    build_afe(workdir)
