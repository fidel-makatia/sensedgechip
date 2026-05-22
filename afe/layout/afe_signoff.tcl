# Magic Tcl: extract afe_top with proper port labels promoted from the
# metal1 pad shapes that were placed by build_final.py.
#
# Workflow:
#   1. Load the GDS
#   2. Promote labels to ports via `port make default`
#   3. Re-place port labels at known pad coordinates if the GDS
#      labels weren't picked up (use `label` + `port` commands)
#   4. Extract + ext2spice for LVS

gds read afe_final
load afe_top

# Pad positions (must match build_final.py)
# DIE_W=700, pads start x=20, pitch=(700-40)/12=55, pad_w=35, pad_h=50
# pad_y = 500 - 50 - 10 = 440, label center y = 465
set pads {VDD VSS VINP VOUT PHI1 PHI1A GAIN0 GAIN1 GAIN2 VREF VBN TEST}
set pitch [expr {(700 - 40) / 12.0}]
set i 0
foreach p $pads {
    set cx [expr {20 + $i * $pitch + 35/2.0}]
    set cy 465
    # Move box to pad position, paint a label
    box position ${cx}um ${cy}um
    box size 0.5um 0.5um
    label "$p" s metal1
    incr i
}

# Promote all labels to ports
port makeall
puts "Created ports:"
port first
while {[port last] >= [port name]} {
    puts "  [port name]"
    port next
}

# Extract — let cells expand
extract all

# Generate SPICE
ext2spice lvs
ext2spice cthresh infinite
ext2spice -p . -o afe_top_extracted.spice afe_top.ext

quit -noprompt
