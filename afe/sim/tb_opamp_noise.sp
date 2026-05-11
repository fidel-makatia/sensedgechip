* Input-referred noise — integrated 1 Hz to 100 kHz
.lib /foss/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice tt
.include /foss/designs/afe/netlist/opamp_2stage_sky130.sp

.param vdd_v=1.8
.param vcm_v=0.9
.param vbn_v=0.7

vdd  vdd  0  {vdd_v}
vss  vss  0  0
vbn  vbn  0  {vbn_v}
vinp vinp 0 dc {vcm_v} ac 1
vinn vinn 0 dc {vcm_v}

xdut vinp vinn vout vbn vdd vss opamp_2stage_sky130
cload vout vss 5p

.control
set noaskquit
noise v(vout) vinp dec 10 1 100k
* The "onoise_spectrum" and "inoise_spectrum" vectors are produced.
* Total integrated input-referred noise (1 Hz – 100 kHz):
let inoise_rms = sqrt(integ(inoise_spectrum))
echo ""
echo "================ Noise Results ================"
print inoise_rms[length(inoise_rms)-1]
echo "==============================================="
wrdata /opt/chipathon/scratch/opamp_noise.dat inoise_spectrum onoise_spectrum
.endc
.end
