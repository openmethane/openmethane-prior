import math
import numpy as np
import xarray as xr

def dataset_metrics(ds: xr.Dataset):
    """Create a numeric summary of a dataset that can be committed as a test
    snapshot and compared against future results. This is useful to establish
    a baseline for results that shouldn't change when no scientific changes
    have been made. When science changes are expected to alter numeric results,
    this metrics snapshot can be used to gauge whether the changes are within
    expected parameters."""

    # dataset variables which contain numeric results (can be summed, averaged, etc)
    numeric_keys = [key for key in ds.keys() if np.issubdtype(ds[key].dtype, np.number)]
    # dataset variables with spatial coordinates
    spatial_keys = [key for key in numeric_keys if ds[key].dims[-2:] == ('y', 'x')]

    return {
        "max": { key: ds[key].max().item() for key in numeric_keys },
        "mean": { key: ds[key].mean().item() for key in numeric_keys },

        # x_band and y_band spatial metrics take the sum of a 1-width/height
        # stripe of the spatial domain in the center of the x and y dimension.
        # changes to these values would indicate spatial shifting of results.
        "x_band": { key: ds[key][..., math.floor(ds[key].shape[-1] / 2)].sum().item() for key in spatial_keys },
        "y_band": { key: ds[key][..., math.floor(ds[key].shape[-2] / 2), :].sum().item() for key in spatial_keys },
    }
