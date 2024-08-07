import xarray as xr
from matplotlib import pyplot as plt
import pandas as pd
import numpy as np

output_file = "../data/outputs/out-om-domain-info.nc"

ds = xr.open_dataset(output_file)




ds.LANDMASK.plot()

# print min and max values for all variables
for var in ds:
    arr_var = ds[var].squeeze().to_numpy()
    print(f"{var}: MIN {arr_var.min():.2e}, MAX {arr_var.max():.2e}")

arr_total = ds.OCH4_TOTAL.squeeze().to_numpy()

# histogram
#series = np.reshape(arr, 1)
arr_total_flat = np.concatenate(arr)
arr_total_flat.shape

# find outliers in total CH4 emissions
(n, bins, patches) = plt.hist(arr_total_flat, bins=10, label='hst')

# inspect the counts in each bin
print([ "{:0.0f}".format(x) for x in n ])

# inspect bins
bins
