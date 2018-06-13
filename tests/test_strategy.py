import pytest

import optopsy as op


def test_init_strategy_with_filters():
    entry_filters = [
        op.filters.EntrySpreadPrice(ideal=1.0, l_limit=0.9, u_limit=1.10),
        op.filters.EntryDaysToExpiration(ideal=47, l_limit=40, u_limit=52),
        op.filters.EntryDayOfWeek(ideal=4)
    ]

    exit_filters = [
        op.filters.ExitDaysToExpiration(ideal=1)
    ]

    dummy_strategy = op.Option(name="Dummy Strategy")
    op.Strategy('Weekly Verticals', dummy_strategy, entry_filters, exit_filters)


def test_strategy_with_invalid_entry_filters():
    entry_filters = [
        op.filters.EntrySpreadPrice(ideal=1.0, l_limit=0.9, u_limit=1.10),
        op.filters.EntryDaysToExpiration(ideal=47, l_limit=40, u_limit=52),
        op.filters.EntryDayOfWeek(ideal=4),
        op.filters.ExitDaysToExpiration(ideal=4)
    ]

    exit_filters = [
        op.filters.ExitDaysToExpiration(ideal=1)
    ]

    dummy_strategy = op.Option(name="Dummy Strategy")

    with pytest.raises(ValueError):
        op.Strategy('Weekly Verticals', dummy_strategy, entry_filters, exit_filters)


def test_strategy_with_invalid_exit_filters():
    entry_filters = [
        op.filters.EntryDaysToExpiration(ideal=47, l_limit=40, u_limit=52),
        op.filters.EntryDayOfWeek(ideal=4),
    ]

    exit_filters = [
        op.filters.EntrySpreadPrice(ideal=1.0, l_limit=0.9, u_limit=1.10),
        op.filters.ExitDaysToExpiration(ideal=1)
    ]

    dummy_strategy = op.Option(name="Dummy Strategy")

    with pytest.raises(ValueError):
        op.Strategy('Weekly Verticals', dummy_strategy, entry_filters, exit_filters)
