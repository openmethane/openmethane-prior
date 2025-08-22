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

## openmethane-prior v1.0.0 (2025-08-22)

### ⚠️ Breaking Changes

- Output changes:
  - `OCH4_{SECTOR}` output variables have been renamed to `ch4_sector_{name}`
  - `OCH4_{SECTOR}` variables which previously produced a single time-step are
    now expanded to include a time step for each day in the period
  - Output file coordinates have been normalised to ('time', 'vertical', 'y', 'x')
    to follow CF Conventions

  ([#70](https://github.com/openmethane/openmethane-prior/pulls/70))
- Default output filename has been changed from `out-om-domain-info.nc` to
  `prior_emissions.nc` ([#75](https://github.com/openmethane/openmethane-prior/pulls/75))
- Official Open Methane domains will now follow a simple incremental versioning
  scheme (v1, v2, etc.) rather than semver (v1.0.0) ([#78](https://github.com/openmethane/openmethane-prior/pulls/78))
- Major updates to the domain info file will require re-creating existing domain definitions ([#106](https://github.com/openmethane/openmethane-prior/pulls/106))

### 🗑️ Deprecations

- Output deprecations:
  - `OCH4_TOTAL` output variable is deprecated in favour of `ch4_total`
  - `LANDMASK` output variable is deprecated in favour of `land_mask`
  - These deprecated outputs will be removed in the next release

  ([#70](https://github.com/openmethane/openmethane-prior/pulls/70))

### 🎉 Improvements

- Test coverage has been improved and several low-value, high-cost tests have
  been disabled until they can be improved ([#70](https://github.com/openmethane/openmethane-prior/pulls/70))
- Output now follows more CF Conventions including projection details, bounds,
  and standard attributes for all data layers ([#70](https://github.com/openmethane/openmethane-prior/pulls/70))
- Improvements to test maintainability and consistency ([#74](https://github.com/openmethane/openmethane-prior/pulls/74))
- Add internal Grid utility class to provide common grid and coordinate logic ([#81](https://github.com/openmethane/openmethane-prior/pulls/81))
- Add grid "slug" or short name to output file ([#82](https://github.com/openmethane/openmethane-prior/pulls/82))
- Add "cell_name" to output file with a short unique name for each grid cell ([#83](https://github.com/openmethane/openmethane-prior/pulls/83))
- Fix Grid performance by removing `@property` usage ([#86](https://github.com/openmethane/openmethane-prior/pulls/86))
- Add `Grid.lonlat_to_cell_index` method which works efficiently on lists ([#86](https://github.com/openmethane/openmethane-prior/pulls/86))
- Adopt standard reprojection approach using Grid class throughout the project ([#87](https://github.com/openmethane/openmethane-prior/pulls/87))
- Replace print statements with configurable logger ([#100](https://github.com/openmethane/openmethane-prior/pulls/100))
- add inventory mask ([#103](https://github.com/openmethane/openmethane-prior/pulls/103))
- use inventory mask on relevant sectors ([#105](https://github.com/openmethane/openmethane-prior/pulls/105))
- Remove XORIG and YORIG from domain format, use x_bounds and y_bounds instead ([#112](https://github.com/openmethane/openmethane-prior/pulls/112))
- Add create_subset_domain script to make it easier to create a domain inside aust10km ([#113](https://github.com/openmethane/openmethane-prior/pulls/113))
- Allow prior domains that dont share projection with the inventory ([#115](https://github.com/openmethane/openmethane-prior/pulls/115))

### 🐛 Bug Fixes

- Fix reprojection in agriculture, LULUCF and waste layers ([#90](https://github.com/openmethane/openmethane-prior/pulls/90))
- Add `grid_mapping` attribute to `land_mask` output variable ([#92](https://github.com/openmethane/openmethane-prior/pulls/92))
- Disable _FillValue in output meta variables like coords and bounds ([#92](https://github.com/openmethane/openmethane-prior/pulls/92))
- Added the grid projection offsets in XORIG/YORIG to the Grid projection ([#106](https://github.com/openmethane/openmethane-prior/pulls/106))
- fixing national inventory normalisation ([#114](https://github.com/openmethane/openmethane-prior/pulls/114))


## openmethane-prior v0.3.0 (2025-01-12)

### 🎉 Improvements

- Make OPENMETHANE_PRIOR_VERSION environment variable available inside the container ([#60](https://github.com/openmethane/openmethane-prior/pulls/60))

### 🐛 Bug Fixes

- Fix actions incorrectly populating container image version ([#61](https://github.com/openmethane/openmethane-prior/pulls/61))

### 🔧 Trivial/Internal Changes

- [#53](https://github.com/openmethane/openmethane-prior/pulls/53)


## openmethane-prior v0.2.0 (2024-11-21)

### 🎉 Improvements

- Adopt common release process from openmethane/openmethane

  Adopt common docker build workflow from openmethane/openmethane ([#57](https://github.com/openmethane/openmethane-prior/pulls/57))
