import os
from typing import Literal

import numpy as np
import rasterio as rio
import xarray as xr
from rasterio.warp import Resampling, calculate_default_transform, reproject

from openmethane_prior.config import PriorConfig
from openmethane_prior.utils import domain_cell_index


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
    input_field: xr.DataArray, config: PriorConfig, AREA_OR_POINT: Literal["Area", "Point"] = "Area"
) -> np.ndarray:
    """
    Map a rasterio dataset onto the domain defined by config.

    We accumulate values from each high-res grid in the raster onto our domain
    then divide by the number of high-res points in each domain cell.

    Our criterion is that the central point in the high-res lies inside the cell
    defined on the grid input coordinates and resolutions,
    these are not retained in this data structure despite presence in underlying tiff file
    """
    # any field will do and select only horizontal dims
    result = np.zeros(config.domain_dataset()["LAT"].shape[-2:])
    count = np.zeros_like(result)
    lons = input_field.x.to_numpy()
    # the following needs .to_numpy() because
    # subtracting xarray matches coordinates, not what we want
    delta_lon = (input_field.x.to_numpy()[1:] - input_field.x.to_numpy()[0:-1]).mean()
    delta_lat = (input_field.y.to_numpy()[1:] - input_field.y.to_numpy()[0:-1]).mean()
    # output resolutions and extents
    lmx = result.shape[-1]
    lmy = result.shape[-2]
    input_field_as_array = input_field.to_numpy()
    # the raster is defined lat-lon so we need to reproject each row separately onto the LCC grid
    for j in range(input_field.y.size):
        lat = input_field.y.item(j)
        lats = np.array([lat]).repeat(lons.size)  # proj needs lats,lons same size

        # correct for point being corner or centre of box, we want centre
        if AREA_OR_POINT.lower() == "area":
            lons_cell = lons + delta_lon / 2.0
            lats_cell = lats + delta_lat / 2
        elif AREA_OR_POINT.lower() == "point":
            lons_cell = lons.copy()
            lats_cell = lats.copy()
        else:
            raise ValueError(f"Unknown area_or_point: {AREA_OR_POINT}")

        ix, iy = domain_cell_index(config, lons_cell, lats_cell)
        # input domain is bigger so mask indices out of range
        mask = (ix >= 0) & (ix < lmx) & (iy >= 0) & (iy < lmy)
        if mask.any():
            # the following needs to use .at method since iy,ix indices may be repeated
            # and we need to acumulate
            np.add.at(result, (iy[mask], ix[mask]), input_field_as_array[j, mask])
            np.add.at(count, (iy[mask], ix[mask]), 1)
    has_vals = count > 0
    result[has_vals] /= count[has_vals]
    return result
