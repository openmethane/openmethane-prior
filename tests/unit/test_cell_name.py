
from openmethane_prior.cell_name import decode_grid_cell_name, encode_grid_cell_name, encode_word_safe, decode_word_safe

expected_names = {
    "A.0.0": ["A", 0, 0],
    "A.1.1": ["A", 1, 1],
    "A.0.1": ["A", 0, 1],
    "A.1.0": ["A", 1, 0],
    "A.Y.Y": ["A", 30, 30],
    "A.Z.Z": ["A", 31, 31], # last character in safe alphabet
    "A.10.10": ["A", 32, 32], # first 2-digit encoding
    "A.11.11": ["A", 33, 33],
    "10.A8.33": ["10", 328, 99], # Melbourne in aust10km
    "10.C4.47": ["10", 388, 135], # Sydney in aust10km
}

def test_encode_grid_cell_name():
    for expected_cell_name in expected_names.keys():
        grid_slug, x, y = expected_names[expected_cell_name]
        assert encode_grid_cell_name(grid_slug, x, y) == expected_cell_name

def test_encode_grid_cell_name_separator():
    # default separator is "."
    assert encode_grid_cell_name("A", 0, 0) == "A.0.0"

    # other separators can be specified
    assert encode_grid_cell_name("A", 0, 0, "-") == "A-0-0"
    assert encode_grid_cell_name("A", 0, 0, "") == "A00"

def test_decode_grid_cell_name():
    for expected_cell_name in expected_names.keys():
        grid_slug, x, y = expected_names[expected_cell_name]
        assert decode_grid_cell_name(expected_cell_name) == { "grid": grid_slug, "x": x, "y": y }

def test_decode_grid_cell_name_separator():
    # default separator is "."
    assert decode_grid_cell_name("A.0.0") == { "grid": "A", "x": 0, "y": 0 }

    # other separators can be specified
    assert decode_grid_cell_name("A-0-0", "-") == { "grid": "A", "x": 0, "y": 0 }
    assert decode_grid_cell_name("A%0%0", "%") == { "grid": "A", "x": 0, "y": 0 }

def test_encode_decode_round_trip():
    for integer in range(0, 1000):
        encoded = encode_word_safe(integer)
        assert decode_word_safe(encoded) == integer
