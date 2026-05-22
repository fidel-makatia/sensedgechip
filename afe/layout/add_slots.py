"""Post-process AFE GDS to add slot cuts in wide metal1 polygons.

MSLOT.1 (GF180): metal lines >= 13 um wide need 1x1 um slot cuts at
~8 um spacing to relieve manufacturing stress. Cuts implemented as
polygon subtraction on the metal1 layer (34, 0).
"""

import os
from pathlib import Path
import gdstk

L_METAL1 = (34, 0)
SLOT_W = 0.6          # slot width — keep < 1um to avoid M1.2a spacing edge cases
SLOT_PITCH = 8.0      # slot pitch
WIDE_THRESHOLD = 12.0 # poly wider than this needs slots
EDGE_MARGIN = 3.0     # keep slots well away from poly edges


def add_slots(in_gds: Path, out_gds: Path):
    lib = gdstk.read_gds(str(in_gds))
    print(f"loaded {in_gds}, {len(lib.cells)} cells")

    total_slots = 0
    for cell in lib.cells:
        # Find metal1 polygons that are wide enough to need slotting
        wide_polys = []
        m1_polys = [p for p in list(cell.polygons)
                    if (p.layer, p.datatype) == L_METAL1]
        for p in m1_polys:
            bb = p.bounding_box()
            if bb is None: continue
            (x0, y0), (x1, y1) = bb
            if (x1 - x0) >= WIDE_THRESHOLD and (y1 - y0) >= WIDE_THRESHOLD:
                wide_polys.append((p, x0, y0, x1, y1))

        if not wide_polys: continue

        # For each wide polygon, generate slot holes on a grid
        slots = []
        for p, x0, y0, x1, y1 in wide_polys:
            xs = [x for x in [x0 + EDGE_MARGIN + i * SLOT_PITCH
                              for i in range(int((x1 - x0 - 2 * EDGE_MARGIN) / SLOT_PITCH))]]
            ys = [y for y in [y0 + EDGE_MARGIN + i * SLOT_PITCH
                              for i in range(int((y1 - y0 - 2 * EDGE_MARGIN) / SLOT_PITCH))]]
            for sx in xs:
                for sy in ys:
                    if sx + SLOT_W < x1 - EDGE_MARGIN and sy + SLOT_W < y1 - EDGE_MARGIN:
                        slots.append(gdstk.rectangle((sx, sy),
                                                     (sx + SLOT_W, sy + SLOT_W),
                                                     layer=L_METAL1[0],
                                                     datatype=L_METAL1[1]))

        # Subtract slots from the original metal1 polys
        if slots:
            for p, *_ in wide_polys:
                result = gdstk.boolean([p], slots, "not",
                                       layer=L_METAL1[0], datatype=L_METAL1[1])
                cell.remove(p)
                for r in result:
                    cell.add(r)
            total_slots += len(slots)
            print(f"  {cell.name}: added {len(slots)} slots to {len(wide_polys)} wide polys")

    print(f"\nTotal slots added: {total_slots}")
    lib.write_gds(str(out_gds))
    print(f"wrote {out_gds} ({out_gds.stat().st_size} B)")


if __name__ == "__main__":
    workdir = Path(os.environ.get("AFE_WORKDIR", "."))
    add_slots(workdir / "afe_final.gds", workdir / "afe_final_slotted.gds")
