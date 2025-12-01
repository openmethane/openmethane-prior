import numpy as np
import pytest

from openmethane_prior.lib.sector.sector import PriorSector

# PriorSector requires a create_estimate, but we want to do nothing
mock_create_estimate = lambda _a, _b, _c: np.ndarray([])

def test_sector_emission_category():
    assert PriorSector(
        name="test",
        emission_category="natural",
        create_estimate=mock_create_estimate,
    ).emission_category == "natural"
    assert PriorSector(
        name="test",
        emission_category="anthropogenic",
        unfccc_categories=["1"],
        create_estimate=mock_create_estimate,
    ).emission_category == "anthropogenic"

    with pytest.raises(ValueError, match="emission_category must be one of natural, anthropogenic"):
        PriorSector(
            name="test",
            emission_category="other",
            create_estimate=mock_create_estimate,
        )

    with pytest.raises(TypeError, match="missing 1 required positional argument: 'emission_category'"):
        PriorSector(
            name="test",
            create_estimate=mock_create_estimate,
        )

def test_sector_unfccc_category():
    assert PriorSector(
        name="test",
        emission_category="anthropogenic",
        unfccc_categories=["1.", "2."],
        create_estimate=mock_create_estimate,
    ).unfccc_categories == ["1.", "2."]

    with pytest.raises(ValueError, match="natural emissions cannot have unfccc_categories"):
        PriorSector(
            name="test",
            emission_category="natural",
            unfccc_categories=["1."],
            create_estimate=mock_create_estimate,
        )

    with pytest.raises(ValueError, match="anthropogenic emissions must have a value in unfccc_categories"):
        PriorSector(
            name="test",
            emission_category="anthropogenic",
            unfccc_categories=[],
            create_estimate=mock_create_estimate,
        )
    with pytest.raises(ValueError, match="anthropogenic emissions must have a value in unfccc_categories"):
        PriorSector(
            name="test",
            emission_category="anthropogenic",
            create_estimate=mock_create_estimate,
        )
