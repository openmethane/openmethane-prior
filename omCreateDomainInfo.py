"""
omCreateDomainInfo.py

Copyright 2023 The Superpower Institute Ltd
Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
"""

from omInputs import domainPath, geomFilePath, croFilePath, dotFilePath
import xarray as xr

domainXr = xr.Dataset()

with xr.open_dataset( geomFilePath) as geomXr:
    for attr in ['DX', 'DY', 'TRUELAT1','TRUELAT2', 'MOAD_CEN_LAT', 'STAND_LON']:
        domainXr.attrs[attr] = geomXr.attrs[attr]
    domainXr.attrs['XCELL'] = geomXr.attrs['DX']
    domainXr.attrs['YCELL'] = geomXr.attrs['DY']
    domainXr['LAT'] = geomXr['XLAT_M']
    domainXr['LON'] = geomXr['XLONG_M']
    domainXr['LATD'] = geomXr['XLAT_C'].rename({'west_east_stag':'COL_D', 'south_north_stag':'ROW_D'})
    domainXr['LOND'] = geomXr['XLONG_C'].rename({'west_east_stag':'COL_D', 'south_north_stag':'ROW_D'})
    domainXr['LANDMASK'] = geomXr['LANDMASK']


domainXr.to_netcdf(domainPath)
