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

def is_code_in_code_family(code: str, code_family: list[str]) -> bool:
    """Returns True if the provided code matches or is a sub-category of any
    code in the code family."""
    for check_code in code_family:
        if code == check_code or code.startswith(f"{check_code}."):
            return True
    return False
