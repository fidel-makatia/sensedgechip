#!/usr/bin/env bash
# Run the op-amp Magic layout script inside the IIC-OSIC container.
set -euo pipefail

mkdir -p /opt/chipathon/scratch/afe_layout
cp /opt/chipathon/designs/afe/layout/opamp_layout.tcl \
   /opt/chipathon/scratch/afe_layout/

docker run --rm \
  -v /opt/chipathon/designs:/foss/designs \
  -v /opt/chipathon/scratch:/scratch \
  hpretl/iic-osic-tools:latest --skip bash -c '
    cd /scratch/afe_layout
    export PDK_ROOT=/foss/pdks
    magic \
      -dnull -noconsole \
      -rcfile /foss/pdks/gf180mcuD/libs.tech/magic/gf180mcuD.magicrc \
      opamp_layout.tcl 2>&1 | tail -40
    echo
    echo === outputs ===
    ls -la /scratch/afe_layout/ | head -10
  '
