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

"""Process fugitive Methane emissions"""

import argparse
import datetime
import math

import numpy as np
import pandas as pd

from openmethane_prior.omInputs import (
    coalPath,
    domainProj,
    oilGasPath,
    sectoralEmissionsPath,
)
from openmethane_prior.omInputs import domainXr as ds
from openmethane_prior.omOutputs import convert_to_timescale, sumLayers, write_layer


def processEmissions(startDate, endDate):
    """
    Process the fugitive methane emissions

    Adds the OCH4_FUGITIVE layer to the output

    Parameters
    ----------
    startDate
        The year used to calculate the emissions
    endDate
        Ignored
    """
    print("processEmissions for fugitives")
    fugitiveEmis = pd.read_csv(sectoralEmissionsPath).to_dict(orient="records")[0][
        "fugitive"
    ]  # national total from inventory
    fugitiveEmis *= 1e9  # convert to kg
    # now read climate_trace facilities emissions for coal, oil and gas
    coalFacilities = pd.read_csv(coalPath)
    oilGasFacilities = pd.read_csv(oilGasPath)
    fugitiveFacilities = pd.concat((coalFacilities, oilGasFacilities))

    # select gas and year
    fugitiveCH4 = fugitiveFacilities.loc[fugitiveFacilities["gas"] == "ch4"]
    fugitiveCH4.loc[:, "start_time"] = pd.to_datetime(fugitiveCH4["start_time"])
    targetDate = (
        startDate
        if startDate <= fugitiveCH4["start_time"].max()
        else fugitiveCH4["start_time"].max()
    )  # startDate or latest Date in data
    years = np.array([x.year for x in fugitiveCH4["start_time"]])
    mask = years == targetDate.year
    fugitiveYear = fugitiveCH4.loc[mask, :]
    # normalise emissions to match inventory total
    fugitiveYear.loc[:, "emissions_quantity"] *= (
        fugitiveEmis / fugitiveYear["emissions_quantity"].sum()
    )
    landmask = ds["LANDMASK"][:]

    _, lmy, lmx = landmask.shape
    ww = ds.DX * lmx
    hh = ds.DY * lmy

    methane = np.zeros(landmask.shape)

    for _, facility in fugitiveYear.iterrows():
        x, y = domainProj(facility["lon"], facility["lat"])
        ix = math.floor((x + ww / 2) / ds.DX)
        iy = math.floor((y + hh / 2) / ds.DY)
        try:
            methane[0][iy][ix] += facility["emissions_quantity"]
        except IndexError:
            pass  # it's outside our domain

    write_layer("OCH4_FUGITIVE", convert_to_timescale(methane))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Calculate the prior methane emissions estimate for OpenMethane"
    )
    parser.add_argument(
        "startDate",
        type=lambda s: datetime.datetime.strptime(s, "%Y-%m-%d"),
        help="Start date in YYYY-MM-DD format",
    )
    parser.add_argument(
        "endDate",
        type=lambda s: datetime.datetime.strptime(s, "%Y-%m-%d"),
        help="end date in YYYY-MM-DD format",
    )
    args = parser.parse_args()
    processEmissions(args.startDate, args.endDate)
    sumLayers()
