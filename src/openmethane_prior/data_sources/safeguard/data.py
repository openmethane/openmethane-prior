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
import pathlib

from openmethane_prior.lib import ConfiguredDataSource, DataSource
from openmethane_prior.lib.data_manager.fetchers import fetch_google_sheet_by_name_csv

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
    "notes", # notes about how this location is related to the facility
]


def parse_csv_numeric(csv_value: str) -> float | None:
    """Convert messy input values like " 124,138 " to float. Values of "-" are
    interpreted as None."""
    raw = csv_value.strip()
    if raw == "-":
        return None
    return float(raw.replace(",", ""))


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

# Facility-level emissions reported under the Safeguard Mechanism.
# Source: https://cer.gov.au/markets/reports-and-data/safeguard-data/2023-24-baselines-and-emissions-data
safeguard_mechanism_data_source = DataSource(
    name="safeguard-mechanism",
    url="https://cer.gov.au/document/2023-24-baselines-and-emissions-table",
    file_path="2023-24-baselines-and-emissions-table.csv",
    parse=parse_safeguard_csv,
)


def fetch_location_csv(data_source: ConfiguredDataSource) -> pathlib.Path:
    # Primary source of external locations
    external_locations_df = fetch_google_sheet_by_name_csv(data_source.url, "External facility locations")

    # Petroleum titles sheet has some extra details, but contains columns for
    # Facility name, Data source, and Production license which can be converted
    # into external location references.
    petroleum_titles_df = fetch_google_sheet_by_name_csv(data_source.url, "Petroleum titles")
    petroleum_locations_df = petroleum_titles_df \
        .drop(columns=["Responsible emitter", "State"]) \
        .rename(columns={
            "Data source": "Supporting data source",
            "Production license": "Supporting data id",
        })

    # Oil and gas sites, which are used as an independent DataSource in the
    # oil_gas sector, already include the Facility name. Create a row for each
    # facility in this with the facility name as both the name and the id.
    oil_gas_sites = fetch_google_sheet_by_name_csv(data_source.url, "Oil and gas sites")
    oil_gas_facilities = oil_gas_sites["Facility name"].unique()
    oil_gas_locations_df = pd.DataFrame({
        "Facility name": oil_gas_facilities,
        "Supporting data id": oil_gas_facilities,
        "Supporting data source": "oil-gas-sites",
    })

    # Combine the sources of facility locations and write them to a CSV file
    df = pd.concat([external_locations_df, oil_gas_locations_df, petroleum_locations_df])
    df.to_csv(data_source.asset_path, index=False)
    return data_source.asset_path


def parse_location_csv(data_source: ConfiguredDataSource):
    locations_rows_df = pd.read_csv(
        filepath_or_buffer=data_source.asset_path,
        header=0,
        names=safeguard_locations_csv_columns,
        usecols=["safeguard_facility_name", "data_source_name", "data_source_id"],
    )

    # filter out any rows with incomplete information
    return locations_rows_df.dropna()


# Locations of Safeguard Mechanism facilities which are found in other data
# sources are recorded in The Superpower Institute's Safeguard Mechanism
# Facility Locations dataset.
# Source: https://docs.google.com/spreadsheets/d/1vET6DVXo3K9MeMYJj9sksSTmQjV3v9JmIPSlR6HS4NA
safeguard_locations_data_source = DataSource(
    name="safeguard-locations",
    file_path="safeguard-facility-locations.csv",
    url="https://docs.google.com/spreadsheets/d/1vET6DVXo3K9MeMYJj9sksSTmQjV3v9JmIPSlR6HS4NA",
    fetch=fetch_location_csv,
    parse=parse_location_csv,
)
