import pathlib

import pytest

from openmethane_prior.lib.config import PriorConfig
from openmethane_prior.lib.create_prior import create_prior


@pytest.fixture()
def minimal_config(tmp_path: pathlib.Path, start_date, end_date):
    """A config that doesn't require any real domain/input data, since the
    tests below mock out everything that would read it."""

    def _make(**kwargs):
        params = dict(
            domain_path="domain.nc",
            start_date=start_date,
            end_date=end_date,
            input_path=tmp_path / "in",
            intermediates_path=tmp_path / "intermediates",
            output_path=tmp_path / "out",
            static_path=tmp_path / "static",
            output_filename="prior-emissions.nc",
        )
        params.update(kwargs)
        return PriorConfig(**params)

    return _make


def test_create_prior_requires_start_date(minimal_config):
    config = minimal_config(start_date=None, end_date=None)

    with pytest.raises(ValueError, match="Start date must be provided"):
        create_prior(config, sectors=[])


def test_create_prior_calls_sector_create_estimate(minimal_config, mocker):
    config = minimal_config()

    mocker.patch("openmethane_prior.lib.create_prior.DataManager")
    mocker.patch("openmethane_prior.lib.create_prior.create_output_dataset")
    mocker.patch("openmethane_prior.lib.create_prior.add_ch4_total")
    mock_add_sector = mocker.patch("openmethane_prior.lib.create_prior.add_sector")

    sector = mocker.Mock()
    sector.create_estimate = mocker.Mock(return_value="sector-data")

    create_prior(config, sectors=[sector])

    sector.create_estimate.assert_called_once()
    mock_add_sector.assert_called_once()


def test_create_prior_raises_for_uncallable_sector(minimal_config, mocker):
    config = minimal_config()

    mocker.patch("openmethane_prior.lib.create_prior.DataManager")
    mocker.patch("openmethane_prior.lib.create_prior.create_output_dataset")

    sector = mocker.Mock()
    sector.create_estimate = None

    with pytest.raises(ValueError, match="must include a create_estimate function"):
        create_prior(config, sectors=[sector])
