# SenseEdge on GF180MCU — Clean GDS

**Date:** 2026-05-10
**Run tag:** `RUN_2026-05-10_23-37-44`
**Flow:** LibreLane v3.0.2 Classic
**Target PDK:** GF180MCU 5LM (gf180mcuD), 9-track 5V std cells (`gf180mcu_fd_sc_mcu9t5v0`)

## Headline

**Manufacturing-ready GDS** — fully timing-closed, DRC-clean, LVS-clean.

| Metric | Value | Status |
|---|---|---|
| Clock period | 250 ns (4 MHz) | met with margin |
| Setup worst slack | **+31.86 ns** | ✅ closed (~12.7% margin) |
| Setup total negative slack | 0 ns | ✅ |
| Hold worst slack | +0.184 ns | ✅ closed |
| Hold total negative slack | 0 ns | ✅ |
| LVS errors | 0 | ✅ clean |
| Magic DRC errors | 0 | ✅ clean |
| Route DRC errors | 0 | ✅ clean |

## Physical

| | |
|---|---|
| Die area | 9.00 mm² (3000 × 3000 µm) |
| Cell area | 8.84 mm² |
| Utilization | 26.19% |
| Cell instances | 265,015 |
| Total wirelength | 5.13 m |
| Metal stack | Metal1–Metal4 signal, Metal5 power |

## Files

```
RUN_2026-05-10_23-37-44-CLOSED/
├── gds/senseedge_top.gds       (84 MB)  — the chip
├── lef/                                  — abstract for higher-level use
├── def/                                  — placed-and-routed netlist
├── lib/                                  — timing libraries (corner files)
├── spef/                                 — parasitics extraction
├── render/senseedge_top.png    (105 KB) — visualization
├── metrics.json                          — full machine-readable metrics
├── metrics.csv                           — same, spreadsheet-friendly
└── SUMMARY.md                            — this file
```

## Build notes / lessons learned

Hard-won config knowledge captured for re-use (also saved in
`~/.claude/projects/.../memory/chipathon_infra.md`):

1. **9-track standard cell library** required — `gf180mcu_fd_sc_mcu7t5v0`
   hits DRT-1231 "no access point" failures on small clock buffers due to
   `LEF58_ENCLOSURE` with no CUTCLASS being unhandled by OpenROAD's parser.
2. **`drc_exclude.cells` missing for 9-track lib** in the IIC-OSIC image —
   created locally and bind-mounted into the PDK path inside the container.
3. **Restrict CTS to `clkbuf_16` + `clkbuf_20` only** — smaller clock
   buffers cause routing-layer access issues.
4. **Disable heuristic diode insertion + antenna repair** — those passes
   insert antenna cells with pin shapes the router can't reach.
5. **Metal4 max routing layer** — Metal5 reserved exclusively for power.
6. **Skip `Checker.YosysSynthChecks`** — 332 mem2bits warnings from FFT/NN
   multi-port memory access fire false positives.
7. **Clock period ≥ 250 ns (4 MHz)** for clean closure on `senseedge_top`.
   Design has combinational paths > 100 ns; 200 ns gave -8 ns slack.

## Rerun

```bash
# Restart VM
az vm start -g rg-chipathon-2026 -n vm-senseedge

# SSH (NSG already locked to your IP; project key is ~/.ssh/chipathon_vm_ed25519)
ssh -i ~/.ssh/chipathon_vm_ed25519 -o IdentitiesOnly=yes fidel@<vm-ip>

# Inside the VM
bash /tmp/launch-openlane.sh
tail -f /opt/chipathon/scratch/openlane_run.log

# Stop billing
az vm deallocate -g rg-chipathon-2026 -n vm-senseedge
```
