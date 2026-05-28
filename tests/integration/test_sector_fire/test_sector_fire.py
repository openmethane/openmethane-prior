import os
import pytest

from openmethane_prior.lib import create_prior
from openmethane_prior.sectors.fire import gfas_data_source, sector


@pytest.mark.skip(reason="Duplicated by test_sector_fire")
def test_cdsapi_connection(tmp_path, data_manager):
    gfas_asset = data_manager.get_asset(gfas_data_source)

    assert os.path.exists(gfas_asset.path)


def test_sector_fire(input_files, config):
    """Run the full fire sector over the au-test domain."""
    prior_fire_ds = create_prior(config, [sector])

    assert prior_fire_ds['ch4_sector_fire'].max().item() == 5.498670963000052e-11
    assert prior_fire_ds['ch4_sector_fire'].mean().item() == 3.6974516872713414e-13
