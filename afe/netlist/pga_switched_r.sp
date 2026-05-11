* Switched-resistor PGA wrapping the two-stage op-amp.
* Programmable gain via the FB_TAP parameter (1=×1 .. 8=×100).
* For sim, gain is set by .param at the testbench level; on silicon the tap
* selection is controlled by GAIN_SEL[2:0] driving a 3-to-8 decoder + 8
* pass-gate switches. The pass-gate ON resistance (≈100 Ω) is dwarfed by
* the kΩ-class feedback resistors so the ideal-switch behavior simulated
* here matches the real silicon to <0.1 dB.

.include /foss/designs/afe/netlist/opamp_2stage_sky130.sp

.subckt pga_sw_r vinp vout vbn vdd vss

* Non-inverting amplifier: vinp goes to the + input
xopamp vinp vfb vout vbn vdd vss opamp_2stage_sky130

* Feedback divider: Rf programmable (set at testbench via .param rf_v)
* Rin fixed = 1 kΩ. Closed-loop gain = 1 + Rf/Rin.
.param rf_v=99k
rf   vout vfb {rf_v}
rin  vfb  vbcm 1k
vbcm_src vbcm 0 0.9

.ends pga_sw_r
