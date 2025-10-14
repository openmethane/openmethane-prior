
import pytest

from openmethane_prior.lib.sector.sector import SectorMeta


def test_sector_emission_category():
    assert SectorMeta(
        name="test",
        emission_category="natural",
    ).emission_category == "natural"
    assert SectorMeta(
        name="test",
        emission_category="anthropogenic",
        unfccc_categories=["1"],
    ).emission_category == "anthropogenic"

    with pytest.raises(ValueError, match="emission_category must be one of natural, anthropogenic"):
        SectorMeta(name="test", emission_category="other")

    with pytest.raises(TypeError, match="missing 1 required positional argument: 'emission_category'"):
        SectorMeta(name="test")

def test_sector_unfccc_category():
    assert SectorMeta(
        name="test",
        emission_category="anthropogenic",
        unfccc_categories=["1.", "2."],
    ).unfccc_categories == ["1.", "2."]

    with pytest.raises(ValueError, match="natural emissions cannot have unfccc_categories"):
        SectorMeta(
            name="test",
            emission_category="natural",
            unfccc_categories=["1."],
        )

    with pytest.raises(ValueError, match="anthropogenic emissions must have a value in unfccc_categories"):
        SectorMeta(
            name="test",
            emission_category="anthropogenic",
            unfccc_categories=[],
        )
        SectorMeta(
            name="test",
            emission_category="anthropogenic",
        )
