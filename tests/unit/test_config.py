import os
import pathlib
import pytest

from openmethane_prior.config import PriorConfig, LayerInputs


# This fixture will allow each test to setup the required env variables and
# then reset back to the intial env before the next test
@pytest.fixture(autouse=True)
def env(monkeypatch, root_dir):
    initial_env = dict(os.environ)

    yield

    # Reset environment to initial state
    os.environ.clear()
    os.environ.update(initial_env)

@pytest.fixture
def mock_layer_inputs(tmp_path):
    # mock paths to fake filenames
    return LayerInputs(
        inventory_path=pathlib.Path("./CH4_INVENTORY_CSV.csv"),
        unfccc_categories_path=pathlib.Path("./UNFCCC_SECTOR_AU_MAPPING.csv"),
        electricity_path=pathlib.Path("./CH4_ELECTRICITY.nc"),
        oil_gas_path=pathlib.Path("./CH4_OILGAS.nc"),
        coal_path=pathlib.Path("./CH4_COAL.nc"),
        land_use_path=pathlib.Path("./LAND_USE.nc"),
        sectoral_emissions_path=pathlib.Path("./SECTORAL_EMISSIONS.nc"),
        sectoral_mapping_path=pathlib.Path("./SECTORAL_MAPPING.nc"),
        ntl_path=pathlib.Path("./NTL.nc"),
        aus_shapefile_path=pathlib.Path("./AUSF.nc"),
        livestock_path=pathlib.Path("./LIVESTOCK_DATA.nc"),
        termite_path=pathlib.Path("./TERMITES.nc"),
        wetland_path=pathlib.Path("./WETLANDS.nc"),
    )

def test_prior_config(tmp_path: pathlib.Path, mock_layer_inputs):
    test_config = PriorConfig(
        remote="http://example.com",
        input_path=tmp_path / "in",
        output_path=tmp_path / "out",
        intermediates_path=tmp_path / "inter",
        domain_path="domain-input.nc",
        inventory_domain_path="domain-input.nc",
        output_filename="out.nc",
        layer_inputs=mock_layer_inputs,
    )

    assert test_config.as_input_file("test.nc") == tmp_path / "in" / "test.nc"
    assert test_config.as_output_file("test.nc") == tmp_path / "out" / "test.nc"
    assert test_config.as_intermediate_file("test.nc") == tmp_path / "inter" / "test.nc"

    assert test_config.domain_file == tmp_path / "in" / "domain-input.nc"
    assert test_config.inventory_domain_file == tmp_path / "in" / "domain-input.nc"
    assert test_config.output_file == tmp_path / "out" / "out.nc"
