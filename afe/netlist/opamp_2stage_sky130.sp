* SKY130 1.8V two-stage Miller-compensated op-amp — v2 (high-gain)
* Same topology as the GF180 5V target; sized for higher rout via longer L
* on the current-source loads.
*
* Pin order: vinp vinn vout vbn vdd vss

.subckt opamp_2stage_sky130 vinp vinn vout vbn vdd vss

* Tail current sink — long L for high rout
xm5 d_tail vbn vss vss sky130_fd_pr__nfet_01v8 w=4 l=2 m=2

* Input differential pair (NMOS) — wide for gm, long for matching
* Convention: vinp (+) drives M2 whose drain (d_r) is the output-side node.
* M1 (vinn, −) drives the diode side (d_l). This makes V(vout) increase
* when V(vinp) > V(vinn) — i.e. proper non-inverting transfer.
xm1 d_l vinn d_tail vss sky130_fd_pr__nfet_01v8 w=20 l=2 m=2
xm2 d_r vinp d_tail vss sky130_fd_pr__nfet_01v8 w=20 l=2 m=2

* PMOS current-mirror load — long L for high rout
xm3 d_l d_l vdd vdd sky130_fd_pr__pfet_01v8 w=10 l=2 m=2
xm4 d_r d_l vdd vdd sky130_fd_pr__pfet_01v8 w=10 l=2 m=2

* Stage-2 common-source PMOS — wide for high gm
xm6 vout d_r vdd vdd sky130_fd_pr__pfet_01v8 w=40 l=1 m=2

* Stage-2 NMOS current-source load — long L for high rout
xm7 vout vbn vss vss sky130_fd_pr__nfet_01v8 w=20 l=2 m=2

* Miller compensation — 3 pF for >60° PM at 5 pF load
ccomp d_r vout 3p

* Nulling resistor (zero cancellation): R_z ≈ 1/gm6 ≈ 1.5 kΩ
* Series with Cc to push the RHP zero into the LHP (or push to infinity)
* For a first pass, skip the resistor — Cc alone gives adequate PM at 1 nF.

.ends opamp_2stage_sky130
