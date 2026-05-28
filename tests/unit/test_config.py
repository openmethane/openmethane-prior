import datetime
import os
import pathlib
import pytest

from openmethane_prior.lib.config import PriorConfig, fetch_domain


# This fixture will allow each test to setup the required env variables and
# then reset back to the initial env before the next test
@pytest.fixture()
def reset_env(monkeypatch):
    initial_env = dict(os.environ)
    os.environ.clear()

    yield

    # Reset environment to initial state
    os.environ.clear()
    os.environ.update(initial_env)


def test_prior_config_defaults(start_date, end_date):
    test_config = PriorConfig(
        domain_path="domain.nc",
        start_date=start_date,
        end_date=end_date,
    )

    assert test_config.domain_path == "domain.nc"
    assert test_config.start_date == start_date
    assert test_config.end_date == end_date

    # defaults
    assert test_config.sectors is None
    assert test_config.input_path == pathlib.Path("data/inputs")
    assert test_config.output_path == pathlib.Path("data/outputs")
    assert test_config.intermediates_path == pathlib.Path("data/intermediates")
    assert test_config.output_filename == "prior-emissions.nc"
    assert test_config.static_path == test_config.input_path
    assert test_config.input_cache is None

    test_config_none = PriorConfig(
        domain_path="domain.nc",
        start_date=start_date,
        end_date=end_date,
        input_path=None,
        output_path=None,
        intermediates_path=None,
        output_filename=None,
    )

    # defaults
    assert test_config_none.input_path == pathlib.Path("data/inputs")
    assert test_config_none.output_path == pathlib.Path("data/outputs")
    assert test_config_none.intermediates_path == pathlib.Path("data/intermediates")
    assert test_config_none.static_path == test_config_none.input_path
    assert test_config_none.output_filename == "prior-emissions.nc"


def test_prior_config_full(tmp_path: pathlib.Path, start_date, end_date):
    test_config = PriorConfig(
        domain_path="domain.nc",
        start_date=start_date,
        end_date=end_date,
        input_path=tmp_path / "in",
        output_path=tmp_path / "out",
        intermediates_path=tmp_path / "inter",
        static_path=tmp_path / "static",
        output_filename="out.nc",
    )

    assert test_config.output_file == tmp_path / "out" / "out.nc"
    assert test_config.static_path == tmp_path / "static"
    assert test_config.static_path != test_config.input_path


def test_prior_config_prepare_paths_creates_static(tmp_path: pathlib.Path, start_date, end_date):
    static_path = tmp_path / "static"
    test_config = PriorConfig(
        domain_path="domain.nc",
        start_date=start_date,
        end_date=end_date,
        input_path=tmp_path / "in",
        output_path=tmp_path / "out",
        intermediates_path=tmp_path / "inter",
        static_path=static_path,
    )

    assert not test_config.input_path.exists()
    assert not test_config.intermediates_path.exists()
    assert not test_config.output_path.exists()
    assert not test_config.static_path.exists()

    test_config.prepare_paths()

    assert test_config.input_path.exists()
    assert test_config.intermediates_path.exists()
    assert test_config.output_path.exists()
    assert test_config.static_path.exists()


def test_prior_config_to_yaml(start_date, end_date):
    test_config = PriorConfig(
        domain_path="domain.nc",
        start_date=start_date,
        end_date=end_date,
        input_path=pathlib.Path("data/input"),
        output_path=pathlib.Path("data/out"),
        intermediates_path=pathlib.Path("data/inter"),
        static_path=pathlib.Path("data/in"),
    )

    assert test_config.to_yaml() == """domain_path: domain.nc
end_date: 2022-12-08 00:00:00
input_cache: null
input_path: data/input
intermediates_path: data/inter
output_filename: prior-emissions.nc
output_path: data/out
sectors: null
start_date: 2022-12-07 00:00:00
static_path: data/in
"""


def test_prior_config_from_env(reset_env, start_date, end_date):
    os.environ["DOMAIN_FILE"] = "env-domain.nc"
    os.environ["START_DATE"] = "2023-01-01"
    os.environ["END_DATE"] = "2023-01-31"
    os.environ["SECTORS"] = "agriculture,coal,waste"
    os.environ["INPUTS"] = "env/in"
    os.environ["OUTPUTS"] = "env/out"
    os.environ["INTERMEDIATES"] = "env/inter"
    os.environ["STATIC_INPUTS"] = "env/static"
    os.environ["INPUT_CACHE"] = "env/cache"
    os.environ["OUTPUT_FILENAME"] = "env-output.nc"

    test_config = PriorConfig.from_env()

    assert test_config.domain_path == "env-domain.nc"
    assert test_config.start_date == datetime.datetime(2023, 1, 1, 0, 0, 0)
    assert test_config.end_date == datetime.datetime(2023, 1, 31, 0, 0, 0)
    assert test_config.sectors == ("agriculture", "coal", "waste")
    assert test_config.input_path == pathlib.Path("env/in")
    assert test_config.output_path == pathlib.Path("env/out")
    assert test_config.intermediates_path == pathlib.Path("env/inter")
    assert test_config.static_path == pathlib.Path("env/static")
    assert test_config.input_cache == pathlib.Path("env/cache")
    assert test_config.output_filename == "env-output.nc"


