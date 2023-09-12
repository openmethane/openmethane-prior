from omInputs import domainPath, geomFilePath, croFilePath, dotFilePath
import xarray as xr

domainXr = xr.Dataset()
with xr.open_dataset( geomFilePath) as geomXr:
    for attr in ['DX', 'DY', 'TRUELAT1','TRUELAT2', 'MOAD_CEN_LAT', 'STAND_LON']:
        domainXr.attrs[attr] = geomXr.attrs[attr]

with xr.open_dataset( croFilePath) as croXr:
    for var in ['LAT','LON']:
        domainXr[var] = croXr[var]

    domainXr['LANDMASK'] = croXr['LWMASK'].squeeze(dim="LAY", drop=True) # copy but remove the 'LAY' dimension

with xr.open_dataset( dotFilePath) as dotXr:
    # some repetition between the geom and grid files here, XCELL=DX and YCELL=DY
    for attr in ['XCELL', 'YCELL']:
        domainXr.attrs[attr] = croXr.attrs[attr]
    for var in ['LATD','LOND']:
        domainXr[var] = dotXr[var].rename({'COL':'COL_D', 'ROW':'ROW_D'})

domainXr.to_netcdf(domainPath)
