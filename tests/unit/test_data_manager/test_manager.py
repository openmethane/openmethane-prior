import logging
import os

import pytest
from openmethane_prior.data_manager.manager import DataManager
from openmethane_prior.data_manager.source import DataSource


def test_manager_add_source(tmp_path):
    data_path = tmp_path / "data"
    test_manager = DataManager(data_path=data_path)

    test_manager.add_source(DataSource(
        name="test-unfccc-codes",
        url="https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv",
    ))
    test_manager.add_source(DataSource(
        name="test-other",
        url="https://example.com/test.csv",
    ))

    assert list(test_manager.data_sources.keys()) == ["test-unfccc-codes", "test-other"]
    assert test_manager.data_sources.get("test-unfccc-codes") == DataSource(
        name="test-unfccc-codes",
        url="https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv",
    )
    assert test_manager.data_sources.get("test-other") == DataSource(
        name="test-other",
        url="https://example.com/test.csv",
    )

    # not fetched yet
    assert list(test_manager.data_assets.keys()) == []


def test_manager_add_source_duplicate(tmp_path, caplog):
    data_path = tmp_path / "data"
    test_manager = DataManager(data_path=data_path)

    test_manager.add_source(DataSource(
        name="test-unfccc-codes",
        url="https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv",
    ))

    assert len(test_manager.data_sources.keys()) == 1
    assert test_manager.data_sources.get("test-unfccc-codes") == DataSource(
        name="test-unfccc-codes",
        url="https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv",
    )

    # add the same source again
    test_manager.add_source(DataSource(
        name="test-unfccc-codes",
        url="https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv",
    ))

    # no additional sources added
    assert len(test_manager.data_sources.keys()) == 1

    # same source name but different url triggers a warning
    with caplog.at_level(logging.WARNING):
        test_manager.add_source(DataSource(
            name="test-unfccc-codes",
            url="https://example.com/different-url",
        ))

    assert "multiple DataSource instances with name 'test-unfccc-codes' providing different URLs" in caplog.text
    assert len(test_manager.data_sources.keys()) == 1


def test_manager_ready_assets(tmp_path):
    data_path = tmp_path / "data"
    test_manager = DataManager(data_path=data_path)
    test_manager.add_source(DataSource(
        name="test-unfccc-codes",
        url="https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv",
    ))

    assert not data_path.exists()

    test_manager.ready_assets()

    assert data_path.exists()
    assert os.listdir(data_path) == [
        "UNFCCC-codes-AU.csv",
    ]
    assert list(test_manager.data_assets.keys()) == ["test-unfccc-codes"]
    assert test_manager.get_asset("test-unfccc-codes").name == "test-unfccc-codes"
    assert test_manager.get_asset("test-unfccc-codes").path == data_path / "UNFCCC-codes-AU.csv"
    assert test_manager.get_asset("test-unfccc-codes").path.exists()


def test_manager_get_asset(tmp_path):
    data_path = tmp_path / "data"
    test_manager = DataManager(data_path=data_path)

    with pytest.raises(ValueError, match=f"Asset 'test-unfccc-codes' not found") as e:
        test_manager.get_asset("test-unfccc-codes")

    test_manager.add_source(DataSource(
        name="test-unfccc-codes",
        url="https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv",
    ))

    with pytest.raises(ValueError, match=f"Asset 'test-unfccc-codes' not ready") as e:
        test_manager.get_asset("test-unfccc-codes")

    test_manager.ready_assets()

    test_asset = test_manager.get_asset("test-unfccc-codes")

    assert test_asset is not None
    assert test_asset.name == "test-unfccc-codes"
    assert test_asset.path == data_path / "UNFCCC-codes-AU.csv"
    assert test_asset.path.exists()
