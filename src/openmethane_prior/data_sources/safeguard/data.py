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
from .facility import SafeguardFacility, create_facility_list

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


def parse_csv_numeric(csv_value: str) -> float:
    """Convert messy input values like " 124,138 " to float. Values of "-" are
    interpreted as None."""
    raw = csv_value.strip()
    return None if raw == "-" else float(raw.replace(",", ""))

def parse_safeguard_csv(data_source: ConfiguredDataSource) -> list[SafeguardFacility]:
    """Read the Safeguard Mechanism Baselines and Emissions Table CSV,
    returning only the data columns useful for methane estimation."""
    csv_records = pd.read_csv(
        filepath_or_buffer=data_source.asset_path,
        encoding="cp1252", # CER distributes the CSV in windows-1252 encoding
        header=0,
        names=safeguard_mechanism_csv_columns,
        # must be kept in sync with SafeguardFacilityRecord attributes
        usecols=["facility_name", "business_name", "state", "anzsic", "co2e_ch4"],
        converters={"co2e_ch4": parse_csv_numeric},
    )

    return create_facility_list(csv_records.to_records(), ar5_ch4_gwp / ar5_co2_gwp)


safeguard_mechanism_data_source = DataSource(
    name="safeguard-mechanism",
    url="https://cer.gov.au/document/2023-24-baselines-and-emissions-table",
    file_path="2023-24-baselines-and-emissions-table.csv",
    parse=parse_safeguard_csv,
)
