import pytest

from optopsy.enums import OptionType
# import optopsy as op
from optopsy.enums import Period
from optopsy.option_query import OptionQuery
from optopsy.option_strategy import OptionStrategy
from.data_fixtures import one_day_data


def test_calls(one_day_data):
    calls = OptionQuery.calls(one_day_data).option_type.unique()
    assert len(calls) == 1
    assert calls[0] == 'c'


def test_puts(one_day_data):
    puts = OptionQuery.puts(one_day_data).option_type.unique()
    assert len(puts) == 1
    assert puts[0] == 'p'


@pytest.mark.parametrize('option_type', [2, 'x', 'invalid', (3, 4)])
def test_invalid_option_type(one_day_data, option_type):
    with pytest.raises(ValueError):
        OptionQuery.opt_type(one_day_data, option_type)


@pytest.mark.parametrize("option_type", [OptionType.CALL, OptionType.PUT])
def test_option_type(one_day_data, option_type):
    chain = OptionQuery.opt_type(one_day_data, option_type).option_type.unique()
    assert len(chain) == 1
    assert chain[0] == option_type.value[0]


def test_underlying_price(one_day_data):
    chain = OptionQuery().underlying_price(one_day_data)
    assert chain == 40.55


@pytest.mark.parametrize("value", [('strike', 20.5, 21), ('delta', 0.0, 0.02)])
def test_nearest_column_round_up(one_day_data, value):
    # here we test for mid-point, values returned should round up.
    chain = OptionQuery.nearest(one_day_data, value[0], value[1])
    values = chain[value[0]].unique()

    assert len(values) == 1
    assert values[0] == value[2]


@pytest.mark.parametrize("value", [('strike', 20.5, 20), ('delta', 0.0, -0.02)])
def test_nearest_column_round_down(one_day_data, value):
    # here we test for mid-point, values returned should round down.
    chain = OptionQuery.nearest(one_day_data, value[0], value[1], 'rounddown')
    values = chain[value[0]].unique()

    assert len(values) == 1
    assert values[0] == value[2]


@pytest.mark.parametrize(
    "value", [('test', 1), (1234, 1), ('option_symbol', 'test')])
def test_invalid_column_values(one_day_data, value):
    with pytest.raises(ValueError):
        OptionQuery._check_inputs(one_day_data, value[0], value[1])


@pytest.mark.parametrize("value", [('strike_1', 30),
                                   ('strike_1', 0),
                                   ('strike_1', 55),
                                   ('delta', 0),
                                   ('delta', 0.50),
                                   ('delta', 1),
                                   ('dte', Period.DAY.value),
                                   ('dte', Period.TWO_WEEKS.value),
                                   ('dte', Period.SEVEN_WEEKS.value)])
def test_lte(one_day_data, value):
    values = (
        one_day_data
        .pipe(OptionStrategy.single, OptionType.CALL)
        .pipe(OptionQuery.lte, column=value[0], val=value[1])
    )[value[0]].unique()

    assert all(v <= value[1] for v in values)


@pytest.mark.parametrize("value", [('strike_1', 30),
                                   ('strike_1', 0),
                                   ('strike_1', 55),
                                   ('delta', 0),
                                   ('delta', 0.50),
                                   ('delta', 1),
                                   ('dte', Period.DAY.value),
                                   ('dte', Period.TWO_WEEKS.value),
                                   ('dte', Period.SEVEN_WEEKS.value)])
def test_gte(one_day_data, value):
    values = (
        one_day_data
        .pipe(OptionStrategy.single, OptionType.CALL)
        .pipe(OptionQuery.gte, column=value[0], val=value[1])
    )[value[0]].unique()

    assert all(v >= value[1] for v in values)


@pytest.mark.parametrize("value", [('strike_1', 30),
                                   ('strike_1', 0),
                                   ('strike_1', 55),
                                   ('delta', 0),
                                   ('delta', 0.54),
                                   ('delta', 1),
                                   ('dte', Period.DAY.value),
                                   ('dte', Period.TWO_WEEKS.value),
                                   ('dte', Period.SEVEN_WEEKS.value)])
def test_eq(one_day_data, value):
    values = (
        one_day_data
        .pipe(OptionStrategy.single, OptionType.CALL)
        .pipe(OptionQuery.eq, column=value[0], val=value[1])
    )[value[0]].unique()

    assert all(v == value[1] for v in values)


@pytest.mark.parametrize("value", [('strike_1', 30),
                                   ('strike_1', 0),
                                   ('strike_1', 55),
                                   ('delta', 0),
                                   ('delta', 0.54),
                                   ('delta', 1),
                                   ('dte', Period.DAY.value),
                                   ('dte', Period.TWO_WEEKS.value),
                                   ('dte', Period.SEVEN_WEEKS.value)])
def test_lt(one_day_data, value):
    values = (
        one_day_data
        .pipe(OptionStrategy.single, OptionType.CALL)
        .pipe(OptionQuery.lt, column=value[0], val=value[1])
    )[value[0]].unique()

    assert all(v < value[1] for v in values)


@pytest.mark.parametrize("value", [('strike_1', 30),
                                   ('strike_1', 0),
                                   ('strike_1', 55),
                                   ('delta', 0),
                                   ('delta', 0.54),
                                   ('delta', 1),
                                   ('dte', Period.DAY.value),
                                   ('dte', Period.TWO_WEEKS.value),
                                   ('dte', Period.SEVEN_WEEKS.value)])
def test_ne(one_day_data, value):
    values = (
        one_day_data
        .pipe(OptionStrategy.single, OptionType.CALL)
        .pipe(OptionQuery.ne, column=value[0], val=value[1])
    )[value[0]].unique()
    assert all(v != value[1] for v in values)


@pytest.mark.parametrize("value", [('strike_1', 30, 35),
                                   ('strike_1', 0, 20),
                                   ('strike_1', 55, 70),
                                   ('delta', 0.4, 0.6),
                                   ('delta', 0, 0.10),
                                   ('delta', 1, 1.10),
                                   ('dte', Period.DAY.value, Period.ONE_WEEK.value),
                                   ('dte', Period.TWO_WEEKS.value, Period.THREE_WEEKS.value)
                                   ])
def test_between(one_day_data, value):
    values = (
        one_day_data
        .pipe(OptionStrategy.single,OptionType.CALL)
        .pipe(OptionQuery.between, column=value[0], start=value[1], end=value[2]))[value[0]].unique()

    assert all(value[1] <= v <= value[2] for v in values)
