"""Build the full AFE chiplet GDS.

Composes the op-amp (transistor PCells + Miller cap), placeholder layouts
for PGA / S/H / Vref blocks, and an AFE top-level die with pad ring.

Strategy:
  - Op-amp: read each transistor's GDS, place with proper spacing
    (Y gap large enough to avoid bbox overlap), add metal1 power rails,
    metal2 routing channels between drains, metal1 port labels.
  - Miller cap: a MIM-cap-sized metal-stack rectangle (placeholder
    geometry; real MIM PCell would replace this).
  - PGA: rectangle block on its own metal layer with port labels —
    real resistor ladder is the next-iteration work.
  - S/H: rectangle block (MIM cap placeholder + switch ports).
  - Vref: rectangle block (resistor stack placeholder).
  - AFE top: composes the four blocks side by side with a pad-ring
    outline around the perimeter and labelled pads on the top edge.

Output: afe_top.gds — the full AFE chiplet, suitable as a Chipathon
submission artifact alongside the SPICE-validated netlists.
"""

from pathlib import Path
import gdstk
import os

# ── GF180 layer numbers (open-pdks) ────────────────────────────────────────
L_COMP      = (22, 0)     # active diffusion
L_POLY      = (30, 0)
L_CONT      = (33, 0)
L_METAL1    = (34, 0)
L_VIA12     = (35, 0)
L_METAL2    = (36, 0)
L_VIA23     = (37, 0)
L_METAL3    = (38, 0)
L_FUSETOP   = (75, 0)     # for MIM cap top plate (placeholder)
L_CAPMIM    = (36, 5)     # MIM cap layer (per GF180 docs)
L_PR_BNDRY  = (0, 0)      # design boundary
L_PADOPEN   = (53, 0)     # pad opening
L_TEXT      = (63, 63)


# ── op-amp placement (with proper spacing to avoid bbox overlap) ───────────
# Each m*_nmos / m*_pmos cell extends ~6 µm in X, ~43 µm in Y.
# Use Y_PMOS = 120 (much bigger than 80) so transistors don't touch.
ROW_NMOS_Y = 0.0
ROW_PMOS_Y = 120.0
X_PITCH    = 18.0   # NMOS in X are 12 µm wide; 18 µm pitch gives 6 µm route channel

OPAMP_PLACEMENTS = [
    ("m1_nmos", 0,             ROW_NMOS_Y),
    ("m2_nmos", X_PITCH * 1,   ROW_NMOS_Y),
    ("m5_nmos", X_PITCH * 2,   ROW_NMOS_Y),
    ("m7_nmos", X_PITCH * 3,   ROW_NMOS_Y),
    ("m3_pmos", 0,             ROW_PMOS_Y),
    ("m4_pmos", X_PITCH * 1,   ROW_PMOS_Y),
    ("m6_pmos", X_PITCH * 2.5, ROW_PMOS_Y),
]

OPAMP_W = X_PITCH * 4 + 20   # ~92 µm
OPAMP_H = ROW_PMOS_Y + 60     # ~180 µm


def rect(x1, y1, x2, y2, layer):
    return gdstk.rectangle((x1, y1), (x2, y2),
                           layer=layer[0], datatype=layer[1])


def lbl(text, x, y, layer=L_TEXT):
    return gdstk.Label(text=text, origin=(x, y),
                       layer=layer[0], texttype=layer[1])


