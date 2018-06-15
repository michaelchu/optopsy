import pytest
import optopsy as op


def test_invalid_opt_strategy():
    with pytest.raises(ValueError):
        op.Strategy('test', op.Filter(), 'list of filters')


def test_init_strategy_with_filters():
    filters = [
        op.filters.EntrySpreadPrice(ideal=1.0, lower=0.9, upper=1.10),
        op.filters.ExitDaysToExpiration(ideal=1)
    ]

    dummy_strategy = op.OptionStrategy(name="Dummy Strategy")
    op.Strategy('Weekly Verticals', dummy_strategy, filters)


def test_strategy_with_invalid_filters():
    filters = (
        op.filters.EntryDaysToExpiration(ideal=47, lower=40, upper=52)
    )

    dummy_strategy = op.OptionStrategy(name="Dummy Strategy")
    with pytest.raises(ValueError):
        op.Strategy('Weekly Verticals', dummy_strategy, filters)
