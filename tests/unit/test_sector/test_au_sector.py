
import pytest

from openmethane_prior.lib.sector.au_sector import AustraliaPriorSector


def test_au_sector_anzsic_codes():
    assert AustraliaPriorSector(
        name="test",
        emission_category="anthropogenic",
        unfccc_categories=["1.", "2."],
        anzsic_codes=["11", "2200"],
        create_estimate=lambda a, b, c: None,
    ).anzsic_codes == ["11", "2200"]

    # anzsic_codes is optional
    assert AustraliaPriorSector(
        name="test",
        emission_category="anthropogenic",
        unfccc_categories=["1.", "2."],
        create_estimate=lambda a, b, c: None,
    ).anzsic_codes is None

    with pytest.raises(ValueError, match="natural emissions cannot have anzsic_codes"):
        AustraliaPriorSector(
            name="test",
            emission_category="natural",
            anzsic_codes=["11"],
            create_estimate=lambda a, b, c: None,
        )

