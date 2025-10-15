
import pytest

from openmethane_prior.lib.sector.sector import PriorSector


def test_sector_emission_category():
    assert PriorSector(
        name="test",
        emission_category="natural",
        create_estimate=lambda a, b, c: None,
    ).emission_category == "natural"
    assert PriorSector(
        name="test",
        emission_category="anthropogenic",
        unfccc_categories=["1"],
        create_estimate=lambda a, b, c: None,
    ).emission_category == "anthropogenic"

    with pytest.raises(ValueError, match="emission_category must be one of natural, anthropogenic"):
        PriorSector(
            name="test",
            emission_category="other",
            create_estimate=lambda a, b, c: None,
        )

    with pytest.raises(TypeError, match="missing 1 required positional argument: 'emission_category'"):
        PriorSector(
            name="test",
            create_estimate=lambda a, b, c: None,
        )

def test_sector_unfccc_category():
    assert PriorSector(
        name="test",
        emission_category="anthropogenic",
        unfccc_categories=["1.", "2."],
        create_estimate=lambda a, b, c: None,
    ).unfccc_categories == ["1.", "2."]

    with pytest.raises(ValueError, match="natural emissions cannot have unfccc_categories"):
        PriorSector(
            name="test",
            emission_category="natural",
            unfccc_categories=["1."],
            create_estimate=lambda a, b, c: None,
        )

    with pytest.raises(ValueError, match="anthropogenic emissions must have a value in unfccc_categories"):
        PriorSector(
            name="test",
            emission_category="anthropogenic",
            unfccc_categories=[],
            create_estimate=lambda a, b, c: None,
        )
    with pytest.raises(ValueError, match="anthropogenic emissions must have a value in unfccc_categories"):
        PriorSector(
            name="test",
            emission_category="anthropogenic",
            create_estimate=lambda a, b, c: None,
        )