def build_opamp(workdir: Path) -> gdstk.Cell:
    """Returns an op-amp cell with placed transistors + power rails +
    metal2 routing channels + Miller cap."""

    lib = gdstk.Library(name="opamp", unit=1e-6, precision=1e-9)
    cell = lib.new_cell("opamp_2stage")

    # Import each transistor GDS and place it
    sub_cells = {}
    for tname, x, y in OPAMP_PLACEMENTS:
        gds = workdir / f"{tname}.gds"
        if not gds.exists():
            print(f"  WARN: {tname}.gds missing — placeholder used")
            ph = lib.new_cell(tname)
            ph.add(rect(-6, -42, 6, 42, L_METAL1))
            sub_cells[tname] = ph
            continue
        sub_lib = gdstk.read_gds(str(gds))
        tops = sub_lib.top_level()
        sub = tops[0]
        # Import dependencies into our library
        for c in [sub] + list(sub.dependencies(True)):
            if c.name not in [x.name for x in lib.cells]:
                lib.add(c)
        sub_cells[tname] = sub
        ref = gdstk.Reference(sub, origin=(x, y))
        cell.add(ref)

    # ── metal1 power rails ────────────────────────────────────────────────
    rail_w = 4.0
    margin = 8.0
    x0 = -margin
    x1 = X_PITCH * 4 + margin

    # VDD rail — above PMOS row
    cell.add(rect(x0, ROW_PMOS_Y + 50, x1, ROW_PMOS_Y + 50 + rail_w, L_METAL1))
    cell.add(lbl("VDD", (x0 + x1) / 2, ROW_PMOS_Y + 52))

    # VSS rail — below NMOS row
    cell.add(rect(x0, ROW_NMOS_Y - 50, x1, ROW_NMOS_Y - 50 + rail_w, L_METAL1))
    cell.add(lbl("VSS", (x0 + x1) / 2, ROW_NMOS_Y - 48))

    # VBN bias rail — between rows
    cell.add(rect(x0, (ROW_NMOS_Y + ROW_PMOS_Y) / 2 - rail_w / 2,
                  x1, (ROW_NMOS_Y + ROW_PMOS_Y) / 2 + rail_w / 2, L_METAL1))
    cell.add(lbl("VBN", x0 + 5, (ROW_NMOS_Y + ROW_PMOS_Y) / 2))

    # ── metal2 routing channels ───────────────────────────────────────────
    # Vertical metal2 stripes connecting NMOS-row drains to PMOS-row drains
    # (the "diode" node d_l from M1.drain to M3.drain, and "output side"
    # d_r from M2.drain to M4.drain to M6.gate).
    # Each transistor is ~12 µm wide; route on its centerline.
    m2_w = 1.5
    for label_text, x_center in [("d_l", X_PITCH * 0.5),
                                 ("d_r", X_PITCH * 1.5),
                                 ("d_tail", X_PITCH * 2.5),
                                 ("vout", X_PITCH * 3 + 4)]:
        cell.add(rect(x_center - m2_w / 2, ROW_NMOS_Y - 5,
                      x_center + m2_w / 2, ROW_PMOS_Y + 5, L_METAL2))
        cell.add(lbl(label_text, x_center, (ROW_NMOS_Y + ROW_PMOS_Y) / 2 + 30,
                     L_TEXT))

    # ── Miller cap (placeholder MIM rectangle) ────────────────────────────
    # 30x30 µm to give ~1 pF at GF180 MIM density.
    mim_x = X_PITCH * 3
    mim_y = ROW_PMOS_Y + 8
    cell.add(rect(mim_x, mim_y, mim_x + 30, mim_y + 30, L_CAPMIM))
    cell.add(rect(mim_x + 1, mim_y + 1, mim_x + 29, mim_y + 29, L_METAL2))
    cell.add(lbl("Cmiller", mim_x + 15, mim_y + 15, L_TEXT))

    # ── op-amp I/O port labels ────────────────────────────────────────────
    cell.add(lbl("vinp", -3, ROW_NMOS_Y - 20))
    cell.add(lbl("vinn", X_PITCH - 3, ROW_NMOS_Y - 20))
    cell.add(lbl("vout", X_PITCH * 3 + 5, (ROW_NMOS_Y + ROW_PMOS_Y) / 2))

    return lib, cell


def block_outline(lib, name, w, h, label_text):
    """Make a simple block-outline cell — represents PGA / S/H / Vref
    at the floorplan level. Real transistor layout per block is future
    work."""
    c = lib.new_cell(name)
    # outline on metal1
    c.add(rect(0, 0, w, h, L_METAL1))
    # cut a smaller inner rectangle to visually distinguish from solid metal
    c.add(rect(1, 1, w - 1, h - 1, L_METAL3))
    c.add(lbl(label_text, w / 2, h / 2, L_TEXT))
    # power/ground straps
    c.add(rect(0, h - 4, w, h, L_METAL1))     # VDD strap top
    c.add(rect(0, 0, w, 4, L_METAL1))         # VSS strap bottom
    return c


def build_afe_top(workdir: Path) -> Path:
    # First produce the op-amp library and cell
    op_lib, op_cell = build_opamp(workdir)
    op_gds = workdir / "opamp_2stage.gds"
    op_lib.write_gds(str(op_gds))
    print(f"  wrote {op_gds} ({op_gds.stat().st_size} B)")

    # Top library for the whole AFE
    top_lib = gdstk.Library(name="AFE", unit=1e-6, precision=1e-9)
    afe = top_lib.new_cell("afe_top")

    # Add op-amp at (40, 40)
    # We need to import op_cell + its dependencies into top_lib
    for c in [op_cell] + list(op_cell.dependencies(True)):
        if c.name not in [x.name for x in top_lib.cells]:
            top_lib.add(c)
    afe.add(gdstk.Reference(op_cell, origin=(40, 40)))

    # Build placeholder block cells (PGA, S/H, Vref) and place them
    pga    = block_outline(top_lib, "pga_R",  120, 100, "PGA")
    sh     = block_outline(top_lib, "sh_cap", 100, 80,  "S/H")
    vref   = block_outline(top_lib, "vref",   100, 80,  "Vref")
    bias   = block_outline(top_lib, "bias",   60,  60,  "Bias")

    afe.add(gdstk.Reference(pga,  origin=(180, 40)))
    afe.add(gdstk.Reference(sh,   origin=(320, 40)))
    afe.add(gdstk.Reference(vref, origin=(40, 280)))
    afe.add(gdstk.Reference(bias, origin=(160, 280)))

    # ── die outline 600 x 500 µm ──────────────────────────────────────────
    DIE_W = 600
    DIE_H = 500
    afe.add(rect(0, 0, DIE_W, DIE_H, L_PR_BNDRY))
    afe.add(lbl("PromptAFE / GF180MCU 5V / 600x500 um", DIE_W / 2, 15))

    # ── pad ring along top edge ───────────────────────────────────────────
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

    out = workdir / "afe_top.gds"
    top_lib.write_gds(str(out))
    print(f"  wrote {out} ({out.stat().st_size} B)")
    return out


if __name__ == "__main__":
    workdir = Path(os.environ.get("AFE_WORKDIR", "."))
    p = build_afe_top(workdir)
    print(f"\nDone. AFE top GDS at {p}")
