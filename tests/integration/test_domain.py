import numpy

def test_domain_attributes(input_domain):
    assert type(input_domain.attrs["TRUELAT1"]) == numpy.float32
    assert type(input_domain.attrs["TRUELAT2"]) == numpy.float32
    assert type(input_domain.attrs["MOAD_CEN_LAT"]) == numpy.float32
    assert type(input_domain.attrs["STAND_LON"]) == numpy.float32
    assert type(input_domain.attrs["XCENT"]) == numpy.float64
    assert type(input_domain.attrs["YCENT"]) == numpy.float64

    assert type(input_domain.attrs['DX']) == numpy.float32
    assert input_domain.attrs['DX'] > 0
    assert type(input_domain.attrs['DX']) == numpy.float32
    assert input_domain.attrs['DY'] > 0
    
# Check domain matches projection used in calculations
def test_domain_projection(config, input_domain):
    assert f"+lat_1={float(input_domain.attrs['TRUELAT1'])} " in str(config.crs)
    assert f"+lat_2={float(input_domain.attrs['TRUELAT2'])} " in str(config.crs)
    assert f"+lat_0={float(input_domain.attrs['MOAD_CEN_LAT'])} " in str(config.crs)
    assert f"+lon_0={float(input_domain.attrs['STAND_LON'])} " in str(config.crs)

    