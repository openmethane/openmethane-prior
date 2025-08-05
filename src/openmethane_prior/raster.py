import os
import numpy as np
import pyproj
import rasterio as rio
from rasterio.warp import Resampling, calculate_default_transform, reproject
import xarray as xr

from openmethane_prior.config import PriorConfig
from openmethane_prior.grid.grid import Grid


def reproject_tiff(image, output, dst_crs="EPSG:4326", resampling="nearest", **kwargs):
    """Reprojects an image.

    Based on samgeo.common.reproject

    Args:
        image (str): The input image filepath.
        output (str): The output image filepath.
        dst_crs (str, optional): The destination CRS. Defaults to "EPSG:4326".
        resampling (Resampling, optional): The resampling method. Defaults to "nearest".
        **kwargs: Additional keyword arguments to pass to rasterio.open.

    """
    if isinstance(resampling, str):
        resampling = getattr(Resampling, resampling)

    image = os.path.abspath(image)
    output = os.path.abspath(output)

    if not os.path.exists(os.path.dirname(output)):
        os.makedirs(os.path.dirname(output))

    with rio.open(image, **kwargs) as src:
        transform, width, height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds
        )
        kwargs = src.meta.copy()
        kwargs.update(
            {
                "crs": dst_crs,
                "transform": transform,
                "width": width,
                "height": height,
            }
        )

        with rio.open(output, "w", **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rio.band(src, i),
                    destination=rio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=dst_crs,
                    resampling=resampling,
                    **kwargs,
                )


def reproject_raster_inputs(config: PriorConfig):
    """Re-project raster files to match domain"""
    print("### Re-projecting raster inputs...")
    reproject_tiff(
        str(config.as_input_file(config.layer_inputs.land_use_path)),
        str(config.as_intermediate_file(config.layer_inputs.land_use_path)),
        config.crs,
    )
    reproject_tiff(
        str(config.as_input_file(config.layer_inputs.ntl_path)),
        str(config.as_intermediate_file(config.layer_inputs.ntl_path)),
        config.crs,
    )


def remap_raster(
    input_field: xr.DataArray,
    target_grid: Grid,
    input_crs: pyproj.crs.CRS = 4326, # EPSG:4362
    AREA_OR_POINT = 'Area',
) -> np.ndarray:
    """
    Maps a rasterio dataset onto the domain grid defined by config.

    If the input dataset uses a non-standard CRS, input coordinates can be
    mapped to the grid by specifying input_crs.

    Returns an np.array in the shape of the domain grid, each cell containing
    the aggregate of raster values who's center point fell within the cell.
    """
    projection_transformer = pyproj.Transformer.from_crs(crs_from=input_crs, crs_to=target_grid.projection.crs, always_xy=True)

    result = np.zeros(target_grid.shape)

    # we accumulate values from each high-res grid in the raster onto our domain then divide by the number
    # our criterion is that the central point in the high-res lies inside the cell defined on the grid
    # get input coordinates and resolutions, these are not retained in this data structure despite presence in underlying tiff file
    input_field_np = input_field.to_numpy().squeeze()

    # the following needs .to_numpy() because
    # subtracting xarray matches coordinates, not what we want
    input_lons_np = input_field.x.to_numpy().copy()
    input_lats_np = input_field.y.to_numpy().copy()
    delta_lon = (input_lons_np[1:] - input_lons_np[0:-1]).mean()
    delta_lat = (input_lats_np[1:] - input_lats_np[0:-1]).mean()

    # correct for source points locating the corner, we want centre
    if AREA_OR_POINT == 'Area':
        input_lons_np += delta_lon / 2
        input_lats_np += delta_lat / 2

    # the raster is defined lat-lon so we need to reproject each row separately onto the LCC grid
    for j in range(input_lats_np.size):
        lat = input_lats_np.item(j)
        lats = np.array([lat]).repeat(input_field.x.size) # proj needs lats,lons same size

        input_x, input_y = projection_transformer.transform(xx=input_lons_np, yy=lats)
        cell_x, cell_y, mask = target_grid.xy_to_cell_index(input_x, input_y)

        # input domain is bigger so mask indices out of range
        if mask.any():
            # the following needs to use .at method since cell_y,cell_x indices may be repeated and we need to acumulate
            np.add.at(result, (cell_y[mask], cell_x[mask]), input_field_np[j, mask])

    return result
