# Generate each op-amp transistor as a standalone GDS.
# Each transistor lives in its own cell + GDS file. Composition into the
# op-amp top-level happens in Python (compose_opamp.py) using gdstk.

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
        return 0
    }
    save $name
    gds write $name
    return 1
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
        return 0
    }
    save $name
    gds write $name
    return 1
}

puts "=== generating GF180 transistor GDS files ==="
make_nfet m1_nmos 20 2 4 4
make_nfet m2_nmos 20 2 4 4
make_nfet m5_nmos 10 2 4 4
make_nfet m7_nmos 20 2 4 4
make_pfet m3_pmos 10 2 4 4
make_pfet m4_pmos 10 2 4 4
make_pfet m6_pmos 40 1 4 4

puts "DONE"
quit -noprompt
