"""
omCreateDomainInfo.py

Copyright 2023 The Superpower Institute Ltd
Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
"""

import xarray as xr
from omInputs import croFilePath, domainPath, dotFilePath, geomFilePath

domainXr = xr.Dataset()

with xr.open_dataset( geomFilePath) as geomXr:
    for attr in ['DX', 'DY', 'TRUELAT1','TRUELAT2', 'MOAD_CEN_LAT', 'STAND_LON']:
        domainXr.attrs[attr] = geomXr.attrs[attr]

with xr.open_dataset( croFilePath) as croXr:
    for var in ['LAT','LON']:
        domainXr[var] = croXr[var]
        domainXr[var] = croXr[var].squeeze(dim="LAY", drop=True) # copy but remove the 'LAY' dimension

    domainXr['LANDMASK'] = croXr['LWMASK'].squeeze(dim="LAY", drop=True) # copy but remove the 'LAY' dimension

with xr.open_dataset( dotFilePath) as dotXr:
    # some repetition between the geom and grid files here, XCELL=DX and YCELL=DY
    for attr in ['XCELL', 'YCELL']:
        domainXr.attrs[attr] = croXr.attrs[attr]
    for var in ['LATD','LOND']:
        domainXr[var] = dotXr[var].rename({'COL':'COL_D', 'ROW':'ROW_D'})

domainXr.to_netcdf(domainPath)
