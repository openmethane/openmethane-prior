from openmethane_prior.lib import create_prior
from openmethane_prior.sectors.termite import sector


def test_sector_termite(input_files, config):
    """Run the full termite sector over the au-test domain."""
    prior_termite_ds = create_prior(config, [sector])

    assert prior_termite_ds['ch4_sector_termite'].max().item() == 3.38580183854853e-12
    assert prior_termite_ds['ch4_sector_termite'].mean().item() == 2.436579367090519e-12
