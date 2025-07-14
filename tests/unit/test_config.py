import os
import pathlib
import pytest

from openmethane_prior.config import PriorConfig, LayerInputs, InputDomain, PublishedInputDomain


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
        input_domain=InputDomain("domain-input.nc"),
        output_filename="out.nc",
        layer_inputs=mock_layer_inputs,
    )

    assert test_config.as_input_file("test.nc") == tmp_path / "in" / "test.nc"
    assert test_config.as_output_file("test.nc") == tmp_path / "out" / "test.nc"
    assert test_config.as_intermediate_file("test.nc") == tmp_path / "inter" / "test.nc"

    assert test_config.input_domain_file == tmp_path / "in" / "domain-input.nc"
    assert test_config.output_file == tmp_path / "out" / "out.nc"

def test_input_domain():
    test_defaults = InputDomain("default.nc")
    assert str(test_defaults.path) == "default.nc"
    assert test_defaults.name == "default"
    assert test_defaults.version == "v1"
    assert test_defaults.domain_index == 1
    assert test_defaults.slug == "default"
    assert str(test_defaults.path) == "default.nc"

    test_domain = InputDomain(name="dname", version="v9.0.1", domain_index=33, slug="dslug", path="./file.nc")
    assert test_domain.name == "dname"
    assert test_domain.version == "v9.0.1"
    assert test_domain.domain_index == 33
    assert test_domain.slug == "dslug"
    assert str(test_domain.path) == "file.nc"

    # TODO remove this when slug is added to the domain file attributes
    test_domain = InputDomain("aust10km")
    assert test_domain.name == "aust10km"
    assert test_domain.slug == "10"

def test_published_input_domain():
    test_domain = PublishedInputDomain(name="dname", version="v9.0.1", domain_index=3, slug="dslug")
    assert test_domain.name == "dname"
    assert test_domain.version == "v9.0.1"
    assert test_domain.domain_index == 3
    assert test_domain.slug == "dslug"
    assert str(test_domain.path) == (
        f"domains/dname/v9.0.1/"
        f"prior_domain_dname_v9.0.1.d03.nc"
    )