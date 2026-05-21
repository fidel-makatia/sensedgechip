"""Build the final AFE top using the real wired op-amp + real PGA
+ S/H with MIM cap. Vref and Bias remain as block outlines (those
are next-iteration work).
"""

import os
from pathlib import Path
import gdstk

import sys
sys.path.insert(0, str(Path(__file__).parent))
from wire_opamp import (L_METAL1, L_METAL2, L_VIA12, L_TEXT, L_PR_BNDRY,
                        L_PADOPEN, rect, lbl, metal2_wire)
from build_pga import build_pga
from wire_opamp import build_wired_opamp


def build_sh(workdir: Path, op_lib) -> gdstk.Library:
    """S/H block: op-amp as buffer + MIM sampling cap + (placeholder)
    switches. Real switches are NMOS pass-gates — for first-pass we draw
    them as block outlines too."""
    lib = gdstk.Library(name="SH", unit=1e-6, precision=1e-9)

    # Import op-amp + deps
    op_cell = op_lib.cells[-1]
    for c in [op_cell] + list(op_cell.dependencies(True)):
        if c.name not in [x.name for x in lib.cells]:
            lib.add(c)

    sh = lib.new_cell("sh_real")
    # Op-amp as unity-gain buffer
    sh.add(gdstk.Reference(op_cell, origin=(0, 0)))

    # MIM cap (30x30 µm — pre-generated as c_samp.gds)
    csamp_gds = workdir / "c_samp.gds"
    if csamp_gds.exists():
        cs_lib = gdstk.read_gds(str(csamp_gds))
        cs = cs_lib.top_level()[0]
        for c in [cs] + list(cs.dependencies(True)):
            if c.name not in [x.name for x in lib.cells]:
                lib.add(c)
        sh.add(gdstk.Reference(cs, origin=(130, 80)))

    # Switches (placeholders for now — NMOS pass-gates would be added here)
    for i, (x, y, name) in enumerate([(120, 30, "sw_phi1"),
                                        (170, 30, "sw_phi1a")]):
        sh.add(rect(x, y, x + 30, y + 20, L_METAL1))
        sh.add(rect(x + 2, y + 2, x + 28, y + 18, L_METAL2))
        sh.add(lbl(name, x + 15, y + 10))

    # Wiring (placeholder metal2 channels)
    metal2_wire(sh, 90, 50, 140, 80)
    metal2_wire(sh, 165, 80, 220, 50)
    sh.add(lbl("vin",  -3, -55))
    sh.add(lbl("vout", 220, 50))

    sh.add(rect(-15, -65, 250, 200, L_PR_BNDRY))
    sh.add(lbl("S/H (Cs=30x30, fs<=100kSPS)", 100, -75))
    return lib


def block_outline(lib, name, w, h, label_text):
    c = lib.new_cell(name)
    c.add(rect(0, 0, w, h, L_METAL1))
    c.add(rect(1, 1, w - 1, h - 1, (38, 0)))
    c.add(lbl(label_text, w / 2, h / 2))
    c.add(rect(0, h - 4, w, h, L_METAL1))
    c.add(rect(0, 0, w, 4, L_METAL1))
    return c


def build_afe_top(workdir: Path):
    # Build PGA (which internally builds the op-amp)
    pga_lib = build_pga(workdir)
    pga_cell = next(c for c in pga_lib.cells if c.name == "pga_real")

    # Build a separate op-amp lib for S/H reuse (avoids name conflict)
    op_only_lib = build_wired_opamp(workdir)
    op_cell = next(c for c in op_only_lib.cells if c.name == "opamp_2stage_wired")

    # S/H reuses the op-amp
    sh_lib_template = gdstk.Library(name="op_for_sh", unit=1e-6, precision=1e-9)
    for c in [op_cell] + list(op_cell.dependencies(True)):
        sh_lib_template.add(c)
    sh_lib = build_sh(workdir, sh_lib_template)
    sh_cell = None
    for c in sh_lib.cells:
        if c.name == "sh_real":
            sh_cell = c
            break

    # Top library
    top_lib = gdstk.Library(name="AFE_v2", unit=1e-6, precision=1e-9)
    afe = top_lib.new_cell("afe_top")

    # Import op-amp once (used by both pga and sh)
    for c in [op_cell] + list(op_cell.dependencies(True)):
        if c.name not in [x.name for x in top_lib.cells]:
            top_lib.add(c)

    # Import PGA cells (skipping the op-amp duplicates)
    for c in [pga_cell] + list(pga_cell.dependencies(True)):
        if c.name not in [x.name for x in top_lib.cells]:
            top_lib.add(c)

    # Import S/H cells
    for c in [sh_cell] + list(sh_cell.dependencies(True)):
        if c.name not in [x.name for x in top_lib.cells]:
            top_lib.add(c)

    # Floorplan placement on a 700 x 500 µm die
    DIE_W, DIE_H = 700, 500
    afe.add(rect(0, 0, DIE_W, DIE_H, L_PR_BNDRY))
    afe.add(lbl("PromptAFE v2 / GF180MCU 5V / 700x500 um", DIE_W / 2, 18))

    # PGA at lower-left
    afe.add(gdstk.Reference(pga_cell, origin=(40, 40)))

    # S/H at lower-right
    afe.add(gdstk.Reference(sh_cell, origin=(340, 40)))

    # Vref and Bias as block outlines, upper area
    vref = block_outline(top_lib, "vref", 100, 80, "Vref")
    bias = block_outline(top_lib, "bias",  60, 60, "Bias")
    afe.add(gdstk.Reference(vref, origin=(40, 300)))
    afe.add(gdstk.Reference(bias, origin=(160, 300)))

    # 12-pad pad ring
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

    out = workdir / "afe_top_v2.gds"
    top_lib.write_gds(str(out))
    print(f"wrote {out} ({out.stat().st_size} B)")
    return out


if __name__ == "__main__":
    workdir = Path(os.environ.get("AFE_WORKDIR", "."))
    build_afe_top(workdir)
