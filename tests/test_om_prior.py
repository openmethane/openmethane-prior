import subprocess

import pytest
import xarray as xr
import os



def test_full_process(num_regression, root_dir, monkeypatch):

    monkeypatch.chdir(root_dir)

    subprocess.run(["python", "scripts/omDownloadInputs.py"])

    subprocess.run(["python", "scripts/omCreateDomainInfo.py"])

    subprocess.run(["python", "scripts/omPrior.py", "2022-07-01", "2022-07-02"])

    filepath_ds = os.path.join(root_dir, "outputs/out-om-domain-info.nc")
    out_om_domain = xr.load_dataset(filepath_ds)

    mean_values = {key: out_om_domain[key].mean().item() for key in out_om_domain.keys()}
    num_regression.check(mean_values)

    downloaded_files = os.listdir("inputs")

    for file in [i for i in downloaded_files if i != 'README.md']:
        filepath = os.path.join("inputs", file)
        os.remove(filepath)

    os.remove("outputs/out-om-domain-info.nc")

