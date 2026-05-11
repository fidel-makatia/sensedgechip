* AFE top-level transient — full chain stimulation
.lib /foss/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice tt
.include /foss/designs/afe/netlist/afe_top.sp

.param vdd_v=1.8
.param vcm_v=0.9
.param vbn_v=0.7

vdd vdd 0 {vdd_v}
vss vss 0 0
vbn vbn 0 {vbn_v}

* Small input: 100 Hz sine, 5 mV amplitude around 0.9 V
* PGA gain 100× → expect 500 mV swing at PGA output
vin vinp 0 sin(0.9 0.005 100)

* Clocks
vphi1  phi1  0 pulse(0 1.8 0 10n 10n 5u 10u)
vphi1a phi1a 0 pulse(0 1.8 0 10n 10n 4.5u 10u)

xdut vinp vout phi1 phi1a vbn vdd vss afe_top

.control
set noaskquit
tran 0.5u 200u
echo "================ AFE top-level results ================"
meas tran vmax MAX v(vout) FROM=50u TO=150u
meas tran vmin MIN v(vout) FROM=50u TO=150u
meas tran swing PARAM='vmax-vmin'
print vmax vmin swing
echo "========================================================"
wrdata /opt/chipathon/scratch/afe_tran.dat v(vinp) v(xdut.vpga_out) v(vout)
.endc
.end
