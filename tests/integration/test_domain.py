import numpy

def test_domain_attributes(input_domain):
    assert type(input_domain.attrs["domain_name"]) == str
    assert type(input_domain.attrs["domain_version"]) == str
    assert type(input_domain.attrs["domain_slug"]) == str
    assert type(input_domain.attrs["title"]) == str
    assert type(input_domain.attrs["history"]) == str
    assert type(input_domain.attrs["openmethane_prior_version"]) == str

    assert input_domain.attrs["Conventions"] == "CF-1.12"

    assert type(input_domain.attrs['DX']) == numpy.float32
    assert input_domain.attrs['DX'] > 0
    assert type(input_domain.attrs['DX']) == numpy.float32
    assert input_domain.attrs['DY'] > 0
    assert type(input_domain.attrs["XCELL"]) == numpy.float64
    assert input_domain.attrs['XCELL'] > 0
    assert type(input_domain.attrs["YCELL"]) == numpy.float64
    assert input_domain.attrs['YCELL'] > 0
    assert type(input_domain.attrs["XORIG"]) == numpy.float64
    assert type(input_domain.attrs["YORIG"]) == numpy.float64
