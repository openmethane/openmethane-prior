import pytest

from openmethane_prior.sectors.wetland.sector import regrid_satwet, satwet_giems_data_source


@pytest.mark.skip(reason="Makes no assertions")
def test_wetland_emis(config, input_files, data_manager):
    # TODO: convert into an actual test
    """Test totals for WETLAND emissions between original and remapped"""
    satwet_asset = data_manager.get_asset(satwet_giems_data_source)
    regridded, satwet_times = regrid_satwet(config, satwet_asset)
    # TODO: add assertions comparing regridded totals to source totals
