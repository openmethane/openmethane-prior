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
"""Australian financial years, which run from July 1st to June 30th.

Australian data sources like the Safeguard Mechanism, NGER, NPI and the
national inventory report per financial year.
"""
import datetime
import re

import attrs

FIRST_MONTH = 7
"""Financial years start in July."""

financial_year_label_pattern = re.compile(r"^(?P<start>\d{4})-(?P<end>\d{2})$")


@attrs.frozen(order=True)
class FinancialYear:
    """An Australian financial year, from July 1st to June 30th.

    The year starts on July 1st in start_year. Data sources identify financial
    years in different ways (by start year, by end year, or with labels like
    "2023-24" or "2023/2024"), so each source converts its own identifier to
    a FinancialYear rather than passing bare years around.
    """

    start_year: int
    """Calendar year the financial year starts in, i.e. 2023 for FY 2023-24."""

    @classmethod
    def from_date(cls, date: datetime.date) -> "FinancialYear":
        """Return the financial year which date falls in."""
        return cls(date.year if date.month >= FIRST_MONTH else date.year - 1)

    @classmethod
    def from_period(cls, start_date: datetime.date, end_date: datetime.date) -> "FinancialYear":
        """Return the financial year containing the period from start_date to end_date.

        Raises
        ------
        ValueError
            If the period spans more than one financial year.
        """
        financial_year = cls.from_date(start_date)
        if cls.from_date(end_date) != financial_year:
            raise ValueError(
                f"start_date ({start_date}) and end_date ({end_date}) must be within the same "
                f"financial year"
            )
        return financial_year

    @classmethod
    def from_label(cls, label: str) -> "FinancialYear":
        """Parse a financial year label like "2023-24".

        Raises
        ------
        ValueError
            If the label isn't two consecutive years in the form "2023-24".
        """
        match = financial_year_label_pattern.match(label.strip())
        if match is None:
            raise ValueError(f"invalid financial year '{label}', expected a label like '2023-24'")
        financial_year = cls(int(match.group("start")))
        if financial_year.label != label.strip():
            raise ValueError(f"invalid financial year '{label}', years must be consecutive")
        return financial_year

    @property
    def label(self) -> str:
        """Label like "2023-24"."""
        return f"{self.start_year}-{(self.start_year + 1) % 100:02d}"

    def __str__(self) -> str:
        """Return the label, for log and error messages.

        Use label directly where the format is relied on, like file names.
        """
        return self.label

    @property
    def start(self) -> datetime.date:
        """First day of the financial year, July 1st."""
        return datetime.date(self.start_year, FIRST_MONTH, 1)

    @property
    def end(self) -> datetime.date:
        """Last day of the financial year, June 30th.

        The year includes this whole day, matching lib.units.days_in_period.
        """
        return datetime.date(self.start_year + 1, 6, 30)
