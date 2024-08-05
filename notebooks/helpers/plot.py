import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import xarray as xr


def _replace_coords_lonlat(ds: xr.Dataset, xy_var: xr.DataArray):
    return xy_var.copy().assign_coords(x=ds.lon, y=ds.lat)


def _plot_map(var: xr.DataArray, ax):
    var.plot.pcolormesh(ax=ax, infer_intervals=True)
    ax.coastlines()
    # ax.gridlines(draw_labels=True)
    ax.gridlines()


def plot_map(ds: xr.Dataset, var_name: str):
    # replace grid projection coordinates with lon/lat from the dataset
    var_lonlat = _replace_coords_lonlat(ds, ds[var_name])

    ax = plt.subplot(projection=ccrs.PlateCarree(), facecolor="gray")
    _plot_map(var_lonlat, ax)


def plot_timestep_maps(ds: xr.Dataset, var_name: str):
    # replace grid projection coordinates with lon/lat from the dataset
    var_lonlat = _replace_coords_lonlat(ds, ds[var_name])

    # make enough room for multiple plots
    rows = ds[var_name].time.size
    fig, axes = plt.subplots(
        figsize=(8, 4 * rows),
        nrows=rows,
        subplot_kw={ "projection": ccrs.PlateCarree(), "facecolor": "gray" },
        sharex=True,
    )
    for i, time_val in enumerate(ds[var_name].time):
        _plot_map(var_lonlat.sel(time=time_val).squeeze(drop=True), axes[i])
        axes[i].label_outer()
