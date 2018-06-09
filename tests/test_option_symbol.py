import pytest

import optopsy as op


@pytest.mark.parametrize(['symbol', 'option_type', 'expiration', 'strike', 'option_symbol'], [
    ('A', 'p', '2016-01-15', 20.0, 'A160115P00020000'),
    ('a', 'P', '2017-01-20', 27.5, 'A170120P00027500'),
    ('VXX', 'CALL', '12/02/2016', 20, 'VXX161202C00020000'),
    ('vxx', 'PUT', '12/02/2016', 20, 'VXX161202P00020000'),
    ('^SPX', 'c', '1/8/2016 0:00:00', 700.0, 'SPX160108C00700000'),
    ('^spx', 'C', '1/8/2016 0:00:00', 700.0, 'SPX160108C00700000')
])
def test_gen_opt_symbol(symbol, option_type, expiration, strike, option_symbol):
    actual_sym = op.helpers.generate_symbol(symbol, expiration, strike, option_type)
    assert option_symbol == actual_sym


@pytest.mark.parametrize(['symbol', 'option_type', 'expiration', 'strike'], [
    ('A', 'camel', '2016-01-15', 20.0,),
    ('A', 'pull', '2017-01-20', 27.5),
    ('VXX', 'case_1', '12/02/2016', 20),
    ('^SPX', 'c_AVC', '1/8/2016 0:00:00', 700.0)
])
def test_gen_opt_invalid_symbol(symbol, option_type, expiration, strike):
    with pytest.raises(ValueError):
        op.helpers.generate_symbol(symbol, expiration, strike, option_type)
