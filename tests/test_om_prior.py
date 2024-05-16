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
    out_om_domain = xr.load_dataset(filepath_ds)

    mean_values = {key: out_om_domain[key].mean().item() for key in out_om_domain.keys()}
    num_regression.check(mean_values)

    with xr.open_dataset("cmaq_example/geo_em.d01.nc") as geomXr :
        assert geomXr.DX == out_om_domain.DX
        assert geomXr.DY == out_om_domain.DY

    with xr.open_dataset("cmaq_example/GRIDDOT2D_1") as dotXr :
        assert dotXr.XCELL == out_om_domain.DX
        assert dotXr.YCELL == out_om_domain.DY

    with xr.open_dataset("cmaq_example/GRIDCRO2D_1") as croXr :
        assert croXr.XCELL == out_om_domain.DX
        assert croXr.YCELL == out_om_domain.DY

