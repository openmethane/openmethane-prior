import pytest

from openmethane_prior.inputs import check_input_files
from scripts.omDownloadInputs import download_input_files


def test_download_non_relative(tmp_path):
    with pytest.raises(ValueError, match="Check download fragment: ../etc/passwd"):
        download_input_files("http://example.com", tmp_path, ["../etc/passwd"])


def test_check_inputs_missing(config, capsys):
    with pytest.raises(SystemExit):
        check_input_files(config)

    stdout = capsys.readouterr().out

    assert "Some required files are missing" in stdout
    assert "Missing file for domain info at" in stdout
    assert "Missing file for termite data at termite_emissions_2010-2016.nc" in stdout


def test_check_inputs(config, input_files):
    check_input_files(config)
