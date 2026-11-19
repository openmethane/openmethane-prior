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
import io
import pathlib
import re
import unicodedata
import urllib.request
from collections.abc import Callable

import attrs
import pandas as pd

from openmethane_prior.lib import ConfiguredDataSource, DataSource, PriorConfig, logger
from openmethane_prior.lib.data_manager.fetchers import fetch_google_sheet_by_name_csv

from ..financial_year import FinancialYear
from .facility import create_facilities_from_safeguard_rows
from .location import filter_locations_for_financial_year

logger = logger.get_logger(__name__)

# NGER emissions numbers are reported in CO2 equivalent, so to calculate raw
# CH4 we must scale using Global Warming Potential (GWP) values. GWP for each
# gas is based on the AR5 GWPs:
# https://cer.gov.au/schemes/national-greenhouse-and-energy-reporting-scheme/about-emissions-and-energy-data/global-warming-potential#summary-of-updates-to-gwp-values
ar5_co2_gwp = 1
ar5_ch4_gwp = 28

# columns read from the Baselines and Emissions Table, mapped from the header
# published by the CER to the column names used in the prior
baselines_and_emissions_columns = {
    "Facility name": "facility_name",
    "State/Territory of operation": "state",
    "ANZSIC": "anzsic",
    "GHG Methane": "co2e_ch4",
}

# columns of the facilities DataFrame created from the table rows by
# create_facilities_from_safeguard_rows
safeguard_facility_columns = [
    *baselines_and_emissions_columns.values(),
    "ch4_kg",
    "anzsic_code",
    "reporting_start",
    "reporting_end",
]

# columns read from the Safeguard Mechanism Facility Locations dataset, mapped
# from the header in the sheet to the column names used in the prior
safeguard_locations_columns = {
    # exact facility_name from the Safeguard Mechanism table
    "Facility name": "safeguard_facility_name",
    # DataSource name with facility details
    "Supporting data source": "data_source_name",
    # identifier in reference DataSource
    "Supporting data id": "data_source_id",
}
# optional columns limiting a location to a range of financial years
safeguard_locations_year_columns = {
    "First financial year": "first_financial_year",
    "Last financial year": "last_financial_year",
}

# columns of the "Petroleum titles" sheet used to create location rows
petroleum_titles_columns = ["Facility name", "Data source", "Production license"]


def parse_csv_numeric(csv_value: str) -> float | None:
    """Convert messy input values like " 124,138 " to float. Values of "-" are
    interpreted as None."""
    raw = csv_value.strip()
    if raw == "-":
        return None
    return float(raw.replace(",", ""))

def parse_csv_text(csv_value: str) -> str:
    """Normalise text values, removing surrounding whitespace and replacing
    compatibility characters like non-breaking spaces with their plain
    equivalents."""
    return unicodedata.normalize("NFKC", csv_value).strip()


def read_baselines_and_emissions_csv(
    filepath_or_buffer: pathlib.Path | io.IOBase,
) -> pd.DataFrame:
    """Read a Safeguard Mechanism Baselines and Emissions Table CSV,
    returning only the columns used for methane estimation. Columns are
    selected by their header, so a table missing one of the expected headers
    raises a ValueError."""
    safeguard_rows_df = pd.read_csv(
        filepath_or_buffer=filepath_or_buffer,
        header=0,
        usecols=list(baselines_and_emissions_columns.keys()),
        converters={
            "Facility name": parse_csv_text,
            "State/Territory of operation": parse_csv_text,
            "ANZSIC": parse_csv_text,
            "GHG Methane": parse_csv_numeric,
        },
        # CER appears to publish this file in windows-1252 encoding
        encoding="cp1252",
    )
    return safeguard_rows_df.rename(columns=baselines_and_emissions_columns)[
        list(baselines_and_emissions_columns.values())
    ]


@attrs.frozen()
class SafeguardBaselinesAndEmissionsTable:
    """A Safeguard Mechanism Baselines and Emissions Table published for a
    single Australian financial year."""

    financial_year: FinancialYear
    """Financial year the table reports emissions for"""

    url: str
    """URL the table is published at"""

    ch4_gwp: float
    """Global warming potential used for CH4 when calculating CO2-e"""

    co2_gwp: float
    """Global warming potential used for CO2 when calculating CO2-e"""

    read: Callable[[pathlib.Path], pd.DataFrame] = read_baselines_and_emissions_csv
    """Reads the published table into a DataFrame with the columns
    facility_name, state, anzsic and co2e_ch4. Years published in a different
    structure can provide their own reader."""

    @property
    def file_name(self) -> str:
        """Name of the cached file, including the financial year so tables
        for different years are cached separately."""
        return f"{self.financial_year.label}-baselines-and-emissions-table.csv"


# Safeguard Mechanism Baselines and Emissions Tables which include per-gas
# emissions. Tables before FY 2023-24 have no methane column.
# Sources:
# - https://cer.gov.au/markets/reports-and-data/safeguard-data/2023-24-baselines-and-emissions-data
# - https://cer.gov.au/markets/reports-and-data/safeguard-data/2024-25-baselines-and-emissions-data
safeguard_tables: dict[FinancialYear, SafeguardBaselinesAndEmissionsTable] = {
    table.financial_year: table
    for table in [
        SafeguardBaselinesAndEmissionsTable(
            financial_year=FinancialYear.from_label("2023-24"),
            url="https://cer.gov.au/document/2023-24-baselines-and-emissions-table",
            ch4_gwp=ar5_ch4_gwp,
            co2_gwp=ar5_co2_gwp,
        ),
        SafeguardBaselinesAndEmissionsTable(
            financial_year=FinancialYear.from_label("2024-25"),
            url="https://cer.gov.au/document/baselines-and-emissions-table-2024-25",
            ch4_gwp=ar5_ch4_gwp,
            co2_gwp=ar5_co2_gwp,
        ),
    ]
}


