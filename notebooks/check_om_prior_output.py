import xarray as xr
from matplotlib import pyplot as plt
import pandas as pd

output_file = "../data/outputs/out-om-domain-info.nc"

ds = xr.open_dataset(output_file)




ds.LANDMASK.plot()

# print min and max values for all variables
for var in ds:
    arr = ds[var].squeeze().to_numpy()
    print(f"{var}: MIN {arr.min():.2e}, MAX {arr.max():.2e}")








