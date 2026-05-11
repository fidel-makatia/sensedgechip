# Minimum test: create one nfet_05v0 PCell instance in batch Magic.
# Uses gf180mcu::nfet_05v0_draw directly (the low-level draw proc).

puts "=== gf180mcu::nfet_05v0 defaults ==="
set defaults [gf180mcu::nfet_05v0_defaults]
puts "defaults: $defaults"
puts ""

# Create an empty top cell
cellname rename {(UNNAMED)} test_nmos
load test_nmos
cellname filepath . ./

# Build params dict on top of the defaults, override w and l
set p $defaults
dict set p w 20
dict set p l 2
dict set p nf 2
dict set p m 1

puts "calling nfet_05v0_draw with: $p"
if {[catch {gf180mcu::nfet_05v0_draw $p} err]} {
    puts "DRAW ERROR: $err"
} else {
    puts "draw OK"
}

# Inspect what was painted
puts "current box:"
box values
puts ""

# Output
gds write test_nmos
exec ls -la test_nmos.gds
puts "DONE"
quit -noprompt
