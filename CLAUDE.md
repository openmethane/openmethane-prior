# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

`openmethane-prior` calculates gridded prior emissions estimates for methane across Australia. It reads a domain NetCDF file, downloads/caches input data from multiple sources, and produces a NetCDF output with per-sector and total methane emissions on the domain grid.

## Common Commands

```bash
uv sync                  # Install dependencies
make test                # Run all tests
make format              # Format code with Ruff
make run-example         # Run for test date 2022-07-01

# Run a single test file
uv run python -m pytest tests/unit/test_livestock.py -v

# Run the prior for a date range
uv run python scripts/omPrior.py --start-date 2022-07-01 --end-date 2022-07-31

# Run specific sectors only
uv run python scripts/omPrior.py --start-date 2022-07-01 --end-date 2022-07-31 --sectors livestock,termite,fire
```

**Package manager**: `uv` (not pip). Always use `uv run` or `uv sync`.

## Architecture

### Entry Point

`scripts/omPrior.py` — parses CLI args, loads config, iterates over requested sectors, writes output NetCDF.

### Core Library (`src/openmethane_prior/lib/`)

- **`config.py`**: `PriorConfig` — all runtime config loaded from `.env` and CLI args (paths, domain file, date range, sectors)
- **`create_prior.py`**: Main orchestration — calls each sector, aggregates results, handles output
- **`grid/`**: Domain/grid handling; supports CF-convention NetCDF with Lambert Conformal projection (also legacy MCIP format)
- **`sector/sector.py`**: `PriorSector` dataclass — defines the interface every sector must implement
- **`data_manager/`**: Downloads and caches input data from URLs or local paths
- **`outputs.py`**: Writes final NetCDF with `ch4_sector_*` variables and `ch4_total`
- **`raster.py`**: Reprojects raster data onto the model grid
- **`units.py`**: Unit conversion helpers

### Sector Plugin System (`src/openmethane_prior/sectors/`)

Each of the 13 sectors (agriculture, coal, electricity, fire, industrial, livestock, lulucf, oil_gas, stationary, termite, transport, waste, wetland) is a module that exports a `PriorSector` instance. Sectors are registered as plugins in `sectors/__init__.py`. Each sector implements a `process_emissions()` function that returns a gridded xarray DataArray.

To add a new sector: create a module in `sectors/`, define a `PriorSector`, and register it in `__init__.py`.

### Data Sources (`src/openmethane_prior/data_sources/`)

Six categories of input data (inventory, safeguard, landuse, nightlights, climate_trace, npi), each with URL definitions and download logic. Data is cached in `data/inputs/` (or `INPUT_CACHE` env var).

### Configuration

Copy `.env.example` to `.env`. Key variables:
- `DOMAIN_FILE`: Path or URL to the CF-convention domain NetCDF
- `INVENTORY_DOMAIN_FILE`: Path or URL to inventory domain
- `INPUTS`, `OUTPUTS`, `INTERMEDIATES`: Override default data directories
- `LOG_LEVEL`, `LOG_FILE`: Logging control
- Copernicus ADS credentials required for some data sources (see README)

## Testing

Tests live in `tests/unit/` and `tests/integration/`. Integration tests exercise the full pipeline with real (cached) data. Use `--cache` pytest fixtures to control data caching behaviour.

## Code Style

- Ruff linting and formatting, line length 100
- NumPy-style docstrings
- Python 3.11 only (`>=3.11,<3.12`)
- Apache 2.0 license headers required on all source files (`make update-licenseheaders`)
- Changelog entries managed via `towncrier` (fragments in `changelog/`)