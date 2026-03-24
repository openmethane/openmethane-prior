
# Overview

Open Methane Prior uses a variety of data sources to estimate emissions from
known methane emission sources. Broadly, these data sources fall into two
categories:
- emission estimates from existing sources
- spatial proxies for methane emissions

## Estimates from existing sources

Gridded methane emission estimates have already been produced for some sectors
in published research or publicly available datasets. Where possible, these
estimates are simply regridded onto the Open Methane grid.

## Estimates from spatial proxies

Where no pre-existing gridded estimates are available, the Open Methane Prior
estimates emissions by taking the sectoral total from the
[National Greenhouse Gas Inventory](https://www.dcceew.gov.au/climate-change/publications/national-greenhouse-gas-inventory-quarterly-updates)
and distributing the emissions based on a spatial dataset that is shown to be a
good proxy for methane emissions in that sector.

For example, light pollution is a good spatial proxy for industrial activity.
Therefore, a map of nighttime light in Australia can be used to distribute
the industrial sectoral emissions from the national inventory spatially. We
must take care to ensure that the sectoral estimate and the spatial proxy
cover the exact same domain, or the spatial proxy must be masked.

The spatialised estimates are then regridded onto the Open Methane grid.


# General data sources

Some data sources are used by multiple sectors of the prior.

## Australian UNFCCC Inventory

Australia reports GHG emissions broken down by gas and by sector under its
UNFCCC obligations. The data is available via the
[National Greenhouse Accounts](https://greenhouseaccounts.climatechange.gov.au/)
web tool, and also via a "Bulk data API".

Specifically, the `AR5_ParisInventory_AUSTRALIA` dataset contains per-gas
emissions broken down by UNFCCC category. This dataset is fetched directly from
ANGA, and non-CH4 emissions are discarded, resulting in per-year, per-sector
CH4 emissions which can be used as the basis for the total emissions in
anthropogenic sectors.


## UNFCCC CRT categories 

To allocate ANGA inventory emissions to prior sectors, we utilise the
`unfccc_categories` in each sector, which contain UNFCCC CRT category codes,
like "5" (Waste), "3.B" (Agriculture - Enteric Fermentation). However, the
[Australian UNFCCC Inventory](#Australian-UNFCCC-Inventory) doesn't include
category codes, only full names of the UNFCCC categories (some of which are
not exact from the original definitions).

A mapping from Australia's inventory categories to UNFCCC has been created to
assist this process. The mapping was created manually by fetching all the
category names present in the Australian inventory, and assigning the correct
code to each category.

File can be created initially by finding unique categories in the bulk data:

```shell
curl -s https://greenhouseaccounts.climatechange.gov.au/OData/AR5_ParisInventory_AUSTRALIA \
  | jq --raw-output '
    (["UNFCCC_Code", "UNFCCC_Level_1", "UNFCCC_Level_2", "UNFCCC_Level_3", "UNFCCC_Level_4"] | @csv),
    (
      .value[]
      | select(.Gas_Level_0 == "CH4")
      | ["", .UNFCCC_Level_1, .UNFCCC_Level_2, .UNFCCC_Level_3, .UNFCCC_Level_4]
      | @csv
    )
  ' \
  | uniq \
  > UNFCCC-codes.csv
```

Note: this excludes level 5 categorisation, where codes are sometimes harder to
identify and prior sectors are unlikely to model categories to this level.

This generates a file with empty values for "UNFCCC_Code" which must then be
populated manually.

The completed mapping is available in our public data store:
https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv


## Safeguard Mechanism Baselines and Emissions

Starting in the 2023-24 financial year, Safeguard Mechanism reporting includes
per-facility CO2-equivalent emissions estimates for multiple greenhouse gases,
including methane. These estimates are provided by the operating entity to the
Clean Energy Regulator, and made public in the
[Safeguard Mechanism Baselines and Emissions Table](https://cer.gov.au/markets/reports-and-data/safeguard-data/2023-24-baselines-and-emissions-data#baselines-and-emissions-table).

Each "emissions number" reported in the Baselines and Emissions Table uses a
unit of "tonnes of carbon dioxide equivalent" (tCO2-e), including the
"GHG Methane" number. Based on the CER legislation, this number must be
calculated using [AR5 global warming potential](https://cer.gov.au/schemes/national-greenhouse-and-energy-reporting-scheme/about-emissions-and-energy-data/global-warming-potential#summary-of-updates-to-gwp-values)
numbers for CO2 and CH4.

Each facility in the dataset includes an ANZSIC sector classification, which
allows us to determine which prior sector the facility should be included in.
Lastly, correlating the Safeguard Mechanism facility with a location in a
supporting dataset allows us to place those emissions in the correct grid cell
or grid cells.


## Land Use of Australia

Some sectoral inventories are spatialised by identifying which Australian Land
Use and Management (ALUM) Classification codes fall within those sectors, and
then distributing inventory emissions to the areas where those ALUM codes are
featured in the Land Use of Australia geographical dataset provided by the
Australian Department of Agriculture.

This is done using a combination of the official
[Land Use of Australia](https://www.agriculture.gov.au/abares/aclump/land-use/land-use-of-australia-2010-11-to-2020-21)
GeoTIFF raster, and a manual [mapping between ALUM codes and Open Methane sectors][4].

Due to issues fetching the file directly from the agriculture.gov.au service
in cloud-hosted services, the land use dataset is mirrored from the Open
Methane Public Data Store: https://openmethane.s3.amazonaws.com/prior/inputs/NLUM_v7_250_ALUMV8_2020_21_alb_package_20241128.zip


## NASA Nighttime Lights

Sectors which have a strong correlation with human / industrial activity are
spatialised using the [NASA Nighttime Lights](https://www.earthdata.nasa.gov/topics/human-dimensions/nighttime-lights)
dataset.

The nighttime lights GeoTIFF covering Australia is mirrored from the Open
Methane Public Data Store: https://openmethane.s3.amazonaws.com/prior/inputs/nasa-nighttime-lights.tiff


## Climate TRACE

Climate TRACE provides a global dataset of greenhouse gas emission sources
across many sectors of human activity. Open Methane uses the Australia CH4
"country pacakge" which includes emissions sources such as coal mines and oil
and gas production.

The package is available from the [Climate TRACE Data](https://climatetrace.org/data)
page by selecting:
- View downloads by: Country
- Select Emission Type: CH4
- Download the Australia CSV package


# Data Sources

## Sector: Livestock

Australian national dataset of CH4 flux estimates from enteric fermentation in livestock.

### Sources

Enteric fermentation emissions generated by CSIRO Ag. and Food using livestock
census data and UNFCCC emissions factors. Underlying livestock numbers
taken from: "Navarro, J. Marcos Martinez, R. (2021) Estimating long-term profits, fertiliser and pesticide use
baselines in Australian agricultural regions. User Guide. CSIRO,
Australia." 

- Dataset: [EntericFermentation.nc][2]
- Resolution: 0.01 degree
- Period: 2020, single annual average
- Updates: never

### Considerations

- Spatial distribution might change during the year since farmers are moving their cows around
- Doesn't appear to be available online

### Alternative candidates

- https://publications.csiro.au/publications/publication/PIcsiro:EP2022-1389/
  - Resolution: 0.1 degree
  - Period: 1972 - 2019, annual averages
  - Global
- Electronic ear tags might be a useful database


## Sector: Termites

Global dataset of CH4 flux estimates from termites.

### Sources

Termite emissions used in [Saunois et al. 2020](https://essd.copernicus.org/articles/12/1561/2020/)
supplied by Simona Castaldi and Sergio Noce.

- Dataset: [termite_emissions_2010-2016.nc][5]
- Resolution: 0.5 degree
- Period: mean of 2010 – 2016
- Updates: never

### Considerations

- No Australian database
- Rough spatial resolution
- Database doesn't appear to be available online
  - Source dataset for
    [Global Methane Budget 2000-2017](https://essd.copernicus.org/articles/12/1561/2020/essd-12-1561-2020.html)

### Alternative candidates

- https://ads.atmosphere.copernicus.eu/datasets/cams-global-emission-inventories?tab=overview
    - Same resolution: 0.5 degree
    - Temporal coverage for termites is stated as 2000, but the
      [documentation](https://atmosphere.copernicus.eu/sites/default/files/2019-11/26_CAMS81_2017SC1_D81.3.4.1-201808_v1_APPROVED_Ver1.pdf)
      claims termite estimates "representative for the years 2000 - 2017".
    - Includes monthly estimates which feature seasonal variation in Australia
    - Publicly available and referenceable


## Sector: Biomass burning

Global dataset of CH4 flux estimates from biomass burning (wildfires)

### Sources

Daily emissions from the Global Fire Assimilation System (Kaiser et al., 2012, doi:10.5194/bg-9-527-2012)

- Dataset: https://ads.atmosphere.copernicus.eu/datasets/cams-global-fire-emissions-gfas?tab=overview
- Resolution: 0.1 degree
- Period: 2003 - present
- Updates: daily, 2 day delay


## Sector: Wetlands

### Sources

Monthly wetland emissions from the diagnostic ensemble used in
[Saunois et al. 2020](https://essd.copernicus.org/articles/12/1561/2020/)
and described in Zhang et al. (2023 under review) (could this be https://essd.copernicus.org/articles/13/2001/2021/?)

- Dataset: [DLEM_totflux_CRU_diagnostic.nc][1]
- Resolution: 0.5 degree
- Period: 2000 - 2020, monthly averages
- Updates: never

### Considerations

- No Australian database
- Rough spatial resolution
- Database/paper doesn't appear to be available online
- There is a new version of Global Methane Budget (2000 - 2024), can we get an updated dataset?

### Alternative candidates

- https://www.icos-cp.eu/GCP-CH4-2024
  - Resolution: 1.0 degrees
  - Period: 2000, monthly averages


## Sector: Agriculture

Agricultural emissions (excluding livestock) reported in the
[Australian UNFCCC Inventory](#Australian-UNFCCC-Inventory)
are spatialised according to the [Land Use of Australia](#Land-Use-of-Australia) dataset.


## Sector: Coal

Solid fuel (coal) emissions reported in the
[Australian UNFCCC Inventory](#Australian-UNFCCC-Inventory)
are spatialised according to facility-level estimates.

Facility estimates are taken from
[Safeguard Mechanism estimates](#Safeguard-Mechanism-Baselines-and-Emissions)
if available, using facility locations published by [Climate TRACE](#Climate-TRACE).

For facilities not covered by the Safeguard Mechanism, the National Inventory
total for solid fuel emissions, minus emissions already allocated to Safeguard
facilities, is pro-rated to the facility noted in the ClimateTrace data. The
listed point location for each facility is mapped to the relevant grid cell.


## Sector: Electricity

Public electricity emissions reported in the [Australian UNFCCC Inventory](#Australian-UNFCCC-Inventory)
are spatialised according to facility-level capacity.

### Sources

- Dataset: [Electricity production facilities][3]
  - Original source: [Open Electricity](https://openelectricity.org.au/)

The national inventory total for electricity emissions is pro-rated to the
location of every facility noted in Open Electricity which is
listed for the chosen period. The listed point location for each
facility is mapped to the relevant domain grid cell.


## Sector: Industrial

Industrial emissions reported in the [Australian UNFCCC Inventory](#Australian-UNFCCC-Inventory) are
spatialised according to [NASA Nighttime Lights](#NASA-Nighttime-Lights).


## Sector: Land Use, Land Use Change, and Forestry (LULUCF)

LULUCF sector emissions reported in the [Australian UNFCCC Inventory](#Australian-UNFCCC-Inventory) are
spatialised according to the [Land Use of Australia](#Land-Use-of-Australia) dataset.


## Sector: Oil and Gas

Oil and gas emissions reported in the
[Australian UNFCCC Inventory](#Australian-UNFCCC-Inventory)
are spatialised according to locations of oil and gas boreholes/wells which lie
within petroleum titles/leases that were active during the period of interest.

### Sources

- New South Wales datasets:
  - [Data.NSW - Coal Seam Gas Boreholes](https://data.nsw.gov.au/data/dataset/coal-seam-gas-borehole)
  - [Data.NSW - NSW Drillholes Petroleum](https://data.nsw.gov.au/data/dataset/nsw-drillholes-petroleum)
  - [Data.NSW - NSW Exploration and Mining Titles](https://data.nsw.gov.au/data/dataset/nsw-mining-titles)
- Northern Territory datasets:
  - [STRIKE](http://strike.nt.gov.au/wss.html)
    - Downloads -> Petroleum Titles and Pipeline Titles -> All Petroleum and Pipeline Titles Layers
    - Downloads -> Drilling -> Petroleum Wells
- Queensland datasets:
  - [Queensland borehole series](https://www.data.qld.gov.au/dataset/queensland-borehole-series)
  - [Queensland mining and exploration tenure series](https://www.data.qld.gov.au/dataset/queensland-mining-and-exploration-tenure-series)
- Western Australia datasets:
  - [WA Petroleum Wells (DMIRS-025)](https://catalogue.data.wa.gov.au/dataset/wa-onshore-petroleum-wells-dmirs-025)
  - [WA Petroleum Titles (DMIRS-011)](https://catalogue.data.wa.gov.au/dataset/wa-petroleum-titles-dmirs-011)
- Offshore datasets:
  - [National Offshore Petroleum Information Management System (NOPIMS)](https://www.nopta.gov.au/maps-and-public-data/nopims-info.html)
  - [National Electronic Approvals Tracking System](https://public.neats.nopta.gov.au/)

Locations of every borehole/drillhole/well in the public datasets from NSW, NT,
QLD, WA and NOPTA are correlated with petroleum production titles and filtered
to only bores involved in petroleum production where the title period overlaps
with the prior period of interest.

The national inventory total for oil and gas emissions is divided evenly between
these sites. The listed point location for each site is mapped to the relevant
domain grid cell, where emissions are allocated.

### Considerations

The approach used to spatialise the oil and gas sector has several known flaws.

1. Capped wells

First and foremost, although some datasets list many bores/wells as "capped" or
"abandoned", they don't include the date when the capping occurred. For this
reason we consider every production well to be an emission source until the
date of expiry of the title. This could be incorrect in both ways: wells very
likely stop emitting methane when they are capped, and in that case this leads
to many false positives within the datasets. Alternatively, capped wells may
continue to emit methane after production (and the title) has ended, leading to
missing emissions on abandoned fields.

2. Attribution of inventory emissions

Attribution of equal emissions to every "active" bore/well is also
very naive. Wells for different resources (i.e. oil vs coal seam gas) or in
different regions (WA vs NSW) or in different infrastructure (onshore vs
offshore) are likely to have very different emission profiles. Until we have
solid evidence of what these profiles might be, we cannot model them.

3. Refineries and pipelines

Several types of major infrastructure are currently missing from this approach:
refineries and pipelines. This is a major omission, as there is reasonable
suspicion that the majority of emissions occur at processing facilities. We
hope to add these facilities at a later date.

4. Missing regions

- South Australia
  - not yet implemented
- Victoria
  - oil and gas extraction currently entirely offshore, present in NOPTA dataset
- ACT
  - no oil or gas production to date


## Sector: Stationary

Stationary emissions reported in the [Australian UNFCCC Inventory](#Australian-UNFCCC-Inventory) are
spatialised according to [NASA Nighttime Lights](#NASA-Nighttime-Lights).


## Sector: Transport

Transport sector emissions reported in the [Australian UNFCCC Inventory](#Australian-UNFCCC-Inventory) are
spatialised according to [NASA Nighttime Lights](#NASA-Nighttime-Lights).


## Sector: Waste

Waste sector emissions reported in the [Australian UNFCCC Inventory](#Australian-UNFCCC-Inventory) are
spatialised according to the [Land Use of Australia](#Land-Use-of-Australia) dataset.


# Assets

[1]: https://openmethane.s3.amazonaws.com/prior/inputs/DLEM_totflux_CRU_diagnostic.nc
[2]: https://openmethane.s3.amazonaws.com/prior/inputs/EntericFermentation.nc
[3]: https://openmethane.s3.amazonaws.com/prior/inputs/ch4-electricity.csv
[4]: https://openmethane.s3.amazonaws.com/prior/inputs/landuse-sector-map.csv
[5]: https://openmethane.s3.amazonaws.com/prior/inputs/termite_emissions_2010-2016.nc
