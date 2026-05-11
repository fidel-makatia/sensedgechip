#!/usr/bin/env bash
# Run the op-amp AC sim inside the IIC-OSIC container.
set -euo pipefail

docker run --rm \
  -v /opt/chipathon/designs:/foss/designs \
  -v /opt/chipathon/scratch:/scratch \
  hpretl/iic-osic-tools:latest --skip bash -c '
    set -e
    cd /foss/designs/afe/sim
    echo "=== ngspice version ==="
    ngspice -v 2>&1 | head -1
    echo
    echo "=== running AC sim ==="
    ngspice -b -o /scratch/afe_opamp_ac.log tb_opamp_ac_sky130.sp 2>&1 | tail -30
    echo
    echo "=== ngspice log tail ==="
    tail -30 /scratch/afe_opamp_ac.log
    echo
    echo "=== .dat file head ==="
    head -5 /scratch/afe_opamp_ac.dat 2>&1 || echo "no .dat produced"
  '
