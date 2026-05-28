#
# Copyright 2026 The Superpower Institute Ltd.
#
# This file is part of OpenMethane.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import geopandas as gpd
import numpy as np
import pandas as pd

from openmethane_prior.data_sources.climate_trace import filter_emissions_sources
from openmethane_prior.data_sources.npi import (
    filter_npi_facilities,
    npi_facilities_data_source,
)
from openmethane_prior.lib import (
    DataManager,
    PriorConfig,
)

from .data import (
    ct_wastewaster_domestic_data_source,
    ct_wastewaster_industrial_data_source,
    ct_solid_waste_data_source,
)

def waste_emission_sources(
    config: PriorConfig,
    data_manager: DataManager,
    anzsic_codes: list[str],
):
    # read all emissions sources corresponding to the waste sector
    wastewater_domestic_df = data_manager.get_asset(ct_wastewaster_domestic_data_source).data
    wastewater_industrial_df = data_manager.get_asset(ct_wastewaster_industrial_data_source).data
    solid_waste_df = data_manager.get_asset(ct_solid_waste_data_source).data

    ct_sources_df: gpd.GeoDataFrame = pd.concat([
        wastewater_domestic_df,
        wastewater_industrial_df,
        solid_waste_df,
    ])

    # select the emissions source data from the requested period
    ct_sources_df = filter_emissions_sources(
        emissions_sources_df=ct_sources_df,
        period_start=config.start_date,
        period_end=config.end_date,
    )

    # the national pollutant inventory doesn't track methane emissions, but it
    # does include the locations of industrial facilities in different ANSIC
    # sectors, including the waste sector.
    npi_da = data_manager.get_asset(npi_facilities_data_source)
    npi_df: gpd.GeoDataFrame = filter_npi_facilities(
        facilities_df=npi_da.data,
        period_start=config.start_date,
        period_end=config.end_date,
        anzsic_codes=anzsic_codes,
    )

    _DUPLICATE_THRESHOLD_METERS = 250

    # Reproject to a meter-based CRS if needed so the threshold stays in meters
    # regardless of the domain CRS. Only indices are used from the join result.
    crs_units = {axis.unit_name for axis in npi_df.crs.coordinate_system.axis_list}
    npi_for_join = npi_df
    sites_for_join = ct_sources_df
    if crs_units != {"metre"}:
        meter_crs = "EPSG:3577"  # GDA94 / Australian Albers
        npi_for_join = npi_for_join.to_crs(meter_crs)
        sites_for_join = sites_for_join.to_crs(meter_crs)

    # locate NPI facilities within 250m of sites already accounted for in the
    # CT datasets, so they don't get counted twice
    npi_duplicate_df = gpd.sjoin_nearest(
        npi_for_join,
        sites_for_join,
        how="inner",
        max_distance=_DUPLICATE_THRESHOLD_METERS,
    )

    # remove npi facilities within 250m of a site from our other dataset
    npi_df = npi_df[~npi_df.index.isin(npi_duplicate_df.index)]

    # normalise output to match emission sources format
    npi_df = npi_df.rename(columns={
        "facility_id": "data_source_id",
        "start_date": "activity_start",
        "expiry_date": "activity_end",
        "primary_anzsic_class_code": "anzsic_code",
    })
    npi_df["data_source"] = npi_da.name
    npi_df["emissions_quantity"] = np.nan

    emission_sources_df: gpd.GeoDataFrame = pd.concat([
        ct_sources_df,
        npi_df,
    ])

    # ClimateTRACE has "emission_quantity" column with their own estimate.
    # Add a column for the emission from each source from inventories, using
    # NaN to indicate "not yet allocated" instead of "no emission"
    emission_sources_df["inventory_quantity"] = np.nan

    return emission_sources_df