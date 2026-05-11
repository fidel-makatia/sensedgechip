* AFE top-level: input → PGA → S/H → output
* For first-tape-out the AFE has these external pins:
*   VINP   – differential input plus  (single-ended for now)
*   VOUT   – sampled output to SAR ADC
*   PHI1   – sample clock from digital chiplet
*   PHI1A  – early-close phase (generated locally from PHI1 or externally)
*   GAIN_SEL[2:0] – future: 8-level gain control
*   VDD, VSS, VREF, VBN

.include /foss/designs/afe/netlist/pga_switched_r.sp
.include /foss/designs/afe/netlist/sh_bottom_plate.sp
.include /foss/designs/afe/netlist/bandgap_simple.sp

.subckt afe_top vinp vout phi1 phi1a vbn vdd vss

* On-chip reference (for monitoring)
xvref vref vbn vdd vss vref_simple

* PGA: input → amplified
xpga vinp vpga_out vbn vdd vss pga_sw_r

* S/H on the PGA output
xsh vpga_out vout phi1 phi1a vbn vdd vss sh_bp

.ends afe_top
