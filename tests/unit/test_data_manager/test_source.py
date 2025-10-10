from urllib.error import URLError

import pytest

from openmethane_prior.config import PriorConfig
from openmethane_prior.data_manager.source import DataSource, configure_data_source


def test_source_file_name(tmp_path, config):
    # file_name provided
    test_data_source = DataSource(
        name="test-unfccc-codes",
        url="https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv",
        file_name="something-else.json",
    )
    configured_data_source = configure_data_source(test_data_source, config, tmp_path)

    assert configured_data_source.file_name == "something-else.json"

def test_source_file_name_from_url(tmp_path, config):
    # no file_name provided, defaults to last part of url
    test_data_source = DataSource(
        name="test-unfccc-codes",
        url="https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv",
    )
    configured_data_source = configure_data_source(test_data_source, config, tmp_path)

    assert configured_data_source.file_name == "UNFCCC-codes-AU.csv"

def test_source_file_name_callable(tmp_path, config):
    # file_name as a method
    def file_name_from_name(_self: DataSource, config: PriorConfig):
        return f"{_self.name}.nc"

    test_data_source = DataSource(
        name="test-unfccc-codes",
        url="https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv",
        file_name=file_name_from_name,
    )
    configured_data_source = configure_data_source(test_data_source, config, tmp_path)

    assert configured_data_source.file_name == "test-unfccc-codes.nc"


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
