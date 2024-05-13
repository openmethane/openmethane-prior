import subprocess

import pytest
import xarray as xr
import os



def test_full_process(num_regression, root_dir, monkeypatch):

    monkeypatch.chdir(root_dir)

    subprocess.run(["python", "omDownloadInputs.py"])

    subprocess.run(["python", "omCreateDomainInfo.py"])

    subprocess.run(["python", "omPrior.py", "2022-07-01", "2022-07-02"])

    filepath_ds = os.path.join(root_dir, "outputs/out-om-domain-info.nc")
    test_ds = xr.load_dataset(filepath_ds)
    mean_values = {key: test_ds[key].mean().item() for key in test_ds.keys()}
    num_regression.check(mean_values)

