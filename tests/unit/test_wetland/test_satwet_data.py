import numpy as np
import pandas as pd
import pytest
import xarray as xr

from openmethane_prior.sectors.wetland.data import satwet_ensemble_mean_blocks


@pytest.fixture()
def ensemble_da():
    # 3 members, 5 monthly time steps, 2x2 grid; member m has value m + t
    members, times = 3, 5
    values = (
        np.arange(members, dtype=np.float32)[:, None, None, None]
        + np.arange(times, dtype=np.float32)[None, :, None, None]
        + np.zeros((1, 1, 2, 2), dtype=np.float32)
    )
    return xr.DataArray(
        values,
        dims=("calibration_setup", "time", "latitude", "longitude"),
        coords={
            "calibration_setup": np.arange(members),
            "time": pd.date_range("2022-01-01", periods=times, freq="MS"),
            "latitude": [-10.125, -9.875],
            "longitude": [130.125, 130.375],
        },
    )


def test_satwet_ensemble_mean_blocks(ensemble_da):
    blocks = list(satwet_ensemble_mean_blocks(ensemble_da, time_block=2))

    # the final block is shorter, covering the remaining time step
    assert [time_slice for time_slice, _ in blocks] == [slice(0, 2), slice(2, 4), slice(4, 5)]
    mean = np.concatenate([block for _, block in blocks])
    assert mean.dtype == np.float32
    np.testing.assert_array_equal(mean, ensemble_da.mean("calibration_setup").values)


def test_satwet_ensemble_mean_blocks_nan(ensemble_da):
    # cell (0, 0) is missing in one member at t=0, and in every member at t=1
    ensemble_da[0, 0, 0, 0] = np.nan
    ensemble_da[:, 1, 0, 0] = np.nan

    blocks = list(satwet_ensemble_mean_blocks(ensemble_da, time_block=12))

    assert len(blocks) == 1
    _, mean = blocks[0]
    # members 1 and 2 at t=0 have values 1 and 2
    assert mean[0, 0, 0] == 1.5
    assert np.isnan(mean[1, 0, 0])
    # other cells are unaffected
    assert mean[0, 1, 1] == 1.0
    assert mean[1, 1, 1] == 2.0
