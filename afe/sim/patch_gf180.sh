#!/usr/bin/env bash
# Patch GF180 ngspice models to set the unresolved $ defaults to 0.
# Must be run INSIDE the IIC-OSIC container.
set -euo pipefail

SRC=/foss/pdks/gf180mcuD/libs.tech/ngspice/sm141064.ngspice
DST=/scratch/sm141064_patched.ngspice

cp "$SRC" "$DST"

# Replace =$ with =0 — one sed expression per parameter
sed -i 's/par_vth=\$/par_vth=0/g'     "$DST"
sed -i 's/par_k=\$/par_k=0/g'         "$DST"
sed -i 's/par_l=\$/par_l=0/g'         "$DST"
sed -i 's/par_w=\$/par_w=0/g'         "$DST"
sed -i 's/par_leff=\$/par_leff=0/g'   "$DST"
sed -i 's/par_weff=\$/par_weff=0/g'   "$DST"
sed -i 's/p_sqrtarea=\$/p_sqrtarea=0/g' "$DST"
sed -i 's/var_k=\$/var_k=0/g'         "$DST"
sed -i 's/var_vth=\$/var_vth=0/g'     "$DST"

# Some variants may use the form  pars = "...=$..."  inside .model lines —
# also catch unparenthesised $ at end of line
sed -i 's/=\$$/=0/g' "$DST"

echo "patched lines:"
diff "$SRC" "$DST" | head -5
echo "..."
diff "$SRC" "$DST" | wc -l
