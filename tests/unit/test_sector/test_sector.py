
import pytest

from openmethane_prior.sector.sector import SectorMeta


def test_sector_emission_category():
    assert SectorMeta(name="test", emission_category="natural").emission_category == "natural"
    assert SectorMeta(name="test", emission_category="anthropogenic").emission_category == "anthropogenic"

    with pytest.raises(ValueError, match="emission_category must be one of natural, anthropogenic"):
        SectorMeta(name="test", emission_category="other")

    with pytest.raises(TypeError, match="missing 1 required positional argument: 'emission_category'"):
        SectorMeta(name="test")
