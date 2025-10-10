import logging

from openmethane_prior.data_manager.manager import DataManager
from openmethane_prior.data_manager.source import DataSource, ConfiguredDataSource
from pytest_mock import MockerFixture


def test_manager_add_source(tmp_path, config):
    data_path = tmp_path / "data"
    test_manager = DataManager(data_path=data_path, prior_config=config)

    test_manager.add_source(DataSource(
        name="test-unfccc-codes",
        url="https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv",
    ))
    test_manager.add_source(DataSource(
        name="test-other",
        url="https://example.com/test.csv",
    ))

    assert list(test_manager.data_sources.keys()) == ["test-unfccc-codes", "test-other"]
    assert test_manager.data_sources.get("test-unfccc-codes").name == "test-unfccc-codes"
    assert test_manager.data_sources.get("test-unfccc-codes").url == "https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv"

    assert test_manager.data_sources.get("test-other").name == "test-other"
    assert test_manager.data_sources.get("test-other").url == "https://example.com/test.csv"

    # not fetched yet
    assert list(test_manager.data_assets.keys()) == []


def test_manager_add_source_duplicate(tmp_path, caplog, config):
    data_path = tmp_path / "data"
    test_manager = DataManager(data_path=data_path, prior_config=config)

    test_manager.add_source(DataSource(
        name="test-unfccc-codes",
        url="https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv",
    ))

    assert len(test_manager.data_sources.keys()) == 1
    assert test_manager.data_sources.get("test-unfccc-codes").name == "test-unfccc-codes"
    assert test_manager.data_sources.get("test-unfccc-codes").url == "https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv"

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


def test_manager_get_asset(tmp_path, config, mocker: MockerFixture):
    data_path = tmp_path / "data"
    mock_fetch = mocker.stub(name="mock_fetch")
    mock_fetch.return_value = data_path / "filename.csv"

    test_manager = DataManager(data_path=data_path, prior_config=config)
    test_data_source = DataSource(
        name="test-unfccc-codes",
        url="https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv",
        fetch=mock_fetch,
    )

    assert mock_fetch.call_count == 0

    test_asset = test_manager.get_asset(test_data_source)

    assert mock_fetch.call_count == 1
    assert test_asset.name == "test-unfccc-codes"
    assert test_asset.path == data_path / "filename.csv"

    test_second_asset = test_manager.get_asset(test_data_source)

    # fetch is not called again, the same asset is returned
    assert mock_fetch.call_count == 1
    assert test_second_asset is test_asset


def test_manager_get_asset_parsed(tmp_path, mocker: MockerFixture, config):
    data_path = tmp_path / "data"
    mock_fetch = mocker.stub(name="mock_fetch")
    mock_fetch.return_value = data_path / "filename.csv"
    mock_parse = mocker.stub(name="mock_parse")
    mock_parse.return_value = "data"

    test_manager = DataManager(data_path=data_path, prior_config=config)
    test_data_source = DataSource(
        name="test-unfccc-codes",
        url="https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv",
        fetch=mock_fetch,
        parse=mock_parse,
    )

    assert mock_fetch.call_count == 0
    assert mock_parse.call_count == 0

    test_asset = test_manager.get_asset(test_data_source)

    assert mock_fetch.call_count == 1
    assert mock_parse.call_count == 1
    assert test_asset.name == "test-unfccc-codes"
    assert test_asset.path == data_path / "filename.csv"
    assert test_asset.data == "data"

    test_second_asset = test_manager.get_asset(test_data_source)

    # fetch is not called again, the same asset is returned
    assert mock_fetch.call_count == 1
    assert mock_parse.call_count == 1
    assert test_second_asset is test_asset


def test_manager_get_asset_dependencies(tmp_path, mocker, config):
    data_path = tmp_path / "data"
    child_fetch = mocker.stub(name="child_fetch")
    child_fetch.return_value = data_path / "child.csv"
    child_parse = mocker.stub(name="child_parse")
    child_parse.return_value = "child data"
    parent_fetch = mocker.stub(name="parent_fetch")
    parent_fetch.return_value = data_path / "parent.csv"

    def parent_parse(source: ConfiguredDataSource):
        return f"parent of {source.data_assets[0].data}"

    test_manager = DataManager(data_path=data_path, prior_config=config)
    child_data_source = DataSource(
        name="test-child",
        url="https://openmethane.s3.amazonaws.com/prior/inputs/child.csv",
        fetch=child_fetch,
        parse=child_parse,
    )
    parent_data_source = DataSource(
        name="test-parent",
        url="https://openmethane.s3.amazonaws.com/prior/inputs/parent.csv",
        fetch=parent_fetch,
        parse=parent_parse,
        data_sources=[child_data_source],
    )

    assert child_fetch.call_count == 0
    assert child_parse.call_count == 0

    test_asset = test_manager.get_asset(parent_data_source)

    assert child_fetch.call_count == 1
    assert child_parse.call_count == 1

    assert test_asset.data == "parent of child data"
