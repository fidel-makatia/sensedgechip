"""Add power rails, port labels, and basic routing to the composed op-amp GDS.

Takes:  opamp_2stage_layout.gds  (transistors placed by compose_opamp.py)
Writes: opamp_routed.gds         (with VDD/VSS/VBN rails + port labels)

This is "first-pass routing" — adds the metal1 power rails and labels that
make the layout testable for connectivity. Real signal routing between
transistor terminals (drain-to-drain, gate-to-net) is the next iteration
and would benefit from interactive design in klayout or magic GUI.

Layers used (GF180 standard):
    Metal1 = (34, 0)
    Metal2 = (36, 0)
    Via12  = (35, 0)
    Text   = (63, 63)
"""

from pathlib import Path
import gdstk

# GF180 layer numbers (from the open-pdks gf180mcu_fd_pr LEF)
L_METAL1 = (34, 0)
L_METAL2 = (36, 0)
L_VIA12  = (35, 0)
L_TEXT   = (63, 63)

# Layout coordinates (must match compose_opamp.py)
ROW_NMOS_Y = 0.0       # µm
ROW_PMOS_Y = 80.0
X_PITCH    = 50.0
N_NMOS     = 4    # m1, m2, m5, m7
N_PMOS     = 3    # m3, m4, m6

# Power rail geometry
RAIL_W       = 4.0           # rail width in µm
RAIL_MARGIN  = 25.0
DIE_LEFT     = -30.0
DIE_RIGHT    = X_PITCH * max(N_NMOS, N_PMOS) + 30.0   # 230 µm
VDD_Y        = ROW_PMOS_Y + 70.0   # above PMOS row
VSS_Y        = ROW_NMOS_Y - 30.0   # below NMOS row
VBN_Y        = ROW_PMOS_Y - 15.0   # between rows


def rect(x1, y1, x2, y2, layer):
    return gdstk.rectangle((x1, y1), (x2, y2), layer=layer[0], datatype=layer[1])


def label(text, x, y, layer):
    return gdstk.Label(text=text, origin=(x, y), layer=layer[0], texttype=layer[1])


def add_routing(in_gds: Path, out_gds: Path):
    # Read the composed layout
    lib = gdstk.read_gds(str(in_gds))
    print(f"loaded {in_gds}")
    print(f"  cells in lib: {[c.name for c in lib.cells]}")

    # Find the top cell
    top_cells = lib.top_level()
    top = None
    for c in top_cells:
        if c.name == "opamp_2stage_layout":
            top = c
            break
    if top is None:
        top = top_cells[0] if top_cells else lib.cells[0]
    print(f"  top cell: {top.name}, current bbox: {top.bounding_box()}")

    # Add VDD rail
    top.add(rect(DIE_LEFT, VDD_Y, DIE_RIGHT, VDD_Y + RAIL_W, L_METAL1))
    top.add(label("VDD", (DIE_LEFT + DIE_RIGHT) / 2, VDD_Y + RAIL_W / 2, L_TEXT))

    # Add VSS rail
    top.add(rect(DIE_LEFT, VSS_Y, DIE_RIGHT, VSS_Y + RAIL_W, L_METAL1))
    top.add(label("VSS", (DIE_LEFT + DIE_RIGHT) / 2, VSS_Y + RAIL_W / 2, L_TEXT))

    # Add VBN rail (vertical strip on left side)
    top.add(rect(DIE_LEFT, VBN_Y, DIE_RIGHT, VBN_Y + RAIL_W, L_METAL1))
    top.add(label("VBN", DIE_LEFT + 10, VBN_Y + RAIL_W / 2, L_TEXT))

    # Add I/O port labels at transistor gate locations (approx)
    # vinp on M1 (left NMOS, gate ~ x = 5)
    top.add(label("vinp", 5,  ROW_NMOS_Y + 30, L_TEXT))
    top.add(label("vinn", X_PITCH + 5, ROW_NMOS_Y + 30, L_TEXT))
    # vout — between M6 (PMOS) and M7 (NMOS) drains
    top.add(label("vout", X_PITCH * 2 + 25, (ROW_NMOS_Y + ROW_PMOS_Y) / 2, L_TEXT))

    # Add a wider die-outline rectangle on a non-printing layer (just for visual)
    bbox = top.bounding_box()
    print(f"  new bbox: {bbox}")

    lib.write_gds(str(out_gds))
    print(f"\nwrote {out_gds}")
    print(f"  size: {out_gds.stat().st_size} bytes")


if __name__ == "__main__":
    import sys
    in_gds  = Path(sys.argv[1] if len(sys.argv) > 1 else "opamp_2stage_layout.gds")
    out_gds = Path(sys.argv[2] if len(sys.argv) > 2 else "opamp_routed.gds")
    add_routing(in_gds, out_gds)
