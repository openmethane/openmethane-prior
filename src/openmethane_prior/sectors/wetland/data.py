#
# Copyright 2025 The Superpower Institute Ltd.
#
# This file is part of OpenMethane.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""SatWetCH4 wetland emissions, published on Zenodo as a 50-member ensemble"""

import hashlib
import os
import pathlib
import tempfile
from collections.abc import Iterator

import netCDF4
import numpy as np
import xarray as xr

from openmethane_prior.lib import ConfiguredDataSource, DataSource, logger
from openmethane_prior.lib.data_manager.fetchers import download_resumable

logger = logger.get_logger(__name__)

SATWET_DOI = "10.5281/zenodo.23965325"
"""Concept DOI, which always resolves to the latest version of the dataset"""

SATWET_URL = (
    "https://zenodo.org/records/23965326/files/SatWetCH4_GIEMS_MC_v2.0_zenodo.nc?download=1"
)
"""Pinned to the v2.0 record so results are reproducible when a new version
is published under the concept DOI"""

SATWET_MD5 = "4336fcbd1c0f500f35a1d060d357a0ec"
"""Checksum of the file at SATWET_URL, as published by Zenodo"""

ENSEMBLE_VARIABLE = "FCH4"
ENSEMBLE_DIM = "calibration_setup"
MEAN_VARIABLE = "fch4_mean"


def satwet_ensemble_mean_blocks(
    ensemble_da: xr.DataArray,
    time_block: int = 12,
) -> Iterator[tuple[slice, np.ndarray]]:
    """Calculate the ensemble mean, one block of time steps at a time.

    The full ensemble is ~82 GB uncompressed, so only one member's block of
    time steps is loaded at a time. When ensemble_da is lazily backed by a
    file, each member block is read from disk as it's needed.

    Parameters
    ----------
    ensemble_da
        Ensemble with dimensions (calibration_setup, time, latitude, longitude)
    time_block
        Number of time steps to process at once. The default matches the
        chunking of the published file, so each chunk is decompressed once.

    Yields
    ------
    tuple[slice, np.ndarray]
        Slice of the time dimension and the float32 mean for those time steps.
        Cells which are NaN in every member are NaN in the mean, otherwise
        NaN members are ignored.
    """
    n_members = ensemble_da.sizes[ENSEMBLE_DIM]
    n_times = ensemble_da.sizes["time"]

    for start in range(0, n_times, time_block):
        time_slice = slice(start, min(start + time_block, n_times))

        # float64 accumulator so the sum of 50 members doesn't lose precision
        # before the division
        total = None
        count = None
        for member in range(n_members):
            values = ensemble_da.isel({ENSEMBLE_DIM: member, "time": time_slice}).values
            valid = np.isfinite(values)
            if total is None:
                total = np.zeros(values.shape, dtype=np.float64)
                count = np.zeros(values.shape, dtype=np.int32)
            total += np.where(valid, values, 0.0)
            count += valid

        with np.errstate(invalid="ignore", divide="ignore"):
            mean = np.where(count > 0, total / count, np.nan)

        yield time_slice, mean.astype(np.float32)


def write_satwet_ensemble_mean(source_path: pathlib.Path, dest_path: pathlib.Path):
    """Write the ensemble mean of a SatWetCH4 ensemble file to a new NetCDF file.

    The output has a single fch4_mean variable on the original global grid.
    Values are stored as float32, the precision of the source data, and are
    compressed losslessly.
    """
    # times are left encoded so their units and calendar are copied as stored
    with xr.open_dataset(source_path, decode_times=False) as source_ds:
        ensemble_da = source_ds[ENSEMBLE_VARIABLE]
        n_members = ensemble_da.sizes[ENSEMBLE_DIM]

        # the published file has units as a global attribute only
        units = ensemble_da.attrs.get("units", source_ds.attrs.get("units"))
        if units is None:
            raise ValueError(f"SatWetCH4 ensemble '{source_path}' has no units")

        with netCDF4.Dataset(dest_path, "w") as dest:
            for dim in ("time", "latitude", "longitude"):
                source_coord = source_ds[dim]
                dest.createDimension(dim, source_coord.size)
                dest_coord = dest.createVariable(dim, source_coord.dtype, (dim,))
                dest_coord.setncatts(source_coord.attrs)
                dest_coord[:] = source_coord.values

            mean_var = dest.createVariable(
                MEAN_VARIABLE,
                np.float32,
                ("time", "latitude", "longitude"),
                zlib=True,
                complevel=6,
                shuffle=True,
                chunksizes=tuple(
                    min(chunk, source_ds.sizes[dim])
                    for chunk, dim in zip((12, 180, 360), ("time", "latitude", "longitude"))
                ),
                fill_value=np.float32(np.nan),
            )
            mean_var.setncatts(
                {
                    "long_name": f"Mean methane flux across {n_members} SatWetCH4 calibrations",
                    "units": units,
                }
            )

            dest.setncatts(
                {
                    "title": "SatWetCH4 v2.0 ensemble mean",
                    "source": SATWET_URL,
                    "doi": SATWET_DOI,
                    "license": "CC-BY-4.0",
                    "history": f"Mean of {n_members} members of '{ENSEMBLE_VARIABLE}' "
                    f"over '{ENSEMBLE_DIM}' calculated by openmethane-prior",
                }
            )

            for time_slice, mean in satwet_ensemble_mean_blocks(ensemble_da):
                logger.debug(f"Writing SatWet ensemble mean for time steps {time_slice}")
                mean_var[time_slice] = mean


