# Magic Tcl — generate poly resistor PCells for PGA feedback network.
# Uses GF180 npolyf_u (n+ poly silicide-blocked) ~280 ohm/sq sheet R.
#   Rin = 1k:    L = 1000/280 * W = 7.14 um for W=2 um  → use L=8, W=2
#   Rf  = 100k:  L = 100k/280 * W = 715 um for W=2 um  → too big.
#                Use ppolyf_u_2k (high-R poly, ~2k ohm/sq):
#                L = 100k/2k * W = 50 um for W=1 um

proc make_npoly {name w l b} {
    cellname rename {(UNNAMED)} $name
    load $name
    set p [gf180mcu::npolyf_u_defaults]
    dict set p w $w
    dict set p l $l
    dict set p b $b
    if {[catch {gf180mcu::npolyf_u_draw $p} err]} {
        puts "ERROR drawing $name: $err"
        return 0
    }
    save $name
    gds write $name
    return 1
}

proc make_mim {name w l} {
    cellname rename {(UNNAMED)} $name
    load $name
    set p [gf180mcu::cap_mim_2p0fF_defaults]
    dict set p w $w
    dict set p l $l
    if {[catch {gf180mcu::cap_mim_2p0fF_draw $p} err]} {
        puts "ERROR drawing $name: $err"
        return 0
    }
    save $name
    gds write $name
    return 1
}

puts "=== generating resistor PCells ==="
make_npoly r_in  2 8  1
make_npoly r_fb  2 80 1
puts ""
puts "=== generating MIM cap PCell ==="
make_mim   c_samp 30 30

puts "DONE"
quit -noprompt
