* AC analysis — op-amp_2stage_sky130 — gain, phase, UGB, PM
* SKY130 1.8V, TT corner, 27°C

.lib /foss/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice tt
.include /foss/designs/afe/netlist/opamp_2stage_sky130.sp

.param vdd_v=1.8
.param vcm_v=0.9
.param vbn_v=0.7

* Supplies
vdd  vdd  0  {vdd_v}
vss  vss  0  0
vbn  vbn  0  {vbn_v}

* Open-loop AC sweep: vinp gets the AC source, vinn fixed at vcm
vinp vinp 0 dc {vcm_v} ac 1
vinn vinn 0 dc {vcm_v}

xdut vinp vinn vout vbn vdd vss opamp_2stage_sky130

cload vout vss 5p

.control
set noaskquit
ac dec 30 1 1e9

let vout_db  = db(v(vout))
let vout_phs = 180/3.14159 * cph(v(vout))

* DC gain (lowest frequency)
let dc_gain_db = vout_db[0]

* UGB: first frequency where gain crosses 0 dB going down
let ugb_hz = 0
let i = 0
while i lt length(frequency)-1
  if (vout_db[i] gt 0) and (vout_db[i+1] le 0)
    let ugb_hz = frequency[i+1]
  end
  let i = i + 1
end

* Phase margin: phase at the frequency where |gain| = 0 dB
* Find the first sign-change of vout_db
meas ac ugb_meas WHEN vout_db=0 FALL=1
meas ac pm_phase FIND vout_phs WHEN vout_db=0 FALL=1

echo ""
echo "================ Op-amp AC Results ================"
print dc_gain_db
print ugb_hz
echo "==================================================="

wrdata /scratch/opamp_ac.dat vout_db vout_phs
echo "Wrote /scratch/opamp_ac.dat"
.endc

.end
