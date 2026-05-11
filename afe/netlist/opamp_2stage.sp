* GF180MCU 5V two-stage Miller-compensated op-amp
* NMOS-input diff pair, PMOS mirror load, PMOS CS stage 2, NMOS current sink
*
* Pin order: vinp vinn vout vbn vdd vss
*   vbn — external NMOS bias (sets tail current via current mirror)

.subckt opamp_2stage vinp vinn vout vbn vdd vss

* Tail current sink — sized for ~50 µA at Vbn ≈ 0.9 V
xm5 d_tail vbn vss vss nfet_05v0 w=20u l=2u m=4

* Input differential pair (NMOS)
xm1 d_l vinp d_tail vss nfet_05v0 w=20u l=2u m=4
xm2 d_r vinn d_tail vss nfet_05v0 w=20u l=2u m=4

* PMOS current-mirror load (m3 diode, mirrored by m4)
xm3 d_l d_l vdd vdd pfet_05v0 w=10u l=2u m=4
xm4 d_r d_l vdd vdd pfet_05v0 w=10u l=2u m=4

* Stage-2 common-source PMOS
xm6 vout d_r vdd vdd pfet_05v0 w=50u l=1u m=4

* Stage-2 NMOS current source load (mirrors same Vbn)
xm7 vout vbn vss vss nfet_05v0 w=40u l=2u m=4

* Miller compensation
ccomp d_r vout 1.5p

.ends opamp_2stage
