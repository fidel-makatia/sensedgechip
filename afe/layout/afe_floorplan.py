"""Generate the PromptAFE chiplet floorplan as a GDS using gdstk.

Floorplan-level GDS — die outline + block placement + pad ring + labels.
Defines the physical envelope of the AFE chiplet (700 × 850 µm = 0.595 mm²)
and the pin layout that interfaces with the SenseEdge digital chiplet via
the BoW-Lite die-to-die bus.

Layers are placeholder GF180 aliases; actual GDS layer numbers are pulled
from the GF180MCU technology file during the real transistor-level layout
step (next session — done via gLayout or Magic with PCells).

This is the SYSTEM-LEVEL physical view. The transistor-level GDS lives
below this, generated per-block, instantiated into these regions.
"""

import gdstk

# Layer assignments (GF180 placeholders)
L_OUTLINE  = (235, 4)
L_METAL1   = (34,  0)
L_METAL2   = (36,  0)
L_METAL3   = (42,  0)
L_METAL4   = (46,  0)
L_PAD      = (53,  0)
L_LABEL    = (235, 5)

DIE_W = 700
DIE_H = 850


def rect(x, y, w, h, layer):
    return gdstk.rectangle((x, y), (x + w, y + h), layer=layer[0],
                           datatype=layer[1])


def label(text, x, y, layer):
    return gdstk.Label(text=text, origin=(x, y), layer=layer[0],
                       texttype=layer[1])


def build():
    lib = gdstk.Library(name="PromptAFE", unit=1e-6, precision=1e-9)
    top = lib.new_cell("afe_top")

    # Die outline
    top.add(rect(0, 0, DIE_W, DIE_H, L_OUTLINE))

    # Blocks
    blocks = [
        ("opamp",  60,  80, 220, 180, L_METAL1),
        ("pga_R",  300, 100, 150, 120, L_METAL2),
        ("sh_cap", 480, 100, 120, 90,  L_METAL3),
        ("vref",   60,  320, 140, 110, L_METAL1),
        ("bias",   220, 320, 90,  90,  L_METAL2),
    ]
    for name, x, y, w, h, lyr in blocks:
        top.add(rect(x, y, w, h, lyr))
        top.add(label(name, x + w / 2, y + h / 2, L_LABEL))

    # Pad ring (top side: 12 pads)
    pad_w, pad_h, pitch = 60, 90, 100
    y_pad = 700
    pads = ["VDD", "VSS", "VINP", "VOUT", "PHI1", "PHI1A",
            "GAIN0", "GAIN1", "GAIN2", "VREF", "VBN", "TEST"]
    for i, p in enumerate(pads):
        x_pad = 40 + i * pitch
        # Pads only fit if x_pad + pad_w < DIE_W
        if x_pad + pad_w > DIE_W:
            break
        top.add(rect(x_pad, y_pad, pad_w, pad_h, L_PAD))
        top.add(label(p, x_pad + pad_w / 2, y_pad + pad_h / 2, L_LABEL))

    # Title
    top.add(label("PromptAFE v1 / GF180MCU / 700x850 um",
                  DIE_W / 2, 25, L_LABEL))

    return lib


if __name__ == "__main__":
    lib = build()
    import os
    out = os.environ.get("AFE_OUT_GDS", "/scratch/afe_floorplan.gds")
    lib.write_gds(out)
    print(f"wrote {out}")
    print(f"die area: {DIE_W} x {DIE_H} = {DIE_W * DIE_H / 1e6:.3f} mm^2")
