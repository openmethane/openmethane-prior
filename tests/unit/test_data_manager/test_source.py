import pathlib
import pytest
from urllib.error import URLError

from openmethane_prior.lib.config import PriorParameters
from openmethane_prior.lib.data_manager.source import DataSource, configure_data_source


def test_source_file_path(tmp_path, params):
    test_data_source = DataSource(
        name="test-unfccc-codes",
        url="https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv",
        file_path="something-else.json",
    )
    configured_data_source = configure_data_source(test_data_source, params, tmp_path)

    assert configured_data_source.asset_path == tmp_path / "something-else.json"

def test_source_file_path_absolute(tmp_path, params):
    test_data_source = DataSource(
        name="test-unfccc-codes",
        url="https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv",
        file_path="/var/prior/something-else.json",
    )
    configured_data_source = configure_data_source(test_data_source, params, tmp_path)

    assert configured_data_source.asset_path == pathlib.Path("/var/prior/something-else.json")

def test_source_file_path_from_url(tmp_path, params):
    test_data_source = DataSource(
        name="test-unfccc-codes",
        url="https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv",
    )
    configured_data_source = configure_data_source(test_data_source, params, tmp_path)

    assert configured_data_source.asset_path == tmp_path / "UNFCCC-codes-AU.csv"

def test_source_file_path_callable(tmp_path, params):
    def file_path_from_name(_self: DataSource, p: PriorParameters):
        return f"{_self.name}.nc"

    test_data_source = DataSource(
        name="test-unfccc-codes",
        url="https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv",
        file_path=file_path_from_name,
    )
    configured_data_source = configure_data_source(test_data_source, params, tmp_path)

    assert configured_data_source.asset_path == tmp_path / "test-unfccc-codes.nc"


def test_source_fetch_default(tmp_path, params):
    data_path = tmp_path / "data"
    test_data_source = DataSource(
        name="test-unfccc-codes",
        url="https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv",
    )
    configured_data_source = configure_data_source(test_data_source, params, data_path)

    assert not configured_data_source.asset_path.exists()

    save_path = configured_data_source.fetch()

    assert save_path.exists()
    assert save_path == configured_data_source.asset_path
    assert save_path == data_path / "UNFCCC-codes-AU.csv"

    with (pytest.raises(URLError) as e):
        bad_data_source = configure_data_source(DataSource(
            name="invalid-url",
            url="https://invalid",
        ), params, data_path)
        bad_data_source.fetch()
