import os
import numpy as np
import rasterio as rio
from rasterio.warp import Resampling, calculate_default_transform, reproject
import xarray as xr

from openmethane_prior.config import PriorConfig


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
    config: PriorConfig,
    AREA_OR_POINT = 'Area'
) -> np.ndarray:
    """
    maps a rasterio dataset onto the domain defined by config.
    returns np.ndarray
    """
    domain_grid = config.domain_grid()

    result = np.zeros(domain_grid.shape)
    count = np.zeros_like(result)

    # we accumulate values from each high-res grid in the raster onto our domain then divide by the number
    # our criterion is that the central point in the high-res lies inside the cell defined on the grid
    # get input coordinates and resolutions, these are not retained in this data structure despite presence in underlying tiff file
    input_field_np = input_field.to_numpy()

    # the following needs .to_numpy() because
    # subtracting xarray matches coordinates, not what we want
    input_lons_np = input_field.x.to_numpy()
    input_lats_np = input_field.y.to_numpy()
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

        cell_x, cell_y, mask = domain_grid.lonlat_to_cell_index(input_lons_np, lats)

        # input domain is bigger so mask indices out of range
        if mask.any():
            # the following needs to use .at method since cell_y,cell_x indices may be repeated and we need to acumulate
            np.add.at(result, (cell_y[mask], cell_x[mask]), input_field_np[j, mask])
            np.add.at(count, (cell_y[mask], cell_x[mask]),  1)

    has_vals = count > 0
    result[has_vals] /= count[has_vals]

    return result