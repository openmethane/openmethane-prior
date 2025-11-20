
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

For the prior we're only interested in CH4 emissions, so the full UNFCCC sector
dataset was fetched and filtered with jq:

```shell
curl -s https://greenhouseaccounts.climatechange.gov.au/OData/AR5_ParisInventory_AUSTRALIA \
  | jq --raw-output '
    (["InventoryYear_ID", "UNFCCC_Level_1", "UNFCCC_Level_2", "UNFCCC_Level_3", "UNFCCC_Level_4", "UNFCCC_Level_5", "Gg"] | @csv),
    (
      .value[]
      | select(.Gas_Level_0 == "CH4")
      | [.InventoryYear_ID, .UNFCCC_Level_1, .UNFCCC_Level_2, .UNFCCC_Level_3, .UNFCCC_Level_4, .UNFCCC_Level_5, .Gg]
      | @csv
    )
  ' \
  > AR5_ParisInventory_AUSTRALIA_CH4.csv
```

This series of commands:
- fetches the full dataset
- constructs a CSV header row
- filters the dataset to only items with `"Gas_Level_0": "CH4"`
- selects the attributes of interest
- outputs in CSV format

This filtered dataset is available in our public data store:
https://openmethane.s3.amazonaws.com/prior/inputs/AR5_ParisInventory_AUSTRALIA_CH4.csv

## UNFCCC CRT categories 

To allocate inventory emissions to prior sectors, we utilise the
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


## Land Use of Australia

Some sectoral inventories are spatialised by identifying which Australian Land
Use and Management (ALUM) Classification codes fall within those sectors, and
then distributing inventory emissions to the areas where those ALUM codes are
featured in the Land Use of Australia geographical dataset provided by the
Australian Department of Agriculture.

This is done using a combination of the official
[Land Use of Australia](https://www.agriculture.gov.au/abares/aclump/land-use/land-use-of-australia-2010-11-to-2020-21)
GeoTIFF raster, and a manual [mapping between ALUM codes and Open Methane sectors][6].

Due to issues fetching the file directly from the agriculture.gov.au service
in cloud-hosted services, the land use dataset is mirrored from the Open
Methane Public Data Store: https://openmethane.s3.amazonaws.com/prior/inputs/NLUM_v7_250_ALUMV8_2020_21_alb_package_20241128.zip


## NASA Nighttime Lights

Sectors which have a strong correlation with human / industrial activity are
spatialised using the [NASA Nighttime Lights](https://www.earthdata.nasa.gov/topics/human-dimensions/nighttime-lights)
dataset.

The nighttime lights GeoTIFF covering Australia is mirrored from the Open
Methane Public Data Store: https://openmethane.s3.amazonaws.com/prior/inputs/nasa-nighttime-lights.tiff


# Data Sources

## Sector: Livestock

Australian national dataset of CH4 flux estimates from enteric fermentation in livestock.

### Sources

Enteric fermentation emissions generated by CSIRO Ag. and Food using livestock
census data and UNFCCC emissions factors. Underlying livestock numbers
taken from: "Navarro, J. Marcos Martinez, R. (2021) Estimating long-term profits, fertiliser and pesticide use
baselines in Australian agricultural regions. User Guide. CSIRO,
Australia." 

- Dataset: [EntericFermentation.nc][3]
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

- Dataset: [termite_emissions_2010-2016.nc][8]
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

- Dataset: [DLEM_totflux_CRU_diagnostic.nc][2]
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


## Sector: Electricity

Public electricity emissions reported in the [Australian UNFCCC Inventory](#Australian-UNFCCC-Inventory)
are spatialised according to facility-level capacity.

### Sources

- Dataset: [Electricity production facilities][4]
  - Original source: [Open Electricity](https://openelectricity.org.au/)

The national inventory total for electricity emissions is pro-rated to the
location of every facility noted in Open Electricity which is
listed for the chosen period. The listed point location for each
facility is mapped to the relevant domain grid cell.


## Sector: Fugitive

Fugitive emissions reported in the [Australian UNFCCC Inventory](#Australian-UNFCCC-Inventory)
are spatialised according to facility-level estimates.

### Sources

- Dataset: [Coal mining sources][5]
  - Original source: [ClimateTrace](https://climatetrace.org/)
- Dataset: [Oil and gas production sources][7]
  - Original source: [ClimateTrace](https://climatetrace.org/)

The national inventory total for fugitive emissions is pro-rated to the
location of every facility noted in the ClimateTrace data which is
listed for the chosen period. The listed point location for each
climate trace emission is mapped to the relevant domain grid cell.


## Sector: Industrial

Industrial emissions reported in the [Australian UNFCCC Inventory](#Australian-UNFCCC-Inventory) are
spatialised according to [NASA Nighttime Lights](#NASA-Nighttime-Lights).


## Sector: Land Use, Land Use Change, and Forestry (LULUCF)

LULUCF sector emissions reported in the [Australian UNFCCC Inventory](#Australian-UNFCCC-Inventory) are
spatialised according to the [Land Use of Australia](#Land-Use-of-Australia) dataset.


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

[1]: https://openmethane.s3.amazonaws.com/prior/inputs/AUS_2021_AUST_SHP_GDA2020.zip
[2]: https://openmethane.s3.amazonaws.com/prior/inputs/DLEM_totflux_CRU_diagnostic.nc
[3]: https://openmethane.s3.amazonaws.com/prior/inputs/EntericFermentation.nc
[4]: https://openmethane.s3.amazonaws.com/prior/inputs/ch4-electricity.csv
[5]: https://openmethane.s3.amazonaws.com/prior/inputs/coal-mining_emissions-sources.csv
[6]: https://openmethane.s3.amazonaws.com/prior/inputs/landuse-sector-map.csv
[7]: https://openmethane.s3.amazonaws.com/prior/inputs/oil-and-gas-production-and-transport_emissions-sources.csv
[8]: https://openmethane.s3.amazonaws.com/prior/inputs/termite_emissions_2010-2016.nc
