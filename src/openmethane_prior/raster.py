import os

import rasterio as rio
from openmethane_prior.config import PriorConfig
from rasterio.warp import Resampling, calculate_default_transform, reproject


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
