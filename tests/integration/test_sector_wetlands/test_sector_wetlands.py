from openmethane_prior.lib import create_prior
from openmethane_prior.sectors.wetland import sector


def test_sector_wetlands(input_files, config):
    """Run the full wetlands sector over the au-test domain."""
    # run the prior and return the result
    prior_wetlands_ds = create_prior(config, [sector])

    assert prior_wetlands_ds['ch4_sector_wetlands'].max().item() == 2.5512281176531815e-10
    assert prior_wetlands_ds['ch4_sector_wetlands'].mean().item() == 1.2524275058017897e-10
