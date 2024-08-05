import xarray as xr
import numpy as np
from helpers.plot import plot_map, plot_timestep_maps

output_file = "../data/outputs/prior-emissions.nc"
ds = xr.open_dataset(output_file)
ds

# plot the shape of the landmask
plot_map(ds, "land_mask")

# plot the total emissions
plot_timestep_maps(ds, "ch4_total")

# print min and max values for all numeric variables
numeric_keys = [key for key in ds.keys() if np.issubdtype(ds[key].dtype, np.number)]
longest_key = len(max(numeric_keys, key=len))
for var in numeric_keys:
    arr_var = ds[var].squeeze().to_numpy()
    print(f"{var: >{longest_key}}: {arr_var.min():.2e} - {arr_var.max():.2e}")



