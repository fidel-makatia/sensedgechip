* Transient — slew rate, settling time, step response
.lib /foss/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice tt
.include /foss/designs/afe/netlist/opamp_2stage_sky130.sp

.param vdd_v=1.8
.param vcm_v=0.9
.param vbn_v=0.7

vdd  vdd  0  {vdd_v}
vss  vss  0  0
vbn  vbn  0  {vbn_v}

* Unity-gain buffer: connect vout to vinn
vinp vinp 0 pulse(0.6 1.2 100n 5n 5n 1u 2u)
xdut vinp vout vout vbn vdd vss opamp_2stage_sky130

cload vout vss 5p

.control
set noaskquit
tran 1n 4u
meas tran t_rise WHEN v(vout)=0.9 RISE=1
meas tran t_settle WHEN v(vout)=1.15 RISE=1
meas tran sr_pos DERIV v(vout) AT=200n
echo ""
echo "================ Transient Results ================"
print t_rise t_settle sr_pos
echo "==================================================="
wrdata /opt/chipathon/scratch/opamp_tran.dat v(vinp) v(vout)
.endc
.end
