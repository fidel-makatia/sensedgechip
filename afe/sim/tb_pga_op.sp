* PGA — DC operating-point check, no AC
.lib /foss/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice tt
.include /foss/designs/afe/netlist/pga_switched_r.sp

vdd vdd 0 1.8
vss vss 0 0
vbn vbn 0 0.7
vinp vinp 0 0.9

xdut vinp vout vbn vdd vss pga_sw_r
cload vout vss 5p

.control
op
print v(vinp) v(vout)
print v(xdut.vfb) v(xdut.vbcm)
print i(vbn) i(vdd)
.endc
.end
