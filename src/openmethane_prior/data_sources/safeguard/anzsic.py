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

# Utility functions for working with ANZSIC classification codes. See:
# https://www.abs.gov.au/statistics/classifications/australian-and-new-zealand-standard-industrial-classification-anzsic/2006-revision-2-0/introduction#anzsic-structure

import numpy as np
import pandas as pd


def simplify_anzsic_code(anzsic_code: str) -> str:
    """Given an ANZSIC code of 2 or more characters, returns only significant
    parts. For example, simplifying a code of "0600" gives "06".
    """
    if len(anzsic_code) < 2:
        raise ValueError(f"invalid ANZSIC code '{anzsic_code}'")

    # strip non-significant characters (0s) from the end of the code
    return anzsic_code.rstrip("0")


def filter_by_anzsic_code_family(
    df: pd.DataFrame,
    anzsic_codes: list[str],
    *,
    column: str,
) -> pd.DataFrame:
    """Return rows whose ``column`` value belongs to any requested ANZSIC code family.

    Each entry in ``anzsic_codes`` may be a division, subdivision, group, or class
    code. Codes are simplified (trailing zeros removed) before matching, so filtering
    by ``"06"`` matches ``"06"``, ``"060"``, ``"0600"``, ``"061"``, and ``"0612"``.
    Filtering by ``"202"`` matches ``"202"``, ``"2021"``, and ``"2029"`` but not
    ``"20"``, ``"201"``, or ``"22"``.
    """
    if not anzsic_codes:
        return df

    code_families = [simplify_anzsic_code(code) for code in anzsic_codes]
    mask = np.logical_or.reduce([df[column].str.startswith(family) for family in code_families])
    return df[mask]
