* Bottom-plate-sampled S/H with non-overlapping phases.
* Φ1   samples (top switch and bottom switch closed)
* Φ1a  opens *slightly before* Φ1 — bottom switch opens first, the cap holds
*       the sampled value before the top switch's charge injection can affect it
* Φ2   hold (both switches open, buffer drives output)
*
* On the chip the switches are NMOS or transmission gates; here for sim
* we model them as ideal voltage-controlled switches.

.include /foss/designs/afe/netlist/opamp_2stage_sky130.sp

.subckt sh_bp vin vout phi1 phi1a vbn vdd vss

* Top switch: connects vin to the sample cap (controlled by phi1)
sw_top vin v_top phi1 vss switch_mod

* Bottom switch: connects bottom of cap to mid-rail (controlled by phi1a)
sw_bot v_bot vmid phi1a vss switch_mod

* Sampling capacitor (5 pF — chosen for kT/C noise floor)
csamp v_top v_bot 5p

* Hold-mode buffer: opamp in unity-gain config, drives output
xbuf v_top vout vout vbn vdd vss opamp_2stage_sky130

* Mid-rail bias
vmid_src vmid 0 0.9

.model switch_mod sw vt=0.9 vh=0.05 ron=100 roff=1g
.ends sh_bp
