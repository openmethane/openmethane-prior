import datetime

import attrs
import pytest

from openmethane_prior.data_sources.au_shapes import (
    amb2020_offshore_areas_data_source,
    amb2020_territorial_sea_data_source,
    au_shapes_states_data_source,
    create_inventory_political_mask,
)
from openmethane_prior.lib import DataManager
from openmethane_prior.lib.grid.geometry import grid_weights_from_linestring
from openmethane_prior.sectors import all_sectors
from openmethane_prior.sectors.oil_gas.emission_sources.all_sources import all_emission_sources

# Pipelines which run partly outside Australian jurisdiction, and the most of
# their length expected in cells outside the mask. See
# docs/inventory-political-mask.md.
PIPELINES_LEAVING_JURISDICTION = {
    # offshore end lies in Timor-Leste waters since the 2018 boundary treaty,
    # about 4.9% of its length is in cells outside the mask
    "Bayu/Undan to Darwin": 0.05,
}


@pytest.fixture()
def safeguard_year_config(aust10km_config):
    # the 2023-24 Safeguard reporting year, when facility locations are linked
    return attrs.evolve(
        aust10km_config,
        start_date=datetime.datetime(2023, 7, 1),
        end_date=datetime.datetime(2024, 6, 30),
    )


@pytest.fixture()
def jurisdiction_data_manager(safeguard_year_config):
    yield DataManager(
        prior_config=safeguard_year_config,
        data_path=safeguard_year_config.input_path,
    )

    # keep fetched AMB2020 inputs in the shared cache for later runs
    safeguard_year_config.cache_inputs()


def test_oil_gas_sources_inside_mask(safeguard_year_config, jurisdiction_data_manager):
    grid = safeguard_year_config.domain().grid
    oil_gas = next(s for s in all_sectors if s.name == "oil_gas")
    sources_df = all_emission_sources(
        data_manager=jurisdiction_data_manager,
        prior_config=safeguard_year_config,
        anzsic_codes=oil_gas.anzsic_codes,
    )
    is_pipeline = sources_df.geom_type.isin(["LineString", "MultiLineString"])
    sites_df = sources_df[~is_pipeline]
    pipelines_df = sources_df[is_pipeline]

    mask = create_inventory_political_mask(
        grid=grid,
        states=jurisdiction_data_manager.get_asset(au_shapes_states_data_source).data,
        territorial_sea=jurisdiction_data_manager.get_asset(amb2020_territorial_sea_data_source).data,
        offshore_areas=jurisdiction_data_manager.get_asset(amb2020_offshore_areas_data_source).data,
    )

    # every well and facility is in a cell inside the mask
    site_points = sites_df.geometry.representative_point()
    cell_x, cell_y, in_domain = grid.xy_to_cell_index(site_points.x.values, site_points.y.values)
    assert in_domain.all()
    outside = sites_df[mask[cell_y, cell_x] == 0]
    assert len(outside) == 0, outside[["data_source", "data_source_id", "group_id"]].to_string()

    # only known pipelines place any of their length in cells outside the mask
    pipelines_outside = {}
    for _, pipeline in pipelines_df.iterrows():
        weights = grid_weights_from_linestring(grid, pipeline.geometry)
        weight_outside = weights[mask == 0].sum()
        if weight_outside > 0:
            pipelines_outside[pipeline["group_id"]] = weight_outside
    assert set(pipelines_outside) <= set(PIPELINES_LEAVING_JURISDICTION)
    for name, weight_outside in pipelines_outside.items():
        assert weight_outside <= PIPELINES_LEAVING_JURISDICTION[name]


def test_mask_known_places(safeguard_year_config, jurisdiction_data_manager):
    grid = safeguard_year_config.domain().grid
    places = {
        # name: (lon, lat, expected mask value)
        # Australian oil field on the Timor-Leste boundary
        "Laminaria-Corallina": (126.030, -10.627, 1),
        "North Rankin A": (116.13, -19.58, 1),  # offshore platform
        "Port Phillip Bay": (144.90, -38.10, 1),  # internal waters
        "Saibai Island": (142.62, -9.38, 1),  # Australian island next to the PNG coast
        "Daru": (143.21, -9.07, 0),  # Papua New Guinea
        "Dili": (125.57, -8.56, 0),  # Timor-Leste
    }

    mask = create_inventory_political_mask(
        grid=grid,
        states=jurisdiction_data_manager.get_asset(au_shapes_states_data_source).data,
        territorial_sea=jurisdiction_data_manager.get_asset(amb2020_territorial_sea_data_source).data,
        offshore_areas=jurisdiction_data_manager.get_asset(amb2020_offshore_areas_data_source).data,
    )

    actual = {}
    for name, (lon, lat, _) in places.items():
        cell_x, cell_y, in_domain = grid.lonlat_to_cell_index(lon, lat)
        assert in_domain, name
        actual[name] = int(mask[cell_y, cell_x])
    assert actual == {name: expected for name, (_, _, expected) in places.items()}
