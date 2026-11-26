# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

`openmethane-prior` calculates gridded prior emissions estimates for methane across Australia. It reads a domain NetCDF file, downloads/caches input data from multiple sources, and produces a NetCDF output with per-sector and total methane emissions on the domain grid.

## Common Commands

```bash
uv sync                  # Install dependencies
uv add <package>         # Add a new dependency (do not edit pyproject.toml manually)
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
- `INPUTS`, `OUTPUTS`, `INTERMEDIATES`: Override default data directories
- `LOG_LEVEL`, `LOG_FILE`: Logging control
- Copernicus ADS credentials required for some data sources (see README)

## Testing

Tests live in `tests/unit/` and `tests/integration/`. Tests follow pytest
conventions and use pytest libraries.

Integration tests exercise the full pipeline with real (cached) data. Use
`input_files` pytest fixture to use cached data. For integration tests which
should download DataSource assets from the internet, `input_files` should be
omitted.

Mark tests which take several minutes with `@pytest.mark.long_running`. CI
deselects them to stay within its timeout; run them locally with
`uv run python -m pytest -m long_running`.

Unit tests should avoid calling methods which read from the filesystem, and
should construct example data to pass to methods.

Every test should call the unit under test directly in the test body, so it's
clear what the test exercises. Fixtures and helpers may set up test conditions
(grids, DataFrames, config), but must not wrap the call to the unit under test.
Prefer repeating a few lines of arguments over hiding the call in a helper.

## Before opening a pull request

For any change that isn't mechanical (see "Code review" in
`docs/development.md`), review it from a fresh context before opening the pull
request, and again after reworking it substantially. Skip this for formatter
runs, dependency bumps and experiments not for merge, or if the operator asks
you to.

Launch the `reviewer` subagent (`.claude/agents/reviewer.md`). Give it:

- the goal of the change and the diff range (e.g. `main...HEAD`)
- the numbers of any issues the change addresses
- any constraints the operator set during the task, such as an approach to use
  or avoid, or something to leave unchanged

Don't give it your reasoning or your view of whether the change is correct,
because it will tend to confirm what it's told.

Independent reviews of the same change find different problems. When a change
both alters the prior's emissions or what production runs do, and touches
error handling, input downloads and readers (including Google Sheets), or
several modules, offer the operator a second review, run in parallel with the
same brief. Each review costs tens of thousands of tokens, so run the second
only if the operator agrees. Merge the two reports, counting a finding both
raised once, before dealing with them.

Deal with each item it reports:

- **Wrong, with a clear fix:** fix it, if the fix stays within the scope of the
  task and doesn't go against the operator's instructions or the project's
  guidance.
- **Needs the operator's decision:** ask the operator, with the options and
  your recommendation. This includes items with an obvious fix that would
  change the prior's emissions or methodology, widen the change beyond what
  was asked, or make the pull request need human review when it otherwise
  wouldn't.
- **Not a problem:** dismiss it, but list it in one line to the operator with
  your reason, because you're judging criticism of your own work.

This review is part of preparing the change. Don't mention it or its findings
in the pull request description or comments.

## Code Style

- Ruff linting and formatting, line length 100
- NumPy-style docstrings
- Python 3.12 only (`>=3.12,<3.13`)
- Apache 2.0 license headers required on all source files (`make update-licenseheaders`)
- Changelog entries managed via `towncrier` (fragments in `changelog/`)