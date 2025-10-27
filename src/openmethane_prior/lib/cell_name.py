
alphabet = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'

def encode_word_safe(v: int) -> str:
    """
    Encode an integer (like a grid coordinate) as a short string using
    url-safe characters.
    """
    remaining = v
    output = ''
    i = 1
    while i == 1 or remaining > 0:
        digit = remaining % (len(alphabet) ** i)
        if digit != 0:
            remaining -= digit
        remaining = remaining // (len(alphabet) ** i)
        i += 1
        output = f"{alphabet[digit]}{output}"
    return output

def decode_word_safe(v: str) -> int:
    """
    Decode a value encoded with encode_word_safe back to an integer.
    """
    output = 0
    for place in range(len(v), 0, -1):
        digit = v[place - 1]
        value = alphabet.index(digit)
        output += value * (len(alphabet) ** (len(v) - place))
    return output

def encode_grid_cell_name(grid_name: str, x: int, y: int, separator: str = '.') -> str:
    """
    Turn the three components that identify a grid cell (grid, x and y) into a
    unique, URL-safe string.
    """
    return separator.join([grid_name, encode_word_safe(x), encode_word_safe(y)])

def decode_grid_cell_name(grid_cell_name: str, separator: str = '.') -> dict:
    """

    :param grid_cell_name:
    :param separator:
    :return:
    """
    grid_name, enc_x, enc_y = grid_cell_name.split(separator)
    return {
        'grid': grid_name,
        'x': decode_word_safe(enc_x),
        'y': decode_word_safe(enc_y)
    }
