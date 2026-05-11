* PGA AC sweep — measures closed-loop gain
.lib /foss/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice tt
.include /foss/designs/afe/netlist/pga_switched_r.sp

.param vdd_v=1.8
.param vcm_v=0.9
.param vbn_v=0.7
.param rf_v=99k   ; max-gain setting: 1 + 99k/1k = 100 → 40 dB

vdd vdd 0 {vdd_v}
vss vss 0 0
vbn vbn 0 {vbn_v}
vinp vinp 0 dc {vcm_v} ac 1m

xdut vinp vout vbn vdd vss pga_sw_r

cload vout vss 5p

.control
set noaskquit
ac dec 30 1 1e8

let vout_db = db(v(vout)/0.001)
let dc_gain = vout_db[0]
meas ac bw_3db WHEN vout_db = (dc_gain - 3) FALL=1

echo ""
echo "================ PGA Results (Rf=99k, gain=100×, 40 dB) ================"
print dc_gain
echo "========================================================================"

wrdata /opt/chipathon/scratch/pga_ac.dat vout_db
.endc
.end
