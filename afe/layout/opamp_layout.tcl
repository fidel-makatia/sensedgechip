# Magic Tcl — op-amp transistor-level layout for GF180MCU 5 V
# Two-stage Miller-compensated op-amp. Each transistor placed as a
# gf180mcu PCell with explicit (w,l,nf,m) sizing.
#
# Sizing matches the SKY130-validated topology (afe/netlist/opamp_2stage.sp),
# rescaled for GF180 5 V drive:
#   M1, M2 (NMOS diff pair):   W=20 µm, L=2 µm, m=4, nf=4
#   M3, M4 (PMOS load mirror): W=10 µm, L=2 µm, m=4, nf=4
#   M5 (NMOS tail):             W=10 µm, L=2 µm, m=4, nf=4
#   M6 (PMOS stage-2):          W=40 µm, L=1 µm, m=4, nf=4
#   M7 (NMOS stage-2 sink):     W=20 µm, L=2 µm, m=4, nf=4
#
# Floorplan: PMOS row on top, NMOS row on bottom. Each device is its own
# sub-cell instance; the top cell `opamp_2stage` places them side by side.

# ── helper ────────────────────────────────────────────────────────────────
# Build a one-transistor cell and return its name. Uses gf180mcu draw procs.
proc make_nfet {name w l nf m} {
    cellname rename {(UNNAMED)} $name
    load $name
    set p [gf180mcu::nfet_05v0_defaults]
    dict set p w  $w
    dict set p l  $l
    dict set p nf $nf
    dict set p m  $m
    if {[catch {gf180mcu::nfet_05v0_draw $p} err]} {
        puts "ERROR drawing $name: $err"
    }
    return $name
}

proc make_pfet {name w l nf m} {
    cellname rename {(UNNAMED)} $name
    load $name
    set p [gf180mcu::pfet_05v0_defaults]
    dict set p w  $w
    dict set p l  $l
    dict set p nf $nf
    dict set p m  $m
    if {[catch {gf180mcu::pfet_05v0_draw $p} err]} {
        puts "ERROR drawing $name: $err"
    }
    return $name
}

# ── build each transistor sub-cell ─────────────────────────────────────────
puts "=== creating transistor sub-cells ==="
make_nfet m1_nmos 20 2 4 4
make_nfet m2_nmos 20 2 4 4
make_nfet m5_nmos 10 2 4 4
make_nfet m7_nmos 20 2 4 4
make_pfet m3_pmos 10 2 4 4
make_pfet m4_pmos 10 2 4 4
make_pfet m6_pmos 40 1 4 4
puts "transistor cells created"

# ── build the op-amp top cell, place all instances ─────────────────────────
puts "=== assembling opamp_2stage top cell ==="
cellname rename {(UNNAMED)} opamp_2stage
load opamp_2stage

# Pitch between transistor instances (umm, micro-units; magic uses 1 lambda = 0.1 µm
# so 30 µm = 300 lambdas = 3000 internal units)
# Use the `instance place` mechanism.
# Approach: getcell each transistor, position the box, instance it

# X positions (NMOS row, left to right)
set x 0
set y_nmos 0
foreach cell {m1_nmos m2_nmos m5_nmos m7_nmos} {
    box position ${x}um ${y_nmos}um
    getcell $cell
    set x [expr {$x + 30}]
}

# Y position for PMOS row, slightly above
set x 0
set y_pmos 50
foreach cell {m3_pmos m4_pmos m6_pmos} {
    box position ${x}um ${y_pmos}um
    getcell $cell
    set x [expr {$x + 30}]
}

# ── outputs ────────────────────────────────────────────────────────────────
puts "=== writing GDS + extracting for LVS ==="
save opamp_2stage
gds write opamp_2stage

# Extract for LVS
extract all
ext2spice lvs
ext2spice cthresh infinite
ext2spice -p . -o opamp_2stage.lvs.spice opamp_2stage.ext 2>/dev/null

# ── DRC ───────────────────────────────────────────────────────────────────
puts "=== running DRC ==="
drc check
drc catchup
set drc_count [drc list count total]
puts "DRC error count: $drc_count"

# Save error list to file for inspection
set fh [open opamp_2stage.drc w]
puts $fh "DRC errors for opamp_2stage:"
puts $fh "Total: $drc_count"
puts $fh [drc listall why]
close $fh

puts "=== summary ==="
puts "GDS:   opamp_2stage.gds"
puts "DRC:   opamp_2stage.drc (count=$drc_count)"
puts "SPICE: opamp_2stage.lvs.spice"
quit -noprompt
