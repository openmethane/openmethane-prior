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
import calendar
import datetime
import pandas as pd


def filter_emissions_sources(
    emissions_sources_df: pd.DataFrame,
    period_start: datetime.date,
    period_end: datetime.date,
):
    """
    Return only the rows of the Climate TRACE emissions sources which
    occurred in the given period.
    """
    # periods in the dataset always end on the last day of the month
    period_end_month_days = calendar.monthrange(period_end.year, period_end.month)[1]
    period_end_month_end = datetime.datetime(period_end.year, period_end.month, period_end_month_days, 0, 0, 0)

    if (period_start.year != period_end.year) or (period_start.month != period_end.month):
        # if we want to run a prior across multiple months, we will have to
        # account for different emissions across each month, and allocate
        # accordingly across daily time steps
        raise NotImplementedError("filtering on multiple months of data not yet implemented")

    # select the month of the desired period, or the latest month in the data
    data_period_latest = emissions_sources_df["end_time"].max()
    target_period = data_period_latest if period_end >= data_period_latest else period_end_month_end

    emissions_sources_filtered_df = emissions_sources_df[emissions_sources_df["end_time"] == target_period]

    return emissions_sources_filtered_df
