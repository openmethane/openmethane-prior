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

Before installation, you will need to make sure that
[uv](https://docs.astral.sh/uv/getting-started/installation/)
is installed.

### Installation

The Open Methane prior can be installed from source into a virtual environment with:

```bash
uv sync
```

### Input Data

Input data will be downloaded on-demand by the layers that use it while running
omPrior.py. To inspect where data is fetched from, look for instances of
`DataSource` defined in each layer.

The downloaded files will be stored in the path specified in `INPUTS` env var
(`data/inputs` by default).

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

### All sectors

To calculate emissions for all sectors, run `omPrior.py` with a start and end date:

```shell
uv run python scripts/omPrior.py --start-date 2022-07-01 --end-date 2022-07-01
```

This takes a while to process (~10 minutes) with the vast majority of that time
spent on the sectors which re-project large input datasets.

### Specific sectors

To run a single sector or a subset of sectors, use the `--sectors` argument:

```shell
uv run python scripts/omPrior.py --start-date 2022-07-01 --end-date 2022-07-01 \
  --sectors livestock,termite,fire
```

Sectors must be separated by commas, without spaces, using the value from the
desired PriorSector `name` attribute.

### Console output

The detail of console output can be controlled by setting the `LOG_LEVEL` env
variable. By default, this is set to `INFO`, but more or less can be achieved
by setting other log levels:

```shell
# verbose debug output
LOG_LEVEL=DEBUG uv run python scripts/omPrior.py --start-date 2022-07-01 --end-date 2022-07-01

# only warnings and errors
LOG_LEVEL=WARNING uv run python scripts/omPrior.py --start-date 2022-07-01 --end-date 2022-07-01
```

Log output can also be written to a file while still logging to the console
with the `LOG_FILE` env variable.

```shell
LOG_FILE=/var/log/prior.log uv run python scripts/omPrior.py --start-date 2022-07-01 --end-date 2022-07-01
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
  This folder should contain all the required input files. Any missing input data
  will be fetched automatically while running the prior (see
  [Input Data](#input-data) for more detail).
* `data/intermediates` This folder contains any intermediate files generated
  through the process. Everything within this folder should be ignored.
* `data/outputs` Outputs files will be saved here.


## Run in a Docker container

To carry out the steps described above in a Docker container, first build the Docker image with

```
make build
```

Then run the commands to with the project path mounted as a volume:

```
docker run --rm -v </your/path/to/openmethane-prior>:/opt/project openmethane-prior python scripts/omPrior.py --start-date 2022-12-07
```

Replace the python files according to the commands in the Makefile for the other steps.

Note: the CDS API credentials will also need to be provided via .env file to run
via docker.

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
