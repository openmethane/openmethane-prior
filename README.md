# Open Methane Prior emissions estimate

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


### Requirements

Before installation, you will need to make sure that [poetry](https://python-poetry.org/docs/) version 1 is installed.

Step-by-step:
- Install pipx 
```bash
python -m pip install --user pipx
```

- Install poetry and downgrading your poetry version to version v1.
```bash
pipx install poetry~=1.0 --force
```


### Installation

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

The domain of interest for the prior is defined using an input domain netCDF
file. The format of the input domain is based on the CMAQ domain file format,
but updated to follow (CF Conventions)[https://cfconventions.org/cf-conventions/cf-conventions.html].

Note that the input domain uses a staggered grid, so `x`, `y` coordinates, as
well as `lat`, `lon` coordinates, represent the center point of each grid cell.
The edges of each grid cell are made available in `x_bounds` and `y_bounds`
based on the CF Conventions "bounds" methodology.

This domain input file should contain the following:

* Coordinates:
  * `x`
  * `y`
* Variables 
  * `lat`
  * `lon`
  * `x_bounds`
  * `y_bounds`
  * `land_mask` - binary land/sea mask
  * `lambert_conformal` - projection details
  * `cell_name` - unique name for each grid cell based on grid.x.y format
  * (Optionally) `inventory_mask` - binary mask denoting the area covered by
    the inventory figures present in the input files
* Attributes
  * `DX`/`XCELL` - size of each grid cell in grid projection coordinates
  * `DY`/`YCELL` - size of each grid cell in grid projection coordinates
  * `domain_name` - the name of the domain of interest
  * `domain_version` - a version string for the domain, typically `v1`, `v2`, etc
  * `domain_slug` - a short, URL-safe name for the grid, often the same as `domain_name`

As part of the [Open Methane](https://openmethane.org/) project,
we have provided a domain file for a 10km grid over Australia.

This file will be downloaded with the other layer inputs (see [Source data](#source-data))
using the default configuration values.

A new domain can be created using one of the provided scripts:
- `scripts/create_prior_domain.py`
  - create a domain from WRF and MCIP files
- `scripts/create_subset_domain.py`
  - create a domain by subsetting an existing Open Methane domain

Or you can use these scripts as the basis for creating your domain from other
sources.

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
poetry run python scripts/omPrior.py --start-date 2022-07-01 --end-date 2022-07-01
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
poetry run python src/openmethane_prior/layers/omWetlandEmis.py --start-date 2022-07-01 --end-date 2022-07-01
```

### Console output

The detail of console output can be controlled by setting the `LOG_LEVEL` env
variable. By default, this is set to `INFO`, but more or less can be achieved
by setting other log levels:

```shell
# verbose debug output
LOG_LEVEL=DEBUG poetry run python scripts/omPrior.py --start-date 2022-07-01 --end-date 2022-07-01

# only warnings and errors
LOG_LEVEL=WARNING poetry run python scripts/omPrior.py --start-date 2022-07-01 --end-date 2022-07-01
```

Log output can also be written to a file while still logging to the console
with the `LOG_FILE` env variable.

```shell
LOG_FILE=/var/log/prior.log poetry run python scripts/omPrior.py --start-date 2022-07-01 --end-date 2022-07-01
```


## Outputs

Outputs can be found in the `data/outputs` folder. The emissions layers will be written as variables to a copy of the
input domain file, with an `ch4_sector_` prefix for the methane layer variable names. The sum of all layers will be stored in
the `ch4_total` layer.

The name of the layered output file will be `om-prior-output.nc`.

The `data/processed` folder will contain any re-projected raster data, and any files downloaded or generated in the
process.

Outputs can be plotted using the ncl file `plot_emis.ncl`. 

```console 
ncl plot_emis.ncl
```

## Source data

For details about all data sources used by the prior, see [Data sources](./docs/data-sources.md).

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
