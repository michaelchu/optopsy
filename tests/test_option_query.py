from optopsy.option_queries import *
from .support.data_fixtures import *

pd.set_option('display.expand_frame_repr', False)


def test_calls(options_data):
    c = calls(options_data).option_type.unique()
    assert len(c) == 1
    assert c[0] == 'c'


def test_puts(options_data):
    p = puts(options_data).option_type.unique()
    assert len(p) == 1
    assert p[0] == 'p'


@pytest.mark.parametrize('option_type', [2, 'x', 'invalid', (3, 4)])
def test_invalid_option_type(options_data, option_type):
    with pytest.raises(ValueError):
        opt_type(options_data, option_type)


@pytest.mark.parametrize("option_type", [OptionType.CALL, OptionType.PUT])
def test_option_type(options_data, option_type):
    chain = opt_type(options_data, option_type).option_type.unique()
    assert len(chain) == 1
    assert chain[0] == option_type.value[0]


def test_underlying_price(options_data):
    chain = underlying_price(options_data)
    assert 359.225 == chain


@pytest.mark.parametrize(
    "value", [('strike', 357.5, [355, 360]),
              ('delta', 0.50, [0.55, -0.46, 0.51, -0.49]),
              ('delta', 0.34, [0.35, -0.31, 0.32, -0.33])]
)
def test_nearest_column(options_data, value):
    # here we test for mid-point, values returned should round up.
    chain = nearest(options_data, value[0], value[1])
    assert all(v in value[2] for v in chain[value[0]].unique().tolist())


@pytest.mark.parametrize(
    "value", [('test', 1), (1234, 1), ('option_symbol', 'test')])
def test_invalid_column_values(options_data, value):
    with pytest.raises(ValueError):
        nearest(options_data, value[0], value[1])


@pytest.mark.parametrize("value", [('strike', 350),
                                   ('delta', 0.50),
                                   ('gamma', 0.02),
                                   ('expiration', '1990-01-21'),
                                   ('quote_date', '01-01-1990'),
                                   ('dte', Period.SEVEN_WEEKS.value),
                                   ('dte', Period.ONE_DAY.value)])
def test_lte(options_data, value):
    values = lte(options_data, column=value[0], val=value[1])[value[0]]
    assert all(values <= value[1])


@pytest.mark.parametrize("value", [('strike', 350),
                                   ('delta', 0.50),
                                   ('gamma', 0.02),
                                   ('expiration', '1990-01-21'),
                                   ('quote_date', '01-01-1990'),
                                   ('dte', Period.SEVEN_WEEKS.value),
                                   ('dte', Period.ONE_DAY.value)])
def test_gte(options_data, value):
    values = gte(options_data, column=value[0], val=value[1])[value[0]]
    assert all(values >= value[1])


@pytest.mark.parametrize("value", [('strike', 350),
                                   ('delta', 0.50),
                                   ('gamma', 0.02),
                                   ('expiration', '1990-01-20'),
                                   ('quote_date', '01-01-1990'),
                                   ('dte', 18),
                                   ('dte', Period.ONE_DAY.value),
                                   ('option_symbol', '.SPX900120C00355000')])
def test_eq(options_data, value):
    values = eq(options_data, column=value[0], val=value[1])[value[0]]
    assert all(values == value[1])


@pytest.mark.parametrize("value", [('strike', 350),
                                   ('delta', 0.50),
                                   ('gamma', 0.02),
                                   ('expiration', '1990-01-21'),
                                   ('quote_date', '01-01-1990'),
                                   ('dte', Period.SEVEN_WEEKS.value),
                                   ('dte', Period.ONE_DAY.value)])
def test_lt(options_data, value):
    values = lt(options_data, column=value[0], val=value[1])[value[0]]
    assert all(values < value[1])


@pytest.mark.parametrize("value", [('strike', 350),
                                   ('delta', 0.50),
                                   ('gamma', 0.02),
                                   ('expiration', '1990-01-21'),
                                   ('quote_date', '01-01-1990'),
                                   ('dte', Period.SEVEN_WEEKS.value),
                                   ('dte', Period.ONE_DAY.value)])
def test_ne(options_data, value):
    values = ne(options_data, column=value[0], val=value[1])[value[0]]
    assert all(values != value[1])


@pytest.mark.parametrize("value", [('strike', 350, 370),
                                   ('delta', 0.5, -0.5),
                                   ('gamma', 0.04, 0.01),
                                   ('expiration', '1990-01-20', '1990-01-21'),
                                   ('quote_date', '01-01-1990', '01-04-1990'),
                                   ('dte', 1, 1.10),
                                   ('dte', Period.ONE_DAY.value,
                                    Period.ONE_WEEK.value)
                                   ])
def test_between_inclusive(options_data, value):
    values = between(
        options_data,
        column=value[0],
        start=value[1],
        end=value[2])[
        value[0]]
    assert all(values.between(value[1], value[2]))


@pytest.mark.parametrize("value", [('strike', 350, 370),
                                   ('delta', 0.5, -0.5),
                                   ('gamma', 0.04, 0.01),
                                   ('expiration', '1990-01-20', '1990-01-21'),
                                   ('quote_date', '01-01-1990', '01-04-1990'),
                                   ('dte', 1, 1.10),
                                   ('dte', Period.ONE_DAY.value,
                                    Period.ONE_WEEK.value)
                                   ])
def test_between(options_data, value):
    values = between(
        options_data,
        column=value[0],
        start=value[1],
        end=value[2],
        inclusive=False)[
        value[0]]
    assert all(values.between(value[1], value[2], inclusive=False))
