import pathlib
import pytest
from urllib.error import URLError

from openmethane_prior.lib.config import PriorConfig
from openmethane_prior.lib.data_manager.source import DataSource, configure_data_source


def test_source_file_path(tmp_path, config):
    # file_path provided
    test_data_source = DataSource(
        name="test-unfccc-codes",
        url="https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv",
        file_path="something-else.json",
    )
    configured_data_source = configure_data_source(test_data_source, config, tmp_path)

    assert configured_data_source.asset_path == tmp_path / "something-else.json"

def test_source_data_path(tmp_path, config):
    data_path = tmp_path / "dynamic"
    static_path = tmp_path / "static"

    static_data_source = DataSource(
        name="test-static",
        file_path="static.txt",
    )
    configured_static = configure_data_source(
        data_source=static_data_source,
        prior_config=config,
        data_path=data_path,
        static_path=static_path,
    )

    assert configured_static.asset_path == static_path / "static.txt"

    dynamic_data_source = DataSource(
        name="test-dynamic",
        file_path="dynamic.txt",
        dynamic=True,
    )
    configured_dynamic = configure_data_source(
        data_source=dynamic_data_source,
        prior_config=config,
        data_path=data_path,
        static_path=static_path,
    )
    assert configured_dynamic.asset_path == data_path / "dynamic.txt"

def test_source_file_path_absolute(tmp_path, config):
    # file_path provided
    test_data_source = DataSource(
        name="test-unfccc-codes",
        url="https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv",
        file_path="/var/prior/something-else.json",
    )
    configured_data_source = configure_data_source(test_data_source, config, tmp_path)

    assert configured_data_source.asset_path == pathlib.Path("/var/prior/something-else.json")

def test_source_file_path_from_url(tmp_path, config):
    # no file_path provided, defaults to last part of url
    test_data_source = DataSource(
        name="test-unfccc-codes",
        url="https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv",
    )
    configured_data_source = configure_data_source(test_data_source, config, tmp_path)

    assert configured_data_source.asset_path == tmp_path / "UNFCCC-codes-AU.csv"

def test_source_file_path_callable(tmp_path, config):
    # file_path as a method
    def file_path_from_name(_self: DataSource, config: PriorConfig):
        return f"{_self.name}.nc"

    test_data_source = DataSource(
        name="test-unfccc-codes",
        url="https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv",
        file_path=file_path_from_name,
    )
    configured_data_source = configure_data_source(test_data_source, config, tmp_path)

    assert configured_data_source.asset_path == tmp_path / "test-unfccc-codes.nc"


def test_source_file_path_callable_dynamic(tmp_path, config):
    data_path = tmp_path / "dynamic"
    static_path = tmp_path / "static"

    def file_path_from_name(_self: DataSource, config: PriorConfig):
        return f"{_self.name}.nc"

    dynamic_data_source = DataSource(
        name="test-dynamic",
        file_path=file_path_from_name,
        dynamic=True,
    )
    configured = configure_data_source(
        data_source=dynamic_data_source,
        prior_config=config,
        data_path=data_path,
        static_path=static_path,
    )

    assert configured.asset_path == data_path / "test-dynamic.nc"


def test_source_fetch_default(tmp_path, config):
    data_path = tmp_path / "data"
    test_data_source = DataSource(
        name="test-unfccc-codes",
        url="https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv",
    )
    configured_data_source = configure_data_source(test_data_source, config, data_path)

    assert not configured_data_source.asset_path.exists()

    save_path = configured_data_source.fetch()

    assert save_path.exists()
    assert save_path == configured_data_source.asset_path
    assert save_path == data_path / "UNFCCC-codes-AU.csv"

    with (pytest.raises(URLError) as e):
        bad_data_source = configure_data_source(DataSource(
            name="invalid-url",
            url="https://invalid",
        ), config, data_path)
        bad_data_source.fetch()
