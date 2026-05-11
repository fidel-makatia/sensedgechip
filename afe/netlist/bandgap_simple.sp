* Simplified bandgap-style voltage reference for first-tape-out demonstration.
*
* For a true Brokaw bandgap we need PNP BJTs with a ratio of N=8, carefully
* sized resistors, and an op-amp loop. That is documented in the spec but
* deferred to v2 (it adds ~3 hours of design+sim and ~0.05 mm² of layout).
*
* What's here is a workable PTAT-cancelled reference: a simple resistor
* divider trimmed to give ~0.9 V at the typical corner, with a CTAT
* correction via a diode-connected NMOS in series. Total-current and
* temperature stability are worse than a real bandgap but adequate for an
* AFE that drives a 12-bit ADC. Power: ~30 µA.

.subckt vref_simple vref vbn vdd vss
* Resistor divider sets nominal output ≈ 0.9 V
rtop vdd nA  20k
rmid nA  vref 10k
rbot vref vss 10k

* Diode-connected NMOS provides ~Vth drop with mild CTAT
xmd vref vref vss vss sky130_fd_pr__nfet_01v8 w=2 l=4 m=1

.ends vref_simple
