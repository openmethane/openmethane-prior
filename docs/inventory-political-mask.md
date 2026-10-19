# Inventory political mask

The `inventory_political_mask` domain variable marks the grid cells inside the
Australian jurisdiction that Australia's national greenhouse gas inventory
reports on. It is a binary mask: `1` inside, `0` outside.

It exists alongside `inventory_mask`, which despite its name is an inventory
*land* mask. `inventory_mask` was made from the National Land Use Map, so it
leaves out coastal cells and every offshore area, including the offshore oil
and gas fields whose emissions are part of the national inventory. See
[issue #225](https://github.com/openmethane/openmethane-prior/issues/225).

The prior does not use `inventory_political_mask` to allocate emissions. It is
published for downstream users who need to know which cells count as
"Australia", such as excluding Papua New Guinea from national totals.

## How the jurisdiction is built

The jurisdiction is the union of:

| Part | Source |
|---|---|
| Land | ABS ASGS Edition 3 State and Territory boundaries 2021 (`AU-states`) |
| Internal waters | Filled from the AMB2020 territorial sea (see below) |
| Territorial sea (12 nautical miles) | AMB2020, Seas and Submerged Lands Act 1973, `Territorial_Sea_AMB2020_Areas` |
| Offshore petroleum areas | AMB2020, Offshore Petroleum and Greenhouse Gas Storage Act 2006, `Offshore_Areas_AMB2020_Areas` |

[Australian Maritime Boundaries 2020 (AMB2020)](https://pid.geoscience.gov.au/dataset/ga/144571)
is published by Geoscience Australia under CC BY 4.0.

### Internal waters

AMB2020 territorial sea polygons run seaward from the territorial sea
baseline. Land and internal waters, such as Port Phillip Bay, Spencer Gulf and
waters inside straight baselines, are holes in those polygons and appear in no
other AMB2020 area layer. ABS state boundaries follow the coastline, so they
don't cover internal waters either.

Each territorial sea polygon is replaced by its outer ring, filling the hole
with everything landward of the 12 nautical mile limit. Without this step,
cells entirely within bays and gulfs would fall outside the mask.

### Why offshore petroleum areas instead of the EEZ

Oil and gas are seabed resources. Australia's rights over them come from the
continental shelf, and Commonwealth petroleum titles are granted in the
offshore areas defined by the Offshore Petroleum and Greenhouse Gas Storage Act.
In the Timor Sea those areas follow seabed treaty boundaries, which lie further
north than the proclaimed Exclusive Economic Zone (EEZ).

A boundary built from the EEZ leaves out the Laminaria-Corallina fields
(production licence AC/L5, Northern Endeavour FPSO). They sit 90–100 km north of
the EEZ, in Commonwealth waters of the Ashmore and Cartier Islands offshore area,
and are regulated by NOPSEMA.

Adding the EEZ on top of the offshore petroleum areas adds 331 aust10km cells
in the Timor and Arafura Seas and the Torres Strait. These are water-column-only
areas with no oil and gas sources, so the EEZ is not included.

### External territories

The 2021 National Inventory Report includes Norfolk Island, Christmas Island
and the Cocos (Keeling) Islands. Christmas Island and Cocos are outside the
aust10km domain. Antarctic and sub-Antarctic territories are outside the
domain.

## From shape to grid cells

A cell is inside (`1`) when **any part** of its area falls inside the
jurisdiction. Cells which only touch the jurisdiction along an edge or at a
corner are outside.

### Why any overlap, not a majority of the cell

A "more than half" rule looks like the obvious choice, and it is what
`inventory_mask` uses. We chose any overlap for practical reasons:

- **Offshore sources are points, not fields.** The prior places each offshore
  well or facility at a single location, so all of its emissions land in one
  cell. Many of these sources are large. A majority rule can leave out a cell
  that contains an Australian facility because most of the cell lies on the
  other side of a boundary. That facility's whole emission would then drop out
  of "Australia", which is a large error for any analysis.
  The Laminaria-Corallina fields (AC/L5) show this happens: only 14.7% of
  their cell is Australian, so a majority rule leaves them out.
- **Any overlap rules this out by construction.** A source inside the
  jurisdiction is always in a cell that overlaps the jurisdiction.
- **The extra cells hold almost no anthropogenic emissions.** On aust10km,
  any overlap adds 846 cells to the 139,217 a majority rule would select.
  [EDGAR 2025](https://edgar.jrc.ec.europa.eu/dataset_ghg2025) 2024 CH4
  places about 0.06 kt/yr of anthropogenic emissions in the non-Australian
  parts of those cells, against about 5,067 kt/yr inside the jurisdiction
  (about 0.001%). Most of this is residential combustion in Papua New Guinea
  villages next to Saibai and Boigu, and small amounts at sea. No foreign oil
  and gas, landfill or agriculture source is picked up.
- **Natural emissions are less important here.** Border cells also count the
  natural emissions in their non-Australian parts as Australian. That error is
  a small fraction of natural emissions, which are not what the inventory
  reports and are largely outside Australia's control.

Effects at specific places:
- Cells containing small Australian islands in the northern Torres Strait
  (Saibai, Boigu) are inside, along with the Papua New Guinea coastline those
  cells also contain.
- Cells with no Australian area, such as Daru (Papua New Guinea) and Dili
  (Timor-Leste), are outside.

## Oil and gas coverage check

Every oil and gas emission source (wells, facilities, pipelines) was tested
against the jurisdiction and the mask. Sources active at any time from 2000
to 2026 were included, and 2023–24 Safeguard facility links were recorded.

| Source | Inside jurisdiction | Cell in mask | Notes |
|---|---|---|---|
| All onshore, coastal and other offshore sources | Yes | Yes | — |
| Laminaria 1–8 wells and two NPI records (AC/L5) | Yes | Yes | Australian under the 2018 Australia–Timor-Leste treaty, which only allows the nearby boundary to be adjusted once these fields are depleted. 14.7% of their cell is Australian. |
| Buffalo Venture FPSO (NPI 540278) | No, 2 km outside | Yes | Buffalo field is on the Timor-Leste side of the 2018 treaty boundary. Its cell is 53% Australian. |
| Sunrise-3 well (NPI 558264, reported 2008/09 only) | No | No | In the Greater Sunrise special regime under the 2018 treaty. |
| Bayu-Undan to Darwin pipeline | 93% of its length | Mostly | The offshore end lies in Timor-Leste waters. The prior spreads pipeline emissions along the whole line, so about 5% of this pipeline's share lands in cells outside the mask. |

`tests/integration/test_inventory_political_mask.py` repeats this check for
the 2023–24 Safeguard year. It fails if any well or facility falls outside
the mask, or if any pipeline other than Bayu-Undan to Darwin places length
outside it.

## Regenerating

```bash
uv run python scripts/add_inventory_political_mask.py \
  --domain domain.aust10km.nc --output out/domain.aust10km.nc
```

`--domain` accepts a path or URL and overrides `DOMAIN_FILE`. Without it the
script uses `DOMAIN_FILE`, and paths like `INPUTS` come from the environment or
`.env`, as they do for `omPrior.py`.

The script fetches the AMB2020 and ABS inputs through the DataManager and takes
about a minute for aust10km, most of it building the jurisdiction shape.
