import datetime
import pandas as pd

# import the backtest library
import optopsy as op
import optopsy.feeds as opfeeds

pd.options.display.width = None


class CboePandasFeed(opfeeds.PandasFeed):
    # define the structure of the datafeed, sourced from 'https://www.discountoptiondata.com/'
    params = (
        ('symbol', 0),
        ('underlying_price', 1),
        ('option_symbol', 3),
        ('option_type', 4),
        ('expiration', 5),
        ('quote_date', 6),
        ('strike', 7),
        ('bid', 9),
        ('ask', 10),
        ('volume', 11),
        ('oi', 12),
        ('iv', 14),
        ('delta', 17),
        ('gamma', 18),
        ('theta', 19),
        ('vega', 20)
    )


def run_strat():
    # Create an instance of Optopsy with config settings
    optopsy = op.Optopsy()

    # Create a strategy
    strategy = (
        {'strategy': 'long_call_spread'},
        {'entry': 'date_range', 'start': datetime.datetime(2016, 1, 1), 'end': datetime.datetime(2016, 12, 1)},
        {'entry': 'abs_delta', 'ideal': (0.4, 0.5, 0.6,), 'min_delta': 0.05, 'max_delta': 0.05},
        {'entry': 'spread_price', 'ideal': (0.75, 1, 1.25,), 'min_delta': 0.05, 'max_delta': 0.05},
        {'entry': 'days_to_expiration', 'ideal': 40, 'min_delta': 10, 'max_delta': 20},
        {'entry': 'day_of_week', 'ideal': 4},
        {'exit': 'exit_hold_days', 'ideal': (5, 6, 7,)}
    )

    # Add the strategy for Optopsy to run
    optopsy.add_strategy(strategy)

    # Tell which data feed config for Optopsy to use
    optopsy.add_data(CboePandasFeed(file_path='../data/A.csv'))

    # Set our desired cash start
    optopsy.broker.set_cash(100000)

    # Print out the starting conditions
    print('Starting Portfolio Value: %.2f' % optopsy.broker.get_value())

    # Run over everything
    optopsy.run()

    # Print out the final result
    print('Final Portfolio Value: %.2f' % optopsy.broker.get_value())


if __name__ == '__main__':
    run_strat()