def _run_financial_year(prior_config: PriorConfig) -> FinancialYear:
    """Financial year of the prior run period, which Safeguard data is read for."""
    return FinancialYear.from_period(prior_config.start_date.date(), prior_config.end_date.date())


def safeguard_file_path(_data_source: DataSource, prior_config: PriorConfig) -> str:
    """File path for the Safeguard table covering the configured period. The
    path includes the financial year, so tables for different years are
    cached separately."""
    financial_year = _run_financial_year(prior_config)
    table = safeguard_tables.get(financial_year)
    if table is None:
        # no file will be fetched for this path
        return f"{financial_year.label}-baselines-and-emissions-table.csv"
    return table.file_name


def fetch_safeguard_csv(data_source: ConfiguredDataSource) -> pathlib.Path:
    """Fetch the Safeguard table for the configured financial year. If no
    table has been published for that year, nothing is fetched."""
    table = safeguard_tables.get(_run_financial_year(data_source.prior_config))
    if table is None:
        return data_source.asset_path

    save_path, _ = urllib.request.urlretrieve(url=table.url, filename=data_source.asset_path)
    return pathlib.Path(save_path)


def parse_safeguard_csv(data_source: ConfiguredDataSource) -> pd.DataFrame:
    """Read the Safeguard table for the configured financial year into
    facilities with CH4 emissions in kg. If no table has been published for
    that year, warn and return no facilities."""
    financial_year = _run_financial_year(data_source.prior_config)
    table = safeguard_tables.get(financial_year)
    if table is None:
        logger.warning(
            f"No Safeguard Mechanism data published for FY {financial_year}, "
            f"Safeguard facility emissions will not be used"
        )
        return pd.DataFrame(columns=safeguard_facility_columns)

    logger.info(f"Using Safeguard Mechanism data for FY {table.financial_year}")
    return create_facilities_from_safeguard_rows(
        safeguard_rows_df=table.read(data_source.asset_path),
        financial_year=table.financial_year,
        ch4_gwp=table.ch4_gwp,
        co2_gwp=table.co2_gwp,
    )


# Facility-level emissions reported under the Safeguard Mechanism, from the
# table for the financial year of the prior run period.
safeguard_mechanism_data_source = DataSource(
    name="safeguard-mechanism",
    file_path=safeguard_file_path,
    fetch=fetch_safeguard_csv,
    parse=parse_safeguard_csv,
)


def fetch_location_csv(data_source: ConfiguredDataSource) -> pathlib.Path:
    # Primary source of external locations
    external_locations_df = fetch_google_sheet_by_name_csv(
        data_source.url, "External facility locations", list(safeguard_locations_columns),
    )

    # Petroleum titles sheet has some extra details, but contains columns for
    # Facility name, Data source, and Production license which can be converted
    # into external location references.
    petroleum_titles_df = fetch_google_sheet_by_name_csv(
        data_source.url, "Petroleum titles", petroleum_titles_columns,
    )
    petroleum_locations_df = petroleum_titles_df[petroleum_titles_columns] \
        .rename(columns={
            "Data source": "Supporting data source",
            "Production license": "Supporting data id",
        })

    # Oil and gas sites, which are used as an independent DataSource in the
    # oil_gas sector, already include the Facility name. Create a row for each
    # facility in this with the facility name as both the name and the id.
    oil_gas_sites = fetch_google_sheet_by_name_csv(
        data_source.url, "Oil and gas sites", ["Facility name"],
    )
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


def check_location_year_columns(columns: list[str]):
    """Raise a ValueError if a column looks like a financial year column but
    isn't named exactly as expected. The year columns are optional, so a
    misnamed one would otherwise be silently ignored, applying its rows to
    every year."""
    unexpected = [
        column for column in columns
        if re.search(r"year|\bfy\b", column, flags=re.IGNORECASE)
        and column not in safeguard_locations_year_columns
    ]
    if unexpected:
        raise ValueError(
            f"Safeguard locations columns {unexpected} look like financial year columns, "
            f"expected {list(safeguard_locations_year_columns)}"
        )


def read_location_csv(
    filepath_or_buffer,
    financial_year: FinancialYear | None = None,
) -> pd.DataFrame:
    """Read Safeguard facility location rows, selecting columns by header
    name so that extra or reordered columns in the sheet don't matter.

    :param financial_year: Keep only rows which apply in this financial year,
      using the optional "First financial year" and "Last financial year"
      columns. If None, rows for every year are kept.
    """
    locations_csv_df = pd.read_csv(filepath_or_buffer, dtype=str)
    locations_csv_df.columns = locations_csv_df.columns.str.strip()
    check_location_year_columns(list(locations_csv_df.columns))

    year_columns = {
        sheet_column: column
        for sheet_column, column in safeguard_locations_year_columns.items()
        if sheet_column in locations_csv_df.columns
    }
    locations_rows_df = locations_csv_df[
        list(safeguard_locations_columns) + list(year_columns)
    ].rename(columns={**safeguard_locations_columns, **year_columns})

    # filter out any rows with incomplete information
    locations_rows_df = locations_rows_df.dropna(subset=list(safeguard_locations_columns.values()))

    if financial_year is not None:
        locations_rows_df = filter_locations_for_financial_year(locations_rows_df, financial_year)

    return locations_rows_df[list(safeguard_locations_columns.values())]


def parse_location_csv(data_source: ConfiguredDataSource) -> pd.DataFrame:
    """Read Safeguard facility locations which apply in the financial year of
    the configured period."""
    return read_location_csv(
        data_source.asset_path,
        financial_year=_run_financial_year(data_source.prior_config),
    )


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
