# Changelog

Versions follow [Semantic Versioning](https://semver.org/) (`<major>.<minor>.<patch>`).

Backward incompatible (breaking) changes will only be introduced in major versions
with advance notice in the **Deprecations** section of releases.


<!--
You should *NOT* be adding new changelog entries to this file, this
file is managed by towncrier. See changelog/README.md.

You *may* edit previous changelogs to fix problems like typo corrections or such.
To add a new changelog entry, please see
https://pip.pypa.io/en/latest/development/contributing/#news-entries,
noting that we use the `changelog` directory instead of news, md instead
of rst and use slightly different categories.
-->

<!-- towncrier release notes start -->

## openmethane-prior v1.3.0 (2026-01-27)

### ⚠️ Breaking Changes

- Replace data sources specified in .env with DataSources managed by DataManager

  If input files in .env have been changed from the default values (.env.example),
  these overrides will no longer be read. The URL in the corresponding DataSource
  must be updated to reflect the override, or a new DataSource must be created
  to reflect the custom resource. ([#125](https://github.com/openmethane/openmethane-prior/pull/125))
- Individual layers can no longer be run as standalone scripts

  See the updated README for details on using the omPrior.py --sectors argument
  to run a subset of sectors. ([#135](https://github.com/openmethane/openmethane-prior/pull/135))
- Replace `poetry` with `uv` for dependency and package management. Developers
  will need to [install uv](https://docs.astral.sh/uv/getting-started/installation/)
  and run `uv sync` in the repo after updating.

  If you are just using Docker containers, no change is necessary. ([#155](https://github.com/openmethane/openmethane-prior/pull/155))

### 🆕 Features

- Add Safeguard Mechanism emissions data source ([#139](https://github.com/openmethane/openmethane-prior/pull/139))
- Add Safeguard Mechanism emissions to coal sector ([#144](https://github.com/openmethane/openmethane-prior/pull/144))
- Add INPUT_CACHE for persisting remote data sources locally ([#151](https://github.com/openmethane/openmethane-prior/pull/151))

### 🎉 Improvements

- - Replace `mask_array_by_sequence` with `numpy.isin` ([#124](https://github.com/openmethane/openmethane-prior/pull/124))
- Reorganise internal source code structure into lib, sectors and data_sources folders ([#134](https://github.com/openmethane/openmethane-prior/pull/134))
- Reorganise all sector implementations into separate modules ([#135](https://github.com/openmethane/openmethane-prior/pull/135))
- Update land use data source with the updated 2020-2021 NLUM dataset ([#136](https://github.com/openmethane/openmethane-prior/pull/136))
- Split "fugitive" sector into "coal" and "oil and gas" sectors ([#141](https://github.com/openmethane/openmethane-prior/pull/141))
- Add AustraliaPriorSector which allows specifying ANZSIC codes covered by the sector ([#142](https://github.com/openmethane/openmethane-prior/pull/142))
- Replace successive assertions with a single large assertion in test_009_prior_emissions_ds ([#146](https://github.com/openmethane/openmethane-prior/pull/146))
- Update Climate TRACE dataset used by coal sector ([#147](https://github.com/openmethane/openmethane-prior/pull/147))
- Replace Land Use data with Climate TRACE emissions sources in waste sector ([#148](https://github.com/openmethane/openmethane-prior/pull/148))
- Improve performance and correctness of `regrid_any` and `remap_raster` ([#153](https://github.com/openmethane/openmethane-prior/pull/153))
- Remove reliance on environment variables for configuration in tests ([#156](https://github.com/openmethane/openmethane-prior/pull/156))

### 🐛 Bug Fixes

- Fix prior failing on dates outside the available inventory data ([#131](https://github.com/openmethane/openmethane-prior/pull/131))
- Remove pixel center offsetting in remap_raster which is already handled by rioxarray ([#154](https://github.com/openmethane/openmethane-prior/pull/154))
- Fix empty folders being created in `tests/` when tests are run ([#158](https://github.com/openmethane/openmethane-prior/pull/158))


## openmethane-prior v1.2.0 (2025-09-18)

### 🆕 Features

- Add UNFCCC category classification to prior sector layers ([#121](https://github.com/openmethane/openmethane-prior/pull/121))
- Source inventory data from [National Greenhouse Accounts](https://greenhouseaccounts.climatechange.gov.au/) "Paris Agreement" dataset ([#122](https://github.com/openmethane/openmethane-prior/pull/122))


## openmethane-prior v1.1.0 (2025-08-31)

### ⚠️ Breaking Changes

- Replace INVENTORY_DOMAIN_NAME and INVENTORY_DOMAIN_VERSION env variables with INVENTORY_DOMAIN_FILE for specifying the inventory domain ([#118](https://github.com/openmethane/openmethane-prior/pull/118))
- Replace DOMAIN_NAME and DOMAIN_VERSION env variables with DOMAIN_FILE for specifying the input domain ([#118](https://github.com/openmethane/openmethane-prior/pull/118))

### 🎉 Improvements

- Update tests to use au-test domain instead of full aust10km domain ([#116](https://github.com/openmethane/openmethane-prior/pull/116))


## openmethane-prior v1.0.0 (2025-08-22)

### ⚠️ Breaking Changes

- Output changes:
  - `OCH4_{SECTOR}` output variables have been renamed to `ch4_sector_{name}`
  - `OCH4_{SECTOR}` variables which previously produced a single time-step are
    now expanded to include a time step for each day in the period
  - Output file coordinates have been normalised to ('time', 'vertical', 'y', 'x')
    to follow CF Conventions

  ([#70](https://github.com/openmethane/openmethane-prior/pull/70))
- Default output filename has been changed from `out-om-domain-info.nc` to
  `prior_emissions.nc` ([#75](https://github.com/openmethane/openmethane-prior/pull/75))
- Official Open Methane domains will now follow a simple incremental versioning
  scheme (v1, v2, etc.) rather than semver (v1.0.0) ([#78](https://github.com/openmethane/openmethane-prior/pull/78))
- Major updates to the domain info file will require re-creating existing domain definitions ([#106](https://github.com/openmethane/openmethane-prior/pull/106))

### 🗑️ Deprecations

- Output deprecations:
  - `OCH4_TOTAL` output variable is deprecated in favour of `ch4_total`
  - `LANDMASK` output variable is deprecated in favour of `land_mask`
  - These deprecated outputs will be removed in the next release

  ([#70](https://github.com/openmethane/openmethane-prior/pull/70))

### 🎉 Improvements

- Test coverage has been improved and several low-value, high-cost tests have
  been disabled until they can be improved ([#70](https://github.com/openmethane/openmethane-prior/pull/70))
- Output now follows more CF Conventions including projection details, bounds,
  and standard attributes for all data layers ([#70](https://github.com/openmethane/openmethane-prior/pull/70))
- Improvements to test maintainability and consistency ([#74](https://github.com/openmethane/openmethane-prior/pull/74))
- Add internal Grid utility class to provide common grid and coordinate logic ([#81](https://github.com/openmethane/openmethane-prior/pull/81))
- Add grid "slug" or short name to output file ([#82](https://github.com/openmethane/openmethane-prior/pull/82))
- Add "cell_name" to output file with a short unique name for each grid cell ([#83](https://github.com/openmethane/openmethane-prior/pull/83))
- Start date and end date can now be specified via START_DATE and END_DATE environment variables ([#84](https://github.com/openmethane/openmethane-prior/pull/84))
- Output will only be written to disk at the end of processing ([#85](https://github.com/openmethane/openmethane-prior/pull/85))
- Fix Grid performance by removing `@property` usage ([#86](https://github.com/openmethane/openmethane-prior/pull/86))
- Add `Grid.lonlat_to_cell_index` method which works efficiently on lists ([#86](https://github.com/openmethane/openmethane-prior/pull/86))
- Adopt standard reprojection approach using Grid class throughout the project ([#87](https://github.com/openmethane/openmethane-prior/pull/87))
- Apply land mask to emissions sources that should only occur on land ([#88](https://github.com/openmethane/openmethane-prior/pull/88))
- Replace print statements with configurable logger ([#100](https://github.com/openmethane/openmethane-prior/pull/100))
- add inventory mask ([#103](https://github.com/openmethane/openmethane-prior/pull/103))
- use inventory mask on relevant sectors ([#105](https://github.com/openmethane/openmethane-prior/pull/105))
- Remove XORIG and YORIG from domain format, use x_bounds and y_bounds instead ([#112](https://github.com/openmethane/openmethane-prior/pull/112))
- Add create_subset_domain script to make it easier to create a domain inside aust10km ([#113](https://github.com/openmethane/openmethane-prior/pull/113))
- Allow prior domains that dont share projection with the inventory ([#115](https://github.com/openmethane/openmethane-prior/pull/115))

### 🐛 Bug Fixes

- Fix reprojection in agriculture, LULUCF and waste layers ([#90](https://github.com/openmethane/openmethane-prior/pull/90))
- Add `grid_mapping` attribute to `land_mask` output variable ([#92](https://github.com/openmethane/openmethane-prior/pull/92))
- Disable _FillValue in output meta variables like coords and bounds ([#92](https://github.com/openmethane/openmethane-prior/pull/92))
- Remove intermediates generated with reproject_tiff which are no longer used ([#99](https://github.com/openmethane/openmethane-prior/pull/99))
- Added the grid projection offsets in XORIG/YORIG to the Grid projection ([#106](https://github.com/openmethane/openmethane-prior/pull/106))
- fixing national inventory normalisation ([#114](https://github.com/openmethane/openmethane-prior/pull/114))


## openmethane-prior v0.3.0 (2025-01-12)

### 🎉 Improvements

- Make OPENMETHANE_PRIOR_VERSION environment variable available inside the container ([#60](https://github.com/openmethane/openmethane-prior/pull/60))

### 🐛 Bug Fixes

- Fix actions incorrectly populating container image version ([#61](https://github.com/openmethane/openmethane-prior/pull/61))

### 🔧 Trivial/Internal Changes

- [#53](https://github.com/openmethane/openmethane-prior/pull/53)


## openmethane-prior v0.2.0 (2024-11-21)

### 🎉 Improvements

- Adopt common release process from openmethane/openmethane

  Adopt common docker build workflow from openmethane/openmethane ([#57](https://github.com/openmethane/openmethane-prior/pull/57))
