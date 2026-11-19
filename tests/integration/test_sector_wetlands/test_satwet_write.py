import numpy as np
import pandas as pd
import pytest
import xarray as xr

from openmethane_prior.sectors.wetland.data import write_satwet_ensemble_mean


@pytest.fixture()
def ensemble_path(tmp_path):
    """A small file laid out like the published SatWetCH4 ensemble, with
    units only in the global attributes."""
    rng = np.random.default_rng(seed=1)
    values = rng.random((4, 14, 3, 2), dtype=np.float32)
    values[:, :, 0, 0] = np.nan
    ds = xr.Dataset(
        {"FCH4": (("calibration_setup", "time", "latitude", "longitude"), values)},
        coords={
            "calibration_setup": np.arange(4),
            "time": pd.date_range("1992-01-01", periods=14, freq="MS"),
            "latitude": np.array([-10.125, -9.875, -9.625], dtype=np.float32),
            "longitude": np.array([130.125, 130.375], dtype=np.float32),
        },
        attrs={"units": "gCH4/m2/month"},
    )
    ds["latitude"].attrs = {"units": "degrees_north", "standard_name": "latitude"}
    path = tmp_path / "ensemble.nc"
    ds.to_netcdf(path)
    return path


def test_write_satwet_ensemble_mean(ensemble_path, tmp_path):
    dest_path = tmp_path / "mean.nc"

    write_satwet_ensemble_mean(ensemble_path, dest_path)

    with xr.open_dataset(ensemble_path) as source_ds, xr.open_dataset(dest_path) as mean_ds:
        assert list(mean_ds.data_vars) == ["fch4_mean"]
        assert mean_ds["fch4_mean"].dims == ("time", "latitude", "longitude")
        assert mean_ds["fch4_mean"].dtype == np.float32
        assert mean_ds["fch4_mean"].attrs["units"] == "gCH4/m2/month"
        xr.testing.assert_identical(mean_ds["time"], source_ds["time"])
        assert mean_ds["latitude"].attrs == source_ds["latitude"].attrs
        np.testing.assert_array_equal(mean_ds["latitude"], source_ds["latitude"])
        np.testing.assert_array_equal(mean_ds["longitude"], source_ds["longitude"])
        np.testing.assert_allclose(
            mean_ds["fch4_mean"].values,
            source_ds["FCH4"].mean("calibration_setup").values,
            rtol=1e-6,
        )
        assert np.isnan(mean_ds["fch4_mean"][:, 0, 0]).all()
