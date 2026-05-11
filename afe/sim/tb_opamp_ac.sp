* AC analysis of opamp_2stage — gain, phase, UGB, phase margin
* GF180MCU 5V, TT corner, 27 C

* Statistical-variation params required by GF180 subckts (nominal = 0)
.param par_vth=0 par_k=0 par_l=0 par_w=0 par_leff=0 par_weff=0
.param p_sqrtarea=0 var_k=0 var_vth=0

.include /foss/pdks/gf180mcuD/libs.tech/ngspice/design.ngspice
.include /foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064.ngspice
.include /foss/designs/afe/netlist/opamp_2stage.sp

.param vdd_v=5.0
.param vcm_v=1.0       ;* input common-mode mid-rail for NMOS-input pair
.param vbn_v=0.9       ;* tail bias

* Supplies
vdd  vdd  0  {vdd_v}
vss  vss  0  0
vbn  vbn  0  {vbn_v}

* DC input common mode + small AC stimulus
* Use a unity-gain configuration to measure open-loop with AC injection
vinp_dc  vinp_dc  0  {vcm_v}
vinn_dc  vinn_dc  0  {vcm_v}
* AC source on vinp only — measures vout / vinp differentially
vac      vac      0  dc 0 ac 1

* Series link of DC + AC into vinp:
e_inp vinp 0 vol='{vcm_v} + V(vac)'
e_inn vinn 0 vol='{vcm_v}'

* DUT
xdut vinp vinn vout vbn vdd vss opamp_2stage

* Load (≈ next stage + parasitic)
cload vout vss 5p

.control
set noaskquit
set ngbehavior=hsa
ac dec 30 1 1g

* Save magnitudes/phases of vout in dB
let vout_db   = db(v(vout))
let vout_phs  = 180/3.14159265 * cph(v(vout))

* Print headline numbers
let dc_gain_db = vout_db[0]
let ugb_hz     = 0
let i=0
while i lt length(frequency)-1
  if (vout_db[i] gt 0) and (vout_db[i+1] le 0)
    let ugb_hz = frequency[i]
  end
  let i = i + 1
end
let pm = vout_phs[$&ugb_hz_idx] + 180

echo "=== opamp_2stage AC results ==="
echo "DC open-loop gain (dB):"
print dc_gain_db
echo "Unity-gain bandwidth (Hz, approx):"
print ugb_hz

* Dump for plotting
wrdata /scratch/afe_opamp_ac.dat vout_db vout_phs

.endc

.end
