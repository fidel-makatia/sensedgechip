* S/H transient — verifies sampling, hold droop, acquisition time
.lib /foss/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice tt
.include /foss/designs/afe/netlist/sh_bottom_plate.sp

.param vdd_v=1.8
.param vcm_v=0.9
.param vbn_v=0.7

vdd vdd 0 {vdd_v}
vss vss 0 0
vbn vbn 0 {vbn_v}

* Input signal: 1 kHz sine, 0.4 V_pp around 0.9 V
vin vin 0 sin(0.9 0.2 1k)

* Clock phases — 100 kHz sample rate, Φ1a opens 0.5 µs before Φ1
* Φ1   : high 5 µs, low 5 µs
* Φ1a  : high 4.5 µs, low 5.5 µs (offset by 0.5 µs early-close)
vphi1  phi1  0 pulse(0 1.8 0    10n 10n 5u  10u)
vphi1a phi1a 0 pulse(0 1.8 0    10n 10n 4.5u 10u)

xdut vin vout phi1 phi1a vbn vdd vss sh_bp

.control
set noaskquit
tran 0.1u 100u
meas tran v_at_50us FIND v(vout) AT=50u
meas tran v_at_60us FIND v(vout) AT=60u
meas tran droop_uV PARAM='(v_at_50us-v_at_60us)*1e6'
echo ""
echo ============== S/H Results ==============
print v_at_50us v_at_60us droop_uV
echo =========================================
wrdata /opt/chipathon/scratch/sh_tran.dat v(vin) v(vout) v(phi1) v(phi1a)
.endc
.end
