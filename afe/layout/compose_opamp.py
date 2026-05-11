"""Compose the op-amp top-cell GDS by placing pre-generated transistor GDS
sub-cells into a top-level layout.

Reads:
  m1_nmos.gds, m2_nmos.gds, m5_nmos.gds, m7_nmos.gds  (NMOS row)
  m3_pmos.gds, m4_pmos.gds, m6_pmos.gds               (PMOS row)

Writes:
  opamp_2stage_layout.gds — top cell instantiating all transistors

Each transistor GDS contains exactly one cell (named the same as the file).
We import them, then place instances on a simple horizontal-row floorplan.

This produces a STRUCTURALLY correct GDS (correct cell instances, no
overlap). Routing (power rails, signal wires) is the next layer of work
and lives in a follow-on Magic script.
"""

from pathlib import Path
import gdstk

ROW_NMOS_Y = 0.0       # µm
ROW_PMOS_Y = 80.0
X_PITCH    = 50.0

PLACEMENTS = [
    # (cell_name, x_um, y_um)
    ("m1_nmos", 0   , ROW_NMOS_Y),
    ("m2_nmos", X_PITCH * 1, ROW_NMOS_Y),
    ("m5_nmos", X_PITCH * 2, ROW_NMOS_Y),
    ("m7_nmos", X_PITCH * 3, ROW_NMOS_Y),
    ("m3_pmos", 0   , ROW_PMOS_Y),
    ("m4_pmos", X_PITCH * 1, ROW_PMOS_Y),
    ("m6_pmos", X_PITCH * 2, ROW_PMOS_Y),
]


def compose(workdir: Path, out_path: Path) -> None:
    # Create the top library
    top_lib = gdstk.Library(name="opamp_top", unit=1e-6, precision=1e-9)
    top_cell = top_lib.new_cell("opamp_2stage_layout")

    for cell_name, x, y in PLACEMENTS:
        gds_file = workdir / f"{cell_name}.gds"
        if not gds_file.exists():
            print(f"  SKIP {cell_name}: {gds_file} not found")
            continue

        # Read the sub-cell GDS
        sub_lib = gdstk.read_gds(str(gds_file))
        # Magic writes cells with the transistor structure inside;
        # find the top cell of the sub-library
        sub_cells = sub_lib.top_level()
        if not sub_cells:
            print(f"  SKIP {cell_name}: no top cell in {gds_file}")
            continue
        sub_top = sub_cells[0]

        # Add the sub-cell to the top library
        top_lib.add(sub_top, *sub_top.dependencies(True))

        # Place an instance
        ref = gdstk.Reference(sub_top, origin=(x, y))
        top_cell.add(ref)
        print(f"  placed {cell_name} at ({x}, {y})")

    top_lib.write_gds(str(out_path))
    print(f"\nwrote {out_path}")
    # Report size
    print(f"GDS size: {out_path.stat().st_size} bytes")


if __name__ == "__main__":
    import sys
    workdir = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out = Path(sys.argv[2] if len(sys.argv) > 2
                            else workdir / "opamp_2stage_layout.gds")
    compose(workdir, out)
