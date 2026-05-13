from openmethane_prior.lib import create_prior
from openmethane_prior.sectors.wetland import sector


def test_sector_wetlands(input_files, config):
    """Run the full wetlands sector over the au-test domain."""
    # run the prior and return the result
    prior_wetlands_ds = create_prior(config, [sector])

    assert prior_wetlands_ds['ch4_total'].max().item() == 9.336642681185954e-13
    assert prior_wetlands_ds['ch4_sector_wetlands'].max().item() == 9.336642681185954e-13

    assert prior_wetlands_ds['ch4_total'].mean().item() == 8.668152860809177e-14
    assert prior_wetlands_ds['ch4_sector_wetlands'].mean().item() == 8.668152860809177e-14
