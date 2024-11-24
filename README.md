# OpenMethane prior emissions estimate

Method to calculate a gridded, prior emissions estimate for methane across Australia.

This repository is matched with downloadable input data so that it will run out of the box.

## Initialise

Copy the `.env.example` file to `.env` and customise the paths as you need.

In order to download the GFAS emissions data, credentials for the Copernicus
Atmospheric Data Store (ADS) API are required. Instructions for registering for
the ADS API and setting up the credentials are provided at 
[ADS Docs](https://ads.atmosphere.copernicus.eu/how-to-api).

Step-by-step:
- Register for an [ECMWF](https://www.ecmwf.int/) account
- While logged in to ECMWF, register your account with [ADS](https://ads.atmosphere.copernicus.eu/)
- Accept the ADS terms and conditions
- Accept the License to use Copernicus products, by visiting the Download tab of the dataset you wish to use and scrolling to the Terms of use section: https://ads.atmosphere.copernicus.eu/datasets/cams-global-fire-emissions-gfas?tab=download

Note: the ADS API is different from the CDS (Climate Data Store) API
even though they are both parts of the Copernicus program
and share the same credentials file.

### Installation

To get started, you will need to make sure that [poetry](https://python-poetry.org/docs/) is installed.
The Open Methane prior can be installed from source into a virtual environment with:

```bash
make virtual-environment
```

The `Makefile` contains the set of commands to create the virtual environment.
You can read the instructions out and run the commands by hand if you wish.

### Input Data

To download all the required input files, run:

```console
make download
```

This will download input files that match the data in `.env`,
so you have a working set to get started with.

The downloaded files will be stored in `data/inputs` by default.

### Domain Info

The domain of interest for the prior is defined using an input domain netCDF file.
The format of the input domain is based on the CMAQ domain file format. Note that CMAQ uses a
[staggered grid](https://www.cmascenter.org/ioapi/documentation/all_versions/html/GRIDS.jpg)
where some quantities are defined at the center of a grid cell, whereas other quantities are defined
at the edges of a grid cell. This circumstance is represented in  `ROW_D = ROW + 1`.

This input file should contain the following variables:

* `LAT`
* `LON`
* `LANDMASK`
* `LATD`
* `LOND`

The contents of the default domain is shown below:

```
>>> ncdump -h prior_domain_aust10km_v1.0.0.d01
netcdf prior_domain_aust10km_v1.0.0.d01 {
dimensions:
        TSTEP = 1;
        ROW = 430;
        COL = 454;
        LAY = 1;
        ROW_D = 431;
        COL_D = 455;
variables:
        float LAT(TSTEP, ROW, COL);
                LAT:_FillValue = NaNf;
                LAT:long_name = "LAT";
                LAT:units = "DEGREES";
                LAT:var_desc = "latitude (south negative)";
        float LON(TSTEP, ROW, COL);
                LON:_FillValue = NaNf;
                LON:long_name = "LON";
                LON:units = "DEGREES";
                LON:var_desc = "longitude (west negative)";
        float LANDMASK(TSTEP, ROW, COL);
                LANDMASK:_FillValue = NaNf;
                LANDMASK:long_name = "LWMASK";
                LANDMASK:units = "CATEGORY";
                LANDMASK:var_desc = "land-water mask (1=land, 0=water)";
        float LATD(TSTEP, LAY, ROW_D, COL_D);
                LATD:_FillValue = NaNf;
                LATD:long_name = "LATD";
                LATD:units = "DEGREES";
                LATD:var_desc = "latitude (south negative) -- dot point";
        float LOND(TSTEP, LAY, ROW_D, COL_D);
                LOND:_FillValue = NaNf;
                LOND:long_name = "LOND";
                LOND:units = "DEGREES";
                LOND:var_desc = "longitude (west negative) -- dot point";

// global attributes:
                :DX = 10000.f;
                :DY = 10000.f;
                :TRUELAT1 = -15.f;
                :TRUELAT2 = -40.f;
                :MOAD_CEN_LAT = -27.644f;
                :STAND_LON = 133.302f;
                :XCELL = 10000.;
                :YCELL = 10000.;
                :XCENT = 133.302001953125;
                :YCENT = -27.5;
                :XORIG = -2270000.;
                :YORIG = -2165629.25;
}
```

As part of the [OpenMethane](https://openmethane.org/) project,
we have provided a domain file for a 10km grid over Australia.

This file will be downloaded with the other layer inputs (see [Input Data](#input-data)) using the default configuration
values.

### Clean outputs

These two commands are set up so that not all generated files have to be deleted manually
Delete all files in the `intermediates` and `outputs` directory with

```
make clean
```

Or delete all files in `intermediates`, `outputs`, and `inputs` directory with

```
make clean-all
```

## Run

### All layers

To calculate emissions for all layers, run `omPrior.py` with a start and end date:

```
poetry run python scripts/omPrior.py 2022-07-01 2022-07-01
```

or use the make target

```console
make run
```

This takes a while to process (~10 minutes) with the vast majority of that time spent on the layers
in `omAgLulucfWasteEmis.py`.

To skip re-projecting raster layers (you only need to do this once for every time you change the raster input files),
add the `--skip-reproject` option.

### Single layers

You can run and re-run individual layers one-by-one. Just run each file on it's own (GFAS and Wetlands require a start
and end date as below):

```console
poetry run python src/layers/omWetlandEmis.py 2022-07-01 2022-07-02
```

## Outputs

Outputs can be found in the `data/outputs` folder. The emissions layers will be written as variables to a copy of the
input domain file, with an `OCH4_` prefix for the methane layer variable names. The sum of all layers will be stored in
the `OCH4_TOTAL` layer.

The name of the layered output file will be `om-prior-output.nc`.

The `data/processed` folder will contain any re-projected raster data, and any files downloaded or generated in the
process.

## Layers

Many sectors are taken from data sets used in by Saunois et al (2020) (doi:10.5194/essd-12-1561-2020)

- Livestock: Enteric fermentation emissions generated by CSIRO Ag. and Food using livestock census data and UNFCCC
  emissions factors
- Electricity: Uses OpenNEM facility data to spatialise the Aust. Gov UNFCCC electricity emissions
- Agriculture: Agricultural emissions apart from livestock taken from the Agricultural emissions of the NGGI and
  spatialised according to the agriculture land-use mask
- Fugitives: Facility-level data from ACF (more info?)
- Industrial: Spatialises the industrial sector of the NGGI according to nighttime lights
- Stationary: Spatialises the stationary energy sector of the NGGI according to nighttime lights
- Transport: Spatialises the transport sector of the NGGI according to nighttime lights
- Waste: Spatialises the NGGI waste emission according to the landuse map
- LULUCF: Spatialises the LULUCF emission from the NGGI according to the landuse map
- FIRE: daily emissions from the Global Fire Assimilation System (Kaiser et al., 2012, doi:10.5194/bg-9-527-2012)
- wetland: Monthly wetland emissions from the diagnostic ensemble used in Saunois et al. 2020 and described in Zhang et
  al. (2023 under review)
- Termite: Termite emissions used in Saunois et al. 2020 supplied by Simona Castaldi and Sergio Noce

## Data directories

* `data/inputs` 
This folder should contain all the required input files, which should be referenced in the `.env` file at the root.
A set of input files has been included in the repository so that it functions out of the box (see [Input Data](#input-data)), but you can add your own
data here.
* `data/inputs/domains` The domain of interest is stored in this folder (see [domain info](#domain-info)).
* `data/intermediates` This folder contains any intermediate files generated through the process. Everything within this folder should be ignored.
* `data/outputs` Outputs files will be saved here.


## Run in a Docker container

To carry out the steps described above in a Docker container, first build the Docker image with

```
make build
```

Then run the commands to download the input data in the docker container

```
docker run --rm -v </your/path/to/openmethane-prior>:/opt/project openmethane-prior python scripts/omDownloadInputs.py
```

Replace the python files according to the commands in the Makefile for the other steps.

## For developers

The ruff-fixes target runs a series of ruff commands to format the code, check and fix linting
issues, and then format the code again to ensure that all formatting and fixes are applied.

```
make ruff-fixes
```

The test target will run all the tests

```
make test
```
