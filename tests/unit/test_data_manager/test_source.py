from urllib.error import URLError

import pytest
from openmethane_prior.data_manager.source import DataSource


def test_source_file_name():
    # no file_name provided, defaults to last part of url
    test_data_source = DataSource(
        name="test-unfccc-codes",
        url="https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv",
    )

    assert test_data_source.file_name == "UNFCCC-codes-AU.csv"

    # file_name provided
    test_data_source = DataSource(
        name="test-unfccc-codes",
        url="https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv",
        file_name="something-else.json",
    )

    assert test_data_source.file_name == "something-else.json"


def test_source_fetch(tmp_path):
    data_path = tmp_path / "data"

    test_data_source = DataSource(
        name="test-unfccc-codes",
        url="https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv",
    )

    save_path = test_data_source.fetch(data_path)

    assert save_path.exists()
    assert save_path == data_path / "UNFCCC-codes-AU.csv"

    with pytest.raises(URLError) as e:
        DataSource(
            name="invalid-url",
            url="https://invalid",
        ).fetch(data_path)
