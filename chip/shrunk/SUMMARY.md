# Shrunk digital chip — 2.2 × 2.2 mm

Re-closed with tighter floorplan to fit Chipathon shuttle slot allocations.

## Key changes vs original 3.0 × 3.0 mm build

| Knob | Original | Shrunk |
|---|---|---|
| `DIE_AREA` | `[0, 0, 3000, 3000]` (9 mm²) | `[0, 0, 2200, 2200]` (**4.84 mm²**) |
| `FP_CORE_UTIL` | 35 | **60** |
| `PL_TARGET_DENSITY` | 0.45 | **0.65** |

All other settings (250 ns clock, 9-track lib, Metal4 max, GRT_ALLOW_CONGESTION,
no antenna repair, etc.) kept identical.

## Sign-off metrics

| | Original | Shrunk |
|---|---|---|
| Die area | 9.00 mm² | **4.84 mm² (46 % smaller)** |
| Cell area | 8.84 mm² | 4.72 mm² |
| Cell count | 265,015 | 157,056 |
| Utilization | 26.19 % | 46.43 % |
| Setup worst slack | +31.86 ns | **+32.27 ns** ✅ |
| Hold worst slack | +0.184 ns | +0.183 ns ✅ |
| Setup TNS | 0 | 0 ✅ |
| Hold TNS | 0 | 0 ✅ |
| LVS errors | 0 | **0** ✅ |
| Magic DRC errors | 0 | **0** ✅ |
| Route DRC errors | 0 | 0 ✅ |
| GDS size | 84 MB | 75 MB |

## Reproducing

```bash
docker run --rm -v $PWD/chip:/foss/designs/sensedge \
  hpretl/iic-osic-tools:latest --skip \
  librelane --pdk-root /foss/pdks --skip Checker.YosysSynthChecks \
  /foss/designs/sensedge/openlane/config_small.json
```
