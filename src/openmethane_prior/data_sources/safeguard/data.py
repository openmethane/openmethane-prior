#
# Copyright 2025 The Superpower Institute Ltd.
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

import pandas as pd

from openmethane_prior.lib import ConfiguredDataSource, DataSource
from .facility import create_facilities_from_safeguard_rows

# NGER emissions numbers are reported in CO2 equivalent, so to calculate raw
# CH4 we must scale using Global Warming Potential (GWP) values. GWP for each
# gas is based on the AR5 GWPs:
# https://cer.gov.au/schemes/national-greenhouse-and-energy-reporting-scheme/about-emissions-and-energy-data/global-warming-potential#summary-of-updates-to-gwp-values
ar5_co2_gwp = 1
ar5_ch4_gwp = 28

# hashable column names for the source data, most are not used
safeguard_mechanism_csv_columns = [
    "facility_name", # Facility name
    "business_name", # Responsible emitter
    "state", # State/Territory of operation
    "anzsic", # ANZSIC
    "erc", # ERC
    "baseline_emissions_number", # Baseline emissions number
    "covered_emissions", # Covered emissions
    "borrowing_adjustment_amount", # Borrowing adjustment amount
    "accus_issued", # ACCUs issued
    "accus_deemed_surrendered", # ACCUs deemed surrendered
    "accus_surrendered", # ACCUs surrendered
    "smcs_surrendered", # SMCs surrendered
    "net_emissions", # Net emissions number
    "net_position", # Net position number
    "smcs_issued", # SMCs Issued
    "mymp_net_emissions", # Cumulative MYMP net emissions number
    "mymp_net_position", # Cumulative MYMP net position number
    "co2e_co2", # GHG Carbon Dioxide
    "co2e_ch4", # GHG Methane
    "co2e_n2o", # GHG Nitrous oxide
    "co2e_other", # GHG Other
    "notes", # Notes
]

safeguard_locations_csv_columns = [
    "safeguard_facility_name", # exact facility_name from Safeguard Mechanism
    "data_source_name", # DataSource name with facility details
    "data_source_id", # identifier in reference DataSource
]


def parse_csv_numeric(csv_value: str) -> float | None:
    """Convert messy input values like " 124,138 " to float. Values of "-" are
    interpreted as None."""
    raw = csv_value.strip()
    if raw == "-":
        return None
    return float(raw.replace(",", ""))


def parse_location_csv(data_source: ConfiguredDataSource):
    locations_rows_df = pd.read_csv(
        filepath_or_buffer=data_source.asset_path,
        header=0,
        names=safeguard_locations_csv_columns,
    )

    # filter out any rows with incomplete information
    return locations_rows_df.dropna()


def parse_safeguard_csv(data_source: ConfiguredDataSource):
    """Read the Safeguard Mechanism Baselines and Emissions Table CSV,
    returning only the data columns useful for methane estimation."""
    safeguard_rows_df = pd.read_csv(
        filepath_or_buffer=data_source.asset_path,
        encoding="cp1252", # CER distributes the CSV in windows-1252 encoding
        header=0,
        names=safeguard_mechanism_csv_columns,
        usecols=["facility_name", "state", "anzsic", "co2e_ch4"],  # from safeguard_mechanism_csv_columns
        converters={"co2e_ch4": parse_csv_numeric},
    )

    return create_facilities_from_safeguard_rows(
        safeguard_rows_df=safeguard_rows_df,
        reporting_period=(2023, 2024),
        ch4_gwp=ar5_ch4_gwp, co2_gwp=ar5_co2_gwp,
    )


safeguard_locations_data_source = DataSource(
    name="safeguard-locations",
    url="https://openmethane.s3.amazonaws.com/prior/inputs/facility-locations-v1.1.csv",
    parse=parse_location_csv,
)


safeguard_mechanism_data_source = DataSource(
    name="safeguard-mechanism",
    url="https://cer.gov.au/document/2023-24-baselines-and-emissions-table",
    file_path="2023-24-baselines-and-emissions-table.csv",
    parse=parse_safeguard_csv,
)
