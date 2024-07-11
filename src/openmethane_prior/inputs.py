#
# Copyright 2023 The Superpower Institute Ltd.
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
"""Input file definitions and checks"""

import os
import sys

from openmethane_prior.config import PriorConfig


def check_input_files(config: PriorConfig):
    """
    Check that all required input files are present

    Exits with an error code of 1 if all required files are not available
    """
    print("### Checking input files...")

    errors = []

    if not config.input_domain_file.exists():
        errors.append(
            f"Missing file for domain info at {config.input_domain_file}, "
            f"suggest running scripts/omCreateDomainInfo.py"
        )

    checks = (
        (config.layer_inputs.electricity_path, "electricity facilities"),
        (config.layer_inputs.coal_path, "Coal facilities"),
        (config.layer_inputs.oil_gas_path, "Oilgas facilities"),
        (config.layer_inputs.land_use_path, "land use"),
        (config.layer_inputs.sectoral_emissions_path, "sectoral emissions"),
        (config.layer_inputs.sectoral_mapping_path, "sectoral emissions mappings"),
        (config.layer_inputs.ntl_path, "night time lights"),
        (config.layer_inputs.livestock_path, "livestock data"),
        (config.layer_inputs.termite_path, "termite data"),
        (config.layer_inputs.wetland_path, "wetlands data"),
    )

    for path, desc in checks:
        if not os.path.exists(config.as_input_file(path)):
            errors.append(f"Missing file for {desc} at {path}")

    ## Print all errors and exit (if we have any errors)
    if len(errors) > 0:
        print(
            "Some required files are missing. "
            "Suggest running omDownloadInputs.py if you're using the default input file set, "
            "and omCreateDomainInfo.py if you haven't already. See issues below."
        )
        print("\n".join(errors))
        sys.exit(1)
