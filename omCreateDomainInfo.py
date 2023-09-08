gridDir = 'cmaq_example'
geomFile = 'geo_em.d01.nc'
dotFile = 'GRIDDOT2D_1'
croFile = 'GRIDCRO2D_1'

from omInputs import domainPath
import xarray as xr
import os

geomPath = os.path.join( gridDir, geomFile)
dotPath = os.path.join( gridDir, dotFile)
croPath = os.path.join( gridDir, croFile)

domainXr = xr.Dataset()
with xr.open_dataset( geomPath) as geomXr:
    for attr in ['DX', 'DY', 'TRUELAT1','TRUELAT2', 'MOAD_CEN_LAT', 'STAND_LON']:
        domainXr.attrs[attr] = geomXr.attrs[attr]

with xr.open_dataset( croPath) as croXr:
    for var in ['LAT','LON']:
        domainXr[var] = croXr[var]

    domainXr['LANDMASK'] = croXr['LWMASK'].squeeze(dim="LAY", drop=True) # copy but remove the 'LAY' dimension

with xr.open_dataset( dotPath) as dotXr:
    # some repetition between the geom and grid files here, XCELL=DX and YCELL=DY
    for attr in ['XCELL', 'YCELL']:
        domainXr.attrs[attr] = croXr.attrs[attr]
    for var in ['LATD','LOND']:
        domainXr[var] = dotXr[var].rename({'COL':'COL_D', 'ROW':'ROW_D'})

domainXr.to_netcdf(domainPath)
