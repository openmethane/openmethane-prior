# Multi-year Safeguard Mechanism data

Issue: [#173 Integrate FY 24/25 Safeguard Mechanism data](https://github.com/openmethane/openmethane-prior/issues/173)
Branch: `173/safeguard-multi-year`
Started: 2026-11-04

This plan is a working document. Update it as decisions change during
development, and delete it as the last commit before merging the PR so it
remains in git history.

## Goal

Use the Safeguard Mechanism (SGM) Baselines and Emissions Table for the
financial year (FY) that matches the prior run period. Start with FY 2023-24
(current) and FY 2024-25 (published 2026-04-15), and make adding later years,
possibly with different file structures, a matter of adding one entry. Using
the nearest year when the run's FY has no table is a follow-up.

## Findings so far

- **FY 2024-25 has the same structure as FY 2023-24.** Both are cp1252-encoded
  CSVs with identical header rows, so the current parser reads both. Tables
  before FY 2023-24 have no methane column and can't be used.
- **GWP is still AR5 (CH4 = 28) for FY 2024-25.** No sign of NGER adopting AR6
  ([CER GWP page](https://cer.gov.au/schemes/national-greenhouse-and-energy-reporting-scheme/about-emissions-and-energy-data/global-warming-potential)).
  GWP will still be stored per year so a future change is a data edit.
- **Runs after 2024-06-30 currently get no SGM facilities, with no warning.**
  `filter_facilities` keeps only facilities whose reporting year fully
  contains the run period. Coal, oil & gas and waste then fall back to
  distributing their whole inventory total. Production daily runs are in
  FY 2025-26 now, so this is the current production behaviour.
- **Multi-year monitoring period (MYMP) rows have methane values** (Curragh,
  Russell Vale, etc.). No special handling needed.
- **Facility names change between years.** Coal, oil & gas and waste
  differences between FY 2023-24 and FY 2024-25:
  - Likely renames: Blackwater Mine → Blackwater Coal Mine,
    Daunia Mine → Daunia Coal Mine, Kestrel Coal Pty Ltd → Kestrel Mine,
    Collinsville Mine → Collinsvile Mine (CER typo),
    `1. Solid Waste Services - MRL` → `2. Solid Waste Services - MRL`
  - New in FY 2024-25: Blair Athol Operations, Newlands Coal Complex including
    Newlands Northern UG, Vales Point Power Station (ANZSIC coal mining),
    Macedon (oil & gas), Woodlawn Bioreactor
  - Gone in FY 2024-25: Chain Valley Colliery, Ironbark No. 1, Kogan Creek Mine,
    Norwich Park Mine, Sojitz Gregory Crinum Mine,
    `1. Solid Waste Services - Lucas Heights`
  - Arrow Surat Operations only differs by a non-breaking space in FY 2023-24.
    The existing NFKC normalisation already handles it.
- **Existing bugs found along the way:**
  - `parse_csv_text` computes a stripped value but returns the unstripped one.
  - `safeguard_mechanism_csv_columns` assigns names by position and mislabels
    5 columns (`units_relinquished`, `net_emissions`, `net_position`,
    `smcs_issued`, `smcs_surrendered` are out of order). They're unused, so
    there's no current effect.
- **Coal scales SGM emissions differently from oil & gas and waste.** It calls
  `filter_facilities` directly and scales with `days / 365`, which is wrong for
  FY 2023-24 (366 days) and skips operating dates.
- **Unlocated facilities already stay in the sector total in every sector.**
  Their emissions are never subtracted as "allocated", so they fall into the
  remainder that's spread over other sources. Only the warning differs.
  - Oil & gas: logs `No sources found for facility ...`. A QLD facility's
    emissions go into the QLD remainder (QLD sources). A non-QLD facility's
    go into the national remainder (non-QLD sources).
  - Waste: logs the same warning. Emissions go into the national remainder.
  - Coal: no warning. `get_safeguard_facility_locations` drops the facility,
    and its emissions go into the remainder spread over the other Climate
    TRACE coal mines.
- **Pyrenees split into Pyrenees and Macedon in FY 2024-25.** Grattan doesn't
  list this one. APU01 Pyrenees reported 10,584 t CO2e CH4 in FY 2023-24 with
  no Macedon row. In FY 2024-25 Pyrenees reported 5,931 t and Macedon
  6,621 t. Both share production licence WA-42-L (NEATS field name
  "Pyrenees (Macedon)"), which holds the Macedon gas wells (Macedon 6–10)
  and most Pyrenees oil wells. WA-43-L is Pyrenees only.
- **Most offshore title location rows match no wells**
  ([#236](https://github.com/openmethane/openmethane-prior/issues/236)).
  Commonwealth titles (`WA-nn-L`, `AC/Ln`, `NT/L1`) are recorded against
  `WA-petroleum-wells` / `NT-petroleum-wells`. Their wells only exist in
  `NOPTA-wells`. 12 facilities (about 40 kt CH4 in FY 2023-24) are placed on
  their site alone, with no warning. This is a sheet fix, separate from this
  issue.
- **Facilities can report emissions in years they weren't operating**
  ([#237](https://github.com/openmethane/openmethane-prior/issues/237)).
  Darwin LNG stopped producing on 2023-11-11 and restarted on Barossa gas in
  December 2025 (first cargo January 2026). It still reported 191 t CH4 for
  FY 2024-25. With no active site it matches nothing, and the 191 t goes to
  the national remainder. #237 proposes data rows for non-operating periods,
  a fallback to non-operating locations, or both. Not part of PR 2.
- **Operating dates only exist for oil & gas, and only through locations.**
  `safeguard_operating_periods` builds a facility's operating period from its
  oil & gas sites (earliest start, latest end). Within the matching year,
  `get_sector_safeguard_facilities` divides the reported figure by operating
  days in the reporting year. Coal and waste have no operating dates.

## Decisions

1. **One dynamic DataSource that fetches only the FY needed.** Chosen over a
   combined multi-year DataFrame because the change to the codebase is smaller.
   - A registry maps each FY to its URL, file name, reader function and GWP.
   - `file_path` is a function of the run's FY and includes the year, so cached
     files are reused and years never overwrite each other.
   - `fetch` looks up the URL in the registry, since `DataSource.url` is
     static.
   - The source stays non-`dynamic` (stored in the static path). The file name
     changes with the year, so the cache is still correct.
2. **A run that spans two FYs raises an error.** The inventory already
   enforces the same constraint.
3. **A run in an FY with no table gets no SGM data, with a loud warning.**
   This is the current behaviour, but now visible. It must not raise, because
   production daily runs are in FY 2025-26. Using the nearest year is a
   follow-up PR.
4. **Reported figures are used as published.** There's no reliable way to
   scale an SGM figure from a partial operating year, since operating dates
   exist only for locations, not facilities.
   - The existing within-year scaling for oil & gas (derived from site dates)
     is unchanged in PR 2.
   - For the nearest-year follow-up: a borrowed figure counts as a full year.
     The days of emission in the run period come from the location operating
     dates, where they exist.
5. **No aliases: locations are recorded against each published name, and
   rows can be limited to a range of financial years** (decided 2026-11-05,
   replacing a "Facility aliases" tab that was built and then removed).
   - [Grattan's Safeguard submission](https://grattan.edu.au/wp-content/uploads/2026/09/Grattan-Institute-Safeguard-submission-Sept-26-.pdf)
     (Appendix A.1.1, p. 39) matched FY 2023-24 to FY 2024-25 with name
     normalisation plus 13 hand-checked pairs, and found matches aren't
     one-to-one. In our data:
     - Renames: Chain Valley Colliery → Vales Point Power Station, Wodgina
       Operations → Wodgina Lithium Project, Gudai-Darri → Koodaideri.
     - Owner handovers: Blackwater and Daunia were each listed twice in
       FY 2023-24 (BMA and Whitehaven rows, already summed by name) and once
       under a new name in FY 2024-25. For us these are just renames.
     - Split: Fisherman's Landing → "- Clinker & Cement" and "- Lime".
       Not in Grattan: APU01 Pyrenees → Pyrenees and Macedon (see findings).
       Macedon gets its own rows. Both facilities share the WA-42-L wells,
       accepted as imprecise but not harmful: wells already get an even
       share, and the shared wells fall in the same few grid cells.
     - Absorbed: Ironbark No. 1 → Carborough Downs Coal Mine, which keeps its
       name in both years.
   - Aliases (one published name → one canonical name) can't give the parts
     of a split their own locations, and can't express an absorption into a
     facility that keeps its name. Plain name-keyed locations handle renames
     and splits. Optional "First financial year" / "Last financial year"
     columns handle absorption: Carborough Downs gets Ironbark's mine from
     FY 2024-25 only.
   - The prior never compares years, so cross-year identity isn't needed
     here. A Grattan-style lineage tab (old → new, type, evidence) could
     serve openmethane-web later, without affecting how emissions are placed.
   - No fuzzy matching.
6. **Unlocated facilities keep their emissions in the sector total.** This is
   better for an inversion than leaving them out: the sector total stays right
   at the cost of slightly higher emissions on other sources. All sectors
   already do this (see findings), so the only change is adding the warning
   to coal.
7. **`safeguard-locations` stays static.** Production runs will start from an
   empty inputs folder so the updated location rows are fetched.

## Work plan

### PR 1 (lead-up): align coal SGM handling with oil & gas and waste

[#235](https://github.com/openmethane/openmethane-prior/pull/235), branch
`173/coal-safeguard-alignment`, opened 2026-11-05.

- [x] Route coal through `get_sector_safeguard_facilities` so period scaling
      uses real FY lengths. Remove the separate `days / 365`.
- [x] Log a warning for each coal SGM facility with no location in the coal
      facilities data, including its CH4, matching oil & gas and waste.
      Also treats a location pointing at a mine missing from Climate TRACE
      as unlocated (previously those emissions were lost).
- [x] Update coal unit and integration tests.
- [x] Changelog fragment.
- Output vs `main` (au-test, FY 2023-24): Safeguard cells −0.2732%
  (365/366 − 1), remainder cells +1.60%, domain total −0.17%.

### PR 2 (this issue): per-year Safeguard data for FY 2023-24 and FY 2024-25

Stacked on #238, which is stacked on PR 1 (#235), so this branch includes
both (rebased 2026-11-06). Once #235 and #238 merge, rebase onto `main`.

Data source:
- [x] Add a per-year registry: FY → `{url, file_name, reader, ch4_gwp, co2_gwp}`.
      (`SafeguardBaselinesAndEmissionsTable` and `safeguard_tables` in
      `data_sources/safeguard/data.py`). GWPs are set explicitly for each
      year, with no defaults.
- [x] Default CSV reader selects columns **by header name**. This fixes the
      positional mislabelling.
- [x] Fix `parse_csv_text` to return the stripped, normalised value. FY 2023-24
      output is identical to `main` (231 facilities, all columns).
- [x] Make `file_path` and `fetch` choose the year from `prior_config`. Raise
      when the run spans two FYs, and warn (no SGM data) when the FY isn't in
      the registry. For an unregistered FY, `fetch` does nothing and `parse`
      warns and returns an empty DataFrame with the facility columns
      (`safeguard_facility_columns`).
- [x] Add FY 2024-25 to the registry. 227 facilities (228 rows, Telfer
      listed twice).

Year-limited locations:
- [x] `parse_location_csv` reads columns by header name and keeps only rows
      valid in the run's FY (`filter_locations_for_financial_year` in
      `data_sources/safeguard/location.py`). Missing year columns are treated
      as blank, so cached CSVs without them still work.
- [x] A `FinancialYear` value type (identified by start year, with
      `from_date`, `from_period`, `from_label`, `label`, `start` and inclusive
      `end`) in `data_sources/financial_year.py`. Safeguard tables, location
      filtering and `create_facilities_from_safeguard_rows` take it instead of
      bare years or a `(start, end)` tuple. It lives in `data_sources/`, not
      `lib/`, because it's Australian: it moves to `australia/` with #220.
      Moving inventory and NPI to it is a separate follow-up,
      [#239](https://github.com/openmethane/openmethane-prior/issues/239). The unused
      `SafeguardFacility` and `SafeguardFacilityRecord` classes were removed.
- [x] Raise when a header looks like a year column but doesn't match exactly
      (`check_location_year_columns`). Header whitespace is stripped first.
      Reading is in `read_location_csv`, which can be tested without files.
- [x] Add "First financial year" and "Last financial year" columns to the
      "External facility locations" tab (done 2026-11-05). Petroleum titles
      doesn't need them.
- Adding the columns broke fetching on `main`: Google's CSV export guessed
  a many-row header, and `main`'s parser read columns by position.
  [#238](https://github.com/openmethane/openmethane-prior/pull/238) fixes
  both (`headers=1`, required columns checked at fetch, columns read by
  name). Until #238 is released, a run that fetches locations into an
  empty inputs folder fails in oil & gas. This branch is stacked on #238
  (rebased 2026-11-06): it keeps #238's fetch and this branch's year
  filtering, and `read_location_csv` takes
  `financial_year: FinancialYear | None`. The live-sheet tests here only
  pass with `headers=1`.
- [ ] Delete the cached `safeguard-facility-locations.csv` (in
      `data/.cache/inputs` for tests, and static inputs in production) so the
      new rows are fetched. Local test cache deleted and re-fetched with
      `headers=1` on 2026-11-06; production still to do.
- Note: the Google Sheets CSV endpoint returns the **first tab** when the
  requested tab doesn't exist (verified). See open questions.

Sheet data (manual, needs human review):
- [x] Review and add the 12 proposed rows for the 10 FY 2024-25 facilities
      with no location (7 coal, 1 oil & gas, 2 waste), plus Carborough Downs
      → Ironbark from 2024-25. Proposed in
      `scratches/claude/safeguard-multi-year/proposed-location-rows-2024-25.csv`
      (year columns before Notes, matching the tab). Added 2026-11-05;
      the CONFIRM rows were accepted. Macedon has two rows: NPI 605872 (onshore gas
      plant) and `NOPTA-wells` / `WA-42-L`. FY 2023-24 has no unlocated
      facilities apart from Norwich Park's deliberately blank row.
- [ ] (After the sandbox daily runs, with the #236 sheet fix, since this tab
      changes FY 2025-26 output.) Add a second Darwin LNG Terminal row to the "Oil and gas sites" tab
      for the Barossa restart (`Operation start` 2025-12-01, no end, INPEX
      and Argus references). The existing row keeps its 2023-11-11 end.
      Doesn't affect FY 2023-24 or FY 2024-25. It matters once FY 2025-26
      is published.

Checks and tests:
- [x] Unit tests with constructed data:
  - year selection (each registered FY, unregistered FY warns and returns no
    data, run spanning two FYs raises)
  - reader column selection by header
  - location rows limited by financial year
- [x] Integration test parsing each registered year's real file. FY 2024-25
      is cached on first fetch by the `input_files` fixture.
- [x] Update existing integration tests that assume FY 2023-24 only. The
      default test dates (2022-12-07) are in FY 2022-23, which has no table,
      so tests reading the Safeguard asset now set FY 2023-24 dates
      (`test_safeguard_data_source`, coal, `test_gas_supply`).
- [x] Update `docs/data-sources.md`.
- [x] Integration test that every coal, oil & gas (not gas supply) and waste
      facility in each registered year has a location row, so a new year's
      table can't be added without its locations. A row with a blank id
      (Norwich Park) counts as deliberately unlocated. Fetches the live
      sheet (`test_safeguard_location_coverage.py`); passes for both years
      with `headers=1`. #236 proposes a
      stricter test (every location row matches a source). That belongs with
      the #236 sheet fix, not this PR.
- [ ] Changelog fragments once the PR has a number: `feature` (per-year
      Safeguard data, year-limited locations) and `fix` (`parse_csv_text`
      stripping, Safeguard table columns read by header name).

### Extend `sector-provenance-attributes` (in parallel, not after)

This work strengthens the case for that branch, so update it rather than
waiting for it to merge.
- [ ] Per-sector output attributes recording the SGM data year used (and
      later, whether it was borrowed) and the total SGM emissions allocated in
      the sector.
- [ ] Record the ANZSIC codes treated as in the sector.

### Follow-up: use the nearest year when the run's FY has no table

- [ ] Later than the latest table → latest table. Earlier than FY 2023-24 →
      FY 2023-24. Warn when borrowing.
- [ ] Replace the strict period-containment filter in `filter_facilities` so a
      borrowed year's rows are kept.
- [ ] Scaling per decision 4: a borrowed figure counts as a full year, and the
      days of emission in the run period come only from location operating
      dates.
- [ ] Tests for borrowed-year scaling with opening-only, closing-only and both
      dates.

## Decided open questions (2026-11-05)

- **Misnamed year column headers** raise an error (see year-limited
  locations).
- **Renamed or broken sheet tabs** raise at fetch time via required columns
  ([#238](https://github.com/openmethane/openmethane-prior/pull/238)).
- **Location coverage test** fetches the live sheet, accepting that a sheet
  edit can fail it.
- **Operating dates for coal and waste** stay deferred to the nearest-year
  follow-up. Before then, check whether Kogan Creek, Norwich Park and
  Sojitz Gregory Crinum (missing from FY 2024-25 with no successor) are
  closures.
- **Facility lineage** (old → new name, type of change, evidence) belongs to
  openmethane-web if it ever compares years; an issue is drafted in
  `scratches/claude/safeguard-multi-year/issue-web-facility-lineage.md`.
- **Darwin LNG restart row** waits for the sandbox daily runs (see sheet
  data).
