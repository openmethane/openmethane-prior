import numpy as np
import pytest

from openmethane_prior.grid.domain_grid import DomainGrid


def test_grid_attributes(input_domain):
    test_grid = DomainGrid(input_domain)

    assert test_grid.dimensions == (input_domain.COL.size, input_domain.ROW.size)
    assert test_grid.shape == (input_domain.ROW.size, input_domain.COL.size)
    assert test_grid.center_lonlat == (input_domain.XCENT, input_domain.YCENT)
    assert test_grid.origin_xy == (input_domain.XORIG, input_domain.YORIG)
    assert test_grid.cell_size == (input_domain.XCELL, input_domain.YCELL)

def test_grid_center(input_domain):
    test_grid = DomainGrid(input_domain)

    grid_center_x, grid_center_y = test_grid.projection(input_domain.XCENT, input_domain.YCENT)

    assert test_grid.center_xy == (grid_center_x, grid_center_y)


def test_grid_llc_xy(input_domain):
    test_grid = DomainGrid(input_domain)

    grid_center_x, grid_center_y = test_grid.projection(input_domain.XCENT, input_domain.YCENT)
    grid_llc_x = grid_center_x + input_domain.XORIG
    grid_llc_y = grid_center_y + input_domain.YORIG

    assert test_grid.llc_xy == (grid_llc_x, grid_llc_y)

def test_grid_llc_center_xy(input_domain):
    test_grid = DomainGrid(input_domain)

    grid_center_x, grid_center_y = test_grid.projection(input_domain.XCENT, input_domain.YCENT)
    grid_llc_center_x = grid_center_x + input_domain.XORIG + (input_domain.XCELL / 2)
    grid_llc_center_y = grid_center_y + input_domain.YORIG + (input_domain.YCELL / 2)

    assert test_grid.llc_center_xy == (grid_llc_center_x, grid_llc_center_y)

def test_grid_cell_area(input_domain):
    test_grid = DomainGrid(input_domain)

    assert test_grid.cell_area == input_domain.XCELL * input_domain.YCELL

def test_grid_coords(input_domain):
    test_grid = DomainGrid(input_domain)
    cell_coords_x = test_grid.cell_coords_x()
    cell_coords_y = test_grid.cell_coords_y()

    assert len(cell_coords_x) == input_domain.COL.size
    assert cell_coords_x[0] == test_grid.llc_center_xy[0]

    assert len(cell_coords_y) == input_domain.ROW.size
    assert cell_coords_y[0] == test_grid.llc_center_xy[1]

def test_grid_bounds(input_domain):
    test_grid = DomainGrid(input_domain)
    cell_bounds_x = test_grid.cell_bounds_x()
    cell_bounds_y = test_grid.cell_bounds_y()

    assert len(cell_bounds_x) == input_domain.COL.size + 1
    assert cell_bounds_x[0] == test_grid.llc_xy[0]

    assert len(cell_bounds_y) == input_domain.ROW.size + 1
    assert cell_bounds_y[0] == test_grid.llc_xy[1]

def test_grid_xy_to_lonlat(input_domain):
    test_grid = DomainGrid(input_domain)

    # this is sort of a "round trip" test, as DomainGrid.center_xy is calculated
    # by running the center_lonlat through the projection forward.
    grid_center_lonlat = test_grid.xy_to_lonlat(*test_grid.center_xy)

    np.testing.assert_allclose(grid_center_lonlat, (input_domain.XCENT, input_domain.YCENT))

def test_grid_projection_coordinates(input_domain):
    test_grid = DomainGrid(input_domain)

    # projection center coords for all cells in the domain
    x_center_coords = test_grid.cell_coords_x()
    y_center_coords = test_grid.cell_coords_y()

    # choose a range of 10x10 coordinates within the domain to spot test, including upper and lower bounds
    x_test_coords = [0, *np.random.randint(test_grid.dimensions[0], size=8), test_grid.dimensions[0] - 1]
    y_test_coords = [0, *np.random.randint(test_grid.dimensions[1], size=8), test_grid.dimensions[1] - 1]

    # note: the coordinates generated by DomainGrid using the pyproj projection have
    # been observed to drift by up to **5 meters** from the coordinates
    # generated by MCIP, due to the differences between MCIPs projection
    # algorithm and ours.
    drift_tolerance = 5 # meters

    for y in y_test_coords:
        for x in x_test_coords:
            # compare the coordinates generated by our DomainGrid class with the
            # LON/LAT coords stored in the input domain file which was
            # generated by MCIP using the same grid parameters.
            expected_coords = (float(x_center_coords[x]), float(y_center_coords[y]))
            input_coords = (float(input_domain["LON"][0, y, x].values), float(input_domain["LAT"][0, y, x].values))
            projected_coords = test_grid.lonlat_to_xy(*input_coords)

            # check that our generated coordinates match the coords generated by MCIP
            np.testing.assert_allclose(projected_coords, expected_coords, atol=drift_tolerance)

def test_grid_valid_cell_coords(input_domain):
    test_grid = DomainGrid(input_domain)

    assert test_grid.valid_cell_coords(0, 0)
    assert test_grid.valid_cell_coords(test_grid.dimensions[0] - 1, test_grid.dimensions[1] - 1)
    assert test_grid.valid_cell_coords(test_grid.dimensions[0] - 1, 0)
    assert test_grid.valid_cell_coords(0, test_grid.dimensions[1] - 1)
    assert test_grid.valid_cell_coords(0, test_grid.dimensions[1] - 1)
    assert test_grid.valid_cell_coords(test_grid.dimensions[0] - 1, 0)

    assert not test_grid.valid_cell_coords(-1, 0)
    assert not test_grid.valid_cell_coords(0, -1)
    assert not test_grid.valid_cell_coords(0, test_grid.dimensions[1])
    assert not test_grid.valid_cell_coords(test_grid.dimensions[0], 0)
    assert not test_grid.valid_cell_coords(test_grid.dimensions[0], test_grid.dimensions[1])

def test_grid_lonlat_to_cell_index(input_domain):
    test_grid = DomainGrid(input_domain)

    # test some known locations inside aust10km
    assert test_grid.lonlat_to_cell_index(144.96, -37.78) == (328, 99, True) # Melbourne, VIC
    assert test_grid.lonlat_to_cell_index(151.18, -33.87) == (388, 135, True) # Sydney, NSW
