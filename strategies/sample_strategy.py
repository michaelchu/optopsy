from datetime import date

import pandas as pd

import optopsy as op

pd.options.display.width = None

vxx_struct = (
    ('symbol', 0),
    ('underlying_price', 1),
    ('option_symbol', 2),
    ('option_type', 3),
    ('expiration', 4),
    ('quote_date', 5),
    ('strike', 6),
    ('bid', 8),
    ('ask', 9),
    ('delta', 13),
    ('gamma', 14),
    ('theta', 15),
    ('vega', 16)
)


def run_strat():
    # fetch the option chains from our data source
    d = op.get('../data/VXX.csv',
               start=date(2016, 12, 1),
               end=date(2016, 12, 31),
               struct=vxx_struct,
               prompt=False
               )

    os = op.option_strategy.Vertical(option_type=op.OptionType.CALL, width=2)

    filters = [
        op.filters.EntrySpreadPrice(ideal=1.0, lower=0.9, upper=1.10),
        op.filters.EntryDaysToExpiration(ideal=47, lower=40, upper=52),
        op.filters.EntryDayOfWeek(ideal=4),
        op.filters.ExitDaysToExpiration(ideal=1)
    ]

    # construct our strategy with our defined filter rules
    strategy = op.Strategy('Weekly Verticals', os, filters)

    # Create an instance of Optopsy with strategy settings, with default initial capital of $10000
    backtest = op.Optopsy(strategy, d)

    # Run over everything once
    backtest.run(progress_bar=False)


if __name__ == '__main__':
    run_strat()
