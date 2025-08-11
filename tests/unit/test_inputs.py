import logging

import pytest

from openmethane_prior.config import PriorConfig
from openmethane_prior.inputs import check_input_files
from scripts.omDownloadInputs import download_input_files


def test_download_non_relative(tmp_path):
    with pytest.raises(ValueError, match="Check download fragment: ../etc/passwd"):
        download_input_files("http://example.com", tmp_path, ["../etc/passwd"])


def test_check_inputs_missing(config: PriorConfig, caplog: pytest.LogCaptureFixture):
    with pytest.raises(ValueError):
        check_input_files(config)

    assert "Required inputs are missing" in caplog.text
    assert "(domain info)" in caplog.text
    assert f"{config.layer_inputs.termite_path} (termite data)" in caplog.text


def test_check_inputs(config, input_files):
    check_input_files(config)
