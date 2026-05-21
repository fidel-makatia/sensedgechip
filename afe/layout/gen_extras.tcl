# Generate the remaining PCells: small NMOS for S/H switches, diode-connected NMOS for Vref,
# additional poly resistors for Vref/bias stacks, and a current-mirror NMOS pair for bias.

proc make_nfet {name w l nf m} {
    cellname rename {(UNNAMED)} $name
    load $name
    set p [gf180mcu::nfet_05v0_defaults]
    dict set p w $w; dict set p l $l; dict set p nf $nf; dict set p m $m
    catch {gf180mcu::nfet_05v0_draw $p}
    save $name; gds write $name
}

proc make_npoly {name w l b} {
    cellname rename {(UNNAMED)} $name
    load $name
    set p [gf180mcu::npolyf_u_defaults]
    dict set p w $w; dict set p l $l; dict set p b $b
    catch {gf180mcu::npolyf_u_draw $p}
    save $name; gds write $name
}

# S/H pass-gate switches — small NMOS, m=1, nf=1
make_nfet sw_nmos 4 1 1 1

# Vref diode-connected NMOS
make_nfet vref_nmos 2 4 1 1

# Bias current mirror — two NMOS in parallel pattern (use one cell, instantiate twice)
make_nfet bias_nmos 8 2 2 2

# Vref resistor stack (5kohm each, multiple in series)
make_npoly r_vref 2 18 1

puts "DONE"
quit -noprompt
