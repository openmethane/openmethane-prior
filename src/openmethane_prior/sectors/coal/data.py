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
import datetime
import pandas as pd

from openmethane_prior.lib import (
    ConfiguredDataSource,
    DataSource,
    logger,
)

logger = logger.get_logger(__name__)


def filter_coal_facilities(
    coal_facilities_df: pd.DataFrame,
    period: tuple[datetime.date, datetime.date],
):
    # select CH4 gas
    coal_facilities_df_ch4 = coal_facilities_df[coal_facilities_df["gas"] == "ch4"]

    # select the year of the desired period, or the latest year in the data
    period_start, period_end = period
    coal_max_year = coal_facilities_df_ch4["year"].max()
    target_year = (
        period_start.year
        if period_start.year <= coal_max_year
        else coal_max_year
    )
    coal_facilities_df_ch4_period = coal_facilities_df_ch4[coal_facilities_df_ch4["year"] == target_year]

    return coal_facilities_df_ch4_period

def parse_coal_facilities_csv(data_source: ConfiguredDataSource) -> pd.DataFrame:
    coal_facilities_df = pd.read_csv(
        data_source.asset_path,
        converters={
            "start_time": datetime.datetime.fromisoformat,
            "end_time": datetime.datetime.fromisoformat,
        },
    )

    coal_facilities_df["year"] = coal_facilities_df["start_time"].apply(lambda start_time: start_time.year)

    return coal_facilities_df

coal_facilities_data_source = DataSource(
    name="coal-facilities",
    url="https://openmethane.s3.amazonaws.com/prior/inputs/coal-mining_emissions-sources.csv",
    parse=parse_coal_facilities_csv,
)
