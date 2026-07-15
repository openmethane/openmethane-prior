# Visualising prior outputs

Prior emissions are written to NetCDF in `data/outputs/` (default filename
`prior-emissions.nc`). All methane flux layers use the CF-standard unit
**`kg/m2/s`** (kilograms of methane per square metre per second).

These units are correct for model interchange, but the numeric values are often
very small (frequently `1e-11` to `1e-8`). That can make quick visual inspection
awkward in Python, QGIS, or other GIS tools unless values are converted for
display or plotted on a logarithmic scale.

This document describes recommended **display conversions** and a basic **QGIS
workflow**. It does not change the canonical NetCDF output format.

Resolves the discussion in [issue #206](https://github.com/openmethane/openmethane-prior/issues/206).

## Output variables

The main variables of interest are:

| Variable | Description |
| -------- | ----------- |
| `ch4_total` | Total methane flux across all sectors |
| `ch4_sector_*` | Per-sector flux layers (e.g. `ch4_sector_livestock`) |
| `land_mask` | Binary land/sea mask (useful for context maps) |

Each flux variable includes `units = "kg/m2/s"` in its metadata.

## Why values look "small"

Flux is reported **per second** and **per square metre**. A cell emitting
`2e-8 kg/m2/s` is equivalent to roughly **1.7 g/m²/day** — a more intuitive
magnitude for maps, but still stored in SI flux units in the NetCDF file.

## Recommended display conversions

Let `flux` be a value in `kg/m2/s`.

### Per unit area

| Display unit | Formula | Notes |
| ------------ | ------- | ----- |
| **g/m²/day** | `flux × 86400 × 1000` | Often easier to read on maps |
| **ng/m²/s** | `flux × 1e9` | Same quantity, larger numeric scale |
| **t/m²/day** | `flux × 86400 / 1000` | Useful for very large sources |

Example: if `ch4_total` max = `2.2e-8 kg/m2/s`, then max ≈ **1.9 g/m²/day**.

### Per grid cell (totals)

To estimate emissions from a whole grid cell over a period, multiply by cell
area and elapsed time:

```
kg/day per cell = flux_kg_m2_s × cell_area_m2 × 86400
kg/year per cell = flux_kg_m2_s × cell_area_m2 × 86400 × 365
```

Cell area can be approximated from domain attributes `DX` and `DY` (in metres):

```
cell_area_m2 = DX × DY
```

For the default `aust10km` domain, `DX = DY = 10000`, so `cell_area_m2 = 1e8`.

These totals are useful for sanity checks; they are not a substitute for formal
inventory reconciliation.

### Python example

```python
import xarray as xr

ds = xr.open_dataset("data/outputs/prior-emissions.nc")
flux = ds["ch4_total"]  # kg/m2/s

g_per_m2_day = flux * 86400 * 1000
cell_area_m2 = float(ds.DX) * float(ds.DY)
kg_per_day = flux * cell_area_m2 * 86400

print("max flux (kg/m2/s):", float(flux.max()))
print("max flux (g/m2/day):", float(g_per_m2_day.max()))
print("max cell total (kg/day):", float(kg_per_day.max()))
```

## QGIS workflow

### Option A: Open the NetCDF directly

1. **Layer → Add Layer → Add Raster Layer**
2. Select `data/outputs/prior-emissions.nc`
3. Choose the sub-dataset (e.g. `ch4_total`) when prompted

The layer uses the Lambert Conformal projection stored in the file. For overlay
with WGS84 basemaps, enable **on-the-fly reprojection** (QGIS does this by
default).

### Option B: Use a GeoTIFF export

If you already have a WGS84 GeoTIFF (e.g. `ch4_total_wgs84.tif` in
`data/outputs/`), add it as a raster layer. This avoids sub-dataset selection
and is often simpler for quick maps.

### Symbology: use a log scale

Linear colour scales compress most flux values near zero and make spatial
patterns hard to see.

1. Open **Layer Properties → Symbology**
2. Change render type to **Singleband pseudocolor** (or **Paletted/Unique values** for masks)
3. For flux layers, set **Min/max value settings** to **Min/max** or **Percentile**
4. Enable **Logarithmic** scale (or use a **Symbology → Min/max → Load** on
   `log10(flux + epsilon)` via Raster Calculator)

For `land_mask`, use a simple two-colour palette.

### Raster Calculator (display units)

To create a temporary visualisation layer in **g/m²/day**:

```
"ch4_total@1" * 86400 * 1000
```

(Adjust the band/layer name to match your import.)

Label the legend clearly, e.g. **g CH₄/m²/day (derived from kg/m²/s)**.

### Common pitfalls

- **Tiny linear colour range** — switch to log symbology or convert units first.
- **Sea vs land** — mask with `land_mask` or hide ocean cells when inspecting
  terrestrial sectors.
- **Time dimension** — output may include a `time` dimension; select a single
  timestep before mapping or use the temporal controller.
- **Comparing to inventory totals** — flux maps show spatial *distribution*;
  sector totals require integrating over area and time.

## Related material

- [Outputs section in README](../README.md#outputs)
- [Data sources](./data-sources.md)
- Legacy scripts (`plot_emis.ncl`, notebooks in `notebooks/`) exist but are not
  actively maintained; prefer this guide and direct QGIS/Python inspection.

## Future work

A standalone script or utility to export visualisation-ready GeoTIFFs (e.g.
g/m²/day) or print summary statistics may be added later. Documentation-only
changes are the first step; see issue #206 for discussion.
