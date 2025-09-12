#
# Copyright 2025 The Superpower Institute Ltd.
#
# This file is part of Open Methane.
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

import attrs
from typing import Iterable


@attrs.define
class Category:
    """
    Category describes a sector category based on the UNFCCC CRT classification
    scheme.
    """
    code: str | None
    """UNFCCC category code, parts separated with '.', like '1.A.3'."""

    api_level_names: list[str]
    """UNFCCC category names, in order from most general to most specific.
    These must be the exact names used in the Australia National Greenhouse
    Accounts 'Paris Inventory'."""


def create_category_list(categories: Iterable[list[str]]) -> list[Category]:
    """
    Create a list of UNFCCC Category objects from a CSV in the format:
      UNFCCC_Code,UNFCCC_Level_1,UNFCCC_Level_2,UNFCCC_Level_3,UNFCCC_Level_4

    UNFCCC_Level names must exactly match the names used in the Australian
    National Greenhouse Accounts "bulk data" API.
    """
    category_list = []
    for category in categories:
        code, *level_names = category
        category_list.append(Category(code=code, api_level_names=level_names))

    return category_list


def compare_level_names(level_names_a, level_names_b) -> int:
    """
    Compare two UNFCCC categories based on the list of level names for each.
    The return value will be the number of level names that match from the
    first position onward.

    A return value that matches the length of the level names means an exact
    match.
    """
    if len(level_names_a) != len(level_names_b):
        raise ValueError("Cannot compare level names with different lengths")

    similarity = 0
    for idx in range(len(level_names_a)):
        if level_names_a[idx] != level_names_b[idx]:
            break
        similarity += 1

    return similarity


def find_category_by_name(
    category_list: list[Category],
    level_names: list[str],
) -> Category:
    """
    Given a list of UNFCCC Category objects, and a single category represented
    by a list of level names, return the Category which is the closest match.

    A match means an exact match (a Category with the exact same level names
    was found), or a parent category was found (level names match up to the
    point where the parent category no longer has names, ie:
      - ["Energy", "Fuel Combustion", "", ""] # 2nd level parent category

    Returns None if no match or parent match was found.
    """
    closest: Category | None = None
    for category in category_list:
        match_length = compare_level_names(level_names, category.api_level_names)

        # exact match
        if match_length == len(level_names):
            return category

        # no match, or the category being compared features deeper level names
        # that do not match, meaning this is not a parent of the given category
        if match_length == 0 or category.api_level_names[match_length] != "":
            continue

        if closest is None or match_length > compare_level_names(level_names, closest.api_level_names):
            closest = category

    return closest


def is_code_in_code_family(code: str, code_family: list[str]) -> bool:
    """Returns True if the provided code matches or is a sub-category of any
    code in the code family."""
    for check_code in code_family:
        if code == check_code or code.startswith(f"{check_code}."):
            return True
    return False
