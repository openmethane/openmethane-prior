from openmethane_prior.data_sources.landuse import alum_codes_for_sector, alum_sector_mapping_data_source


def test_alum_codes_for_sector(data_manager):
    sector_mapping_asset = data_manager.get_asset(alum_sector_mapping_data_source)
    agriculture_codes = alum_codes_for_sector("agriculture", sector_mapping_asset.data)
    assert agriculture_codes == [210, 320, 420, 520, 521, 522, 523, 524, 525, 526, 527, 542]

    assert alum_codes_for_sector("fake sector", sector_mapping_asset.data) == []