def test_prior_config_input_cache(tmp_path: pathlib.Path, start_date, end_date):
    generic_params = dict(domain_path="domain.nc", start_date=start_date)

    data_path = tmp_path / "data"
    cache_path = tmp_path / "cache-test"

    # created some cached content
    (cache_path / "inputs").mkdir(parents=True)
    cache_test_contents = f"cache test {datetime.datetime.now()}"
    with open(cache_path / "inputs/cache-test.txt", "w") as cache_test_file:
        cache_test_file.write(cache_test_contents)

    # create a config with input_cache
    test_config = PriorConfig(
        **generic_params,
        input_path=data_path / "input-test",
        input_cache=cache_path,
    )

    assert not (test_config.input_path / "cache-test.txt").exists()

    test_config.load_cached_inputs()

    assert (test_config.input_path / "cache-test.txt").exists()

    with open(test_config.input_path / "cache-test.txt") as input_file:
        assert input_file.read() == cache_test_contents

    # create a new input in the prior input folder
    cache_test_updated = f"cache updated {datetime.datetime.now()}"
    with open(test_config.input_path / "cache-update.txt", "w") as cache_test_file:
        cache_test_file.write(cache_test_updated)

    # the new file is not copied to the cache yet
    assert not (cache_path / "inputs/cache-update.txt").exists()

    # reassign the variable to trigger the PriorConfig deconstructor
    test_config.cache_inputs()

    # updated inputs are copied back to the cache
    assert (cache_path / "inputs/cache-update.txt").exists()
    with open(cache_path / "inputs/cache-update.txt") as input_file:
        assert input_file.read() == cache_test_updated

    # create a config with a different input_cache
    test_config = PriorConfig(
        **generic_params,
        input_path=data_path / "new-input",
        input_cache=data_path / "new-cache",
    )

    # the file from the cache is NOT copied
    assert not (test_config.input_path / "cache-test.txt").exists()


# ---------------------------------------------------------------------------
# fetch_domain tests
# ---------------------------------------------------------------------------

@pytest.fixture()
def input_path(tmp_path):
    path = tmp_path / "inputs"
    path.mkdir()
    return path


@pytest.fixture()
def mock_retrieve(mocker):
    return mocker.patch("urllib.request.urlretrieve")


def test_fetch_domain_returns_path_under_input_path(input_path, mock_retrieve):
    """Returned path is always input_path / basename(path_or_url)."""
    mock_retrieve.return_value = (str(input_path / "domain.nc"), None)
    result = fetch_domain("https://example.com/some/nested/domain.nc", input_path)
    assert result == input_path / "domain.nc"


def test_fetch_domain_downloads_url_when_file_missing(input_path, mock_retrieve):
    """Calls urlretrieve with the URL and destination path when file is absent."""
    url = "https://example.com/domain.nc"
    expected_dest = input_path / "domain.nc"
    mock_retrieve.return_value = (str(expected_dest), None)

    fetch_domain(url, input_path)

    mock_retrieve.assert_called_once_with(url=url, filename=expected_dest)


def test_fetch_domain_skips_download_when_file_exists(input_path, mock_retrieve):
    """Does not call urlretrieve when the destination file already exists."""
    (input_path / "domain.nc").touch()

    result = fetch_domain("https://example.com/domain.nc", input_path)

    mock_retrieve.assert_not_called()
    assert result == input_path / "domain.nc"


def test_fetch_domain_uses_basename_of_url(input_path, mock_retrieve):
    """Only the basename of a URL with path segments is used as the filename."""
    url = "https://example.com/v1/au-test/my-domain-file.nc"
    expected_dest = input_path / "my-domain-file.nc"
    mock_retrieve.return_value = (str(expected_dest), None)

    result = fetch_domain(url, input_path)

    assert result.name == "my-domain-file.nc"
    mock_retrieve.assert_called_once_with(url=url, filename=expected_dest)


def test_fetch_domain_hardlinks_local_file(input_path, mock_retrieve):
    """Creates a hard link in input_path when given a path to an existing local file."""
    source = input_path.parent / "source" / "domain.nc"
    source.parent.mkdir()
    source.write_text("domain content")

    result = fetch_domain(str(source), input_path)

    mock_retrieve.assert_not_called()
    assert result == input_path / "domain.nc"
    assert result.exists()
    assert result.read_text() == "domain content"


def test_fetch_domain_skips_hardlink_when_dest_exists(input_path, mocker, mock_retrieve):
    """Does not create a hard link when the destination already exists."""
    source = input_path.parent / "source" / "domain.nc"
    source.parent.mkdir()
    source.write_text("source content")

    existing = input_path / "domain.nc"
    existing.write_text("existing content")

    mock_hardlink = mocker.patch.object(pathlib.Path, "hardlink_to")
    result = fetch_domain(str(source), input_path)

    mock_hardlink.assert_not_called()
    assert result.read_text() == "existing content"