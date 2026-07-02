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

from openmethane_prior.data_sources.safeguard.anzsic import filter_by_anzsic_prefixes
from openmethane_prior.lib import rows_in_period


def filter_npi_facilities(
    facilities_df: pd.DataFrame,
    period_start: datetime.date,
    period_end: datetime.date,
    anzsic_codes: list[str] = None,
) -> pd.DataFrame:
    """Return only the rows of the NPI facilities which reported to the NPI
    during the given period. Since the NPI dataset doesn't include dates when
    a facility was active, we assume that facilities are active from the year
    they filed their first report, to the year they filed their last report.

    Expects reporting_start_date and reporting_end_date columns to already be
    present on facilities_df (added by parse_npi_facilities_csv).

    :return: Filtered DataFrame with only facilities that were active between
      start_date and end_date, and in one of the specified ANZSIC sectors if
      provided.
    """

    # filter out facilities which didn't report during the period of interest
    facilities_df = rows_in_period(
        df=facilities_df,
        start_date=period_start,
        end_date=period_end,
        start_field="reporting_start_date",
        end_field="reporting_end_date",
    )

    if anzsic_codes is not None:
        facilities_df = filter_by_anzsic_prefixes(
            facilities_df,
            anzsic_codes,
            column="primary_anzsic_class_code",
        )

    return facilities_df