def file_md5(path: pathlib.Path, block_size: int = 16 * 1024 * 1024) -> str:
    """Calculate the MD5 hex digest of a file without reading it all into memory."""
    md5 = hashlib.md5(usedforsecurity=False)
    with open(path, "rb") as f:
        while block := f.read(block_size):
            md5.update(block)
    return md5.hexdigest()


def fetch_satwet_ensemble_mean(data_source: ConfiguredDataSource) -> pathlib.Path:
    """Download the SatWetCH4 ensemble and save only its ensemble mean.

    The published ensemble is 9 GB, while the mean is ~170 MB. The download
    is placed in a temporary folder next to the asset and removed once the
    mean has been written:
      - /tmp is often RAM-backed tmpfs, which can't hold the download
      - the asset is moved into place last, so an interrupted fetch never
        leaves a partial file that would be mistaken for a complete asset
    """
    data_source.asset_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".satwet-", dir=data_source.asset_path.parent
    ) as tmp_dir:
        tmp_path = pathlib.Path(tmp_dir)
        ensemble_path = tmp_path / "ensemble.nc"

        logger.info(f"Downloading SatWetCH4 ensemble (9 GB) from {data_source.url}")
        download_resumable(data_source.url, ensemble_path)

        checksum = file_md5(ensemble_path)
        if checksum != SATWET_MD5:
            raise ValueError(f"SatWetCH4 download has MD5 {checksum}, expected {SATWET_MD5}")

        logger.info("Calculating SatWetCH4 ensemble mean")
        mean_path = tmp_path / data_source.asset_path.name
        write_satwet_ensemble_mean(ensemble_path, mean_path)
        os.replace(mean_path, data_source.asset_path)

    return data_source.asset_path


SATWET_MEAN_FILE = "SatWetCH4_GIEMS_MC_v2.0_mean.nc"

satwet_zenodo_data_source = DataSource(
    name="SatWetCH4-v2.0-mean-zenodo",
    url=SATWET_URL,
    file_path=SATWET_MEAN_FILE,
    fetch=fetch_satwet_ensemble_mean,
)
"""Creates the ensemble mean from the original Zenodo dataset, which is the
file satwet_data_source fetches. The prior doesn't use this source directly,
because downloading 9 GB from Zenodo takes ~2 hours.

To regenerate the mean when a new version is published:

1. Update SATWET_URL, SATWET_MD5 and the version in SATWET_MEAN_FILE
2. Fetch this source, which needs ~9 GB of free space next to the asset:

   >>> import datetime, pathlib
   >>> from openmethane_prior.lib.config import PriorConfig
   >>> from openmethane_prior.lib.data_manager.source import configure_data_source
   >>> out = pathlib.Path("data/inputs").resolve()
   >>> config = PriorConfig(domain_path="", start_date=datetime.datetime(2022, 1, 1))
   >>> configure_data_source(
   ...     satwet_zenodo_data_source, config, data_path=out, static_path=out
   ... ).fetch()

3. Upload the result to s3://openmethane/prior/inputs/
"""

satwet_data_source = DataSource(
    name="SatWetCH4-v2.0-mean",
    url=f"https://openmethane.s3.amazonaws.com/prior/inputs/{SATWET_MEAN_FILE}",
)
"""The ensemble mean created by satwet_zenodo_data_source, published to the
openmethane data store for fast and reliable fetching. Both sources share a
file name, so a locally regenerated file is used in place of the published
one."""
