# Visualising prior outputs

After a run, emissions layers are written to NetCDF in `data/outputs/`
(default filename `prior-emissions.nc`). Flux variables such as `ch4_total`
and `ch4_sector_*` use the unit **`kg/m2/s`**.

Those values are often very small (commonly `1e-11` to `1e-8`). That is
expected for a per-second, per-square-metre flux, but it makes maps hard to read
unless you convert units for display or use a logarithmic colour scale.

## Main variables

| Variable | Description |
| -------- | ----------- |
| `ch4_total` | Total methane flux across all sectors |
| `ch4_sector_*` | Per-sector flux (e.g. `ch4_sector_coal`, `ch4_sector_transport`) |
| `land_mask` | Land/sea mask |

## Display unit conversions

These conversions are for **inspection and mapping only**. The NetCDF file
keeps `kg/m2/s`.

Let `flux` be a value in `kg/m2/s`.

| Display unit | Formula |
| ------------ | ------- |
| g/m²/day | `flux × 86400 × 1000` |
| ng/m²/s | `flux × 1e9` |

Example: `2.2e-8 kg/m2/s` ≈ **1.9 g/m²/day**.

### Per-cell totals

To estimate emissions from one grid cell over a day:

```
kg/day per cell = flux_kg_m2_s × cell_area_m2 × 86400
```

Open Methane domains use a **rectilinear grid** with constant cell size. Cell
area is:

```
cell_area_m2 = DX × DY
```

where `DX` and `DY` (metres) are stored as attributes on the output file. For
the default `aust10km` domain, `DX = DY = 10000`, so each cell is
`1 × 10⁸ m²`.

### Python check

```python
import xarray as xr

ds = xr.open_dataset("data/outputs/prior-emissions.nc")
flux = ds["ch4_total"]  # kg/m2/s

g_per_m2_day = flux * 86400 * 1000
cell_area_m2 = float(ds.DX) * float(ds.DY)
kg_per_day = flux * cell_area_m2 * 86400

print("max flux (kg/m2/s):", float(flux.max()))
print("max flux (g/m2/day):", float(g_per_m2_day.max()))
```

## QGIS workflow

These steps assume QGIS 3.x and a completed local run with
`data/outputs/prior-emissions.nc` present.

### Load a flux layer

1. **Layer → Add Layer → Add Raster Layer**
2. Select `prior-emissions.nc`
3. When prompted, choose the subdataset for the variable you want (e.g.
   `ch4_total`)

The raster uses the Lambert Conformal projection from the domain file. QGIS
reprojects on the fly for WGS84 basemaps by default.

If your output has a `time` dimension, pick one timestep (Temporal Controller or
by exporting a single band) before mapping.

### Symbology

Linear scales often hide spatial structure because most cells are near zero.

1. **Layer Properties → Symbology**
2. Render type: **Singleband pseudocolor**
3. Min/max: **Min/max** or **Percentile**
4. Check **Logarithmic** (under min/max settings, depending on QGIS version)

Use a simple palette for `land_mask`.

### Convert to g/m²/day in QGIS

**Raster → Raster Calculator**:

```
"ch4_total@1" * 86400 * 1000
```

Adjust the layer/band name to match your import. Label the legend as g/m²/day.

### Comparing more than one layer

QGIS applies symbology **independently** to each layer. If you overlay
`ch4_sector_coal` and `ch4_sector_transport`, each layer is stretched to its
own min/max. A saturated colour on transport does **not** mean it has the same
flux as coal — coal values are often orders of magnitude larger.

To compare sectors fairly:

- use the **same display unit** (e.g. g/m²/day) on each layer, and
- set **matching min/max** or **percentile** ranges manually, or
- compare layers one at a time, or
- subtract layers (Raster Calculator) when looking at before/after or
  difference maps.

### Export a GeoTIFF (optional)

To share a map or reload it without selecting NetCDF subdatasets:

1. Load and style the layer as above
2. **Project → Export → Export Map to Raster** for a map image, or
3. **Right-click layer → Export → Save As…** to write a GeoTIFF (choose target
   CRS, e.g. EPSG:4326, if you need WGS84)

There is no built-in prior step that writes GeoTIFFs automatically; export from
QGIS or a separate script if you need them.

## Common pitfalls

- **Linear colour scale on raw `kg/m2/s`** — use log symbology or g/m²/day first.
- **Overlaying sectors without shared scaling** — colours are not comparable
  (see above).
- **Ocean cells** — mask with `land_mask` when inspecting land-based sectors.
- **Inventory totals** — maps show spatial distribution; integrating flux over
  area and time is a separate calculation.

## See also

- [Outputs](../README.md#outputs) in the README
- [Data sources](./data-sources.md)
