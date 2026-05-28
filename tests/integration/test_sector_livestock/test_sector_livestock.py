from openmethane_prior.lib import create_prior
from openmethane_prior.sectors.livestock import sector


def test_sector_livestock(input_files, config):
    """Run the full livestock sector over the au-test domain."""
    # run the prior and return the result
    prior_livestock_ds = create_prior(config, [sector])

    print(prior_livestock_ds['ch4_sector_livestock'].max())

    assert prior_livestock_ds['ch4_sector_livestock'].max().item() == 6.201040469743898e-11
    assert prior_livestock_ds['ch4_sector_livestock'].mean().item() == 3.9170379930287976e-11
