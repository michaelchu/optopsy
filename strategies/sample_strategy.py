import datetime
import pandas as pd

# import the backtest library
import optopsy as op

pd.options.display.width = None

# define the structure of our data, sourced from 'www.historicaloptiondata.com'
data_struct = (
    {'symbol', 0},
    {'underlying_price', 1},
    {'option_symbol', 3},
    {'option_type', 4},
    {'expiration', 5},
    {'quote_date', 6},
    {'strike', 7},
    {'bid', 9},
    {'ask', 10},
    {'volume', 11},
    {'oi', 12},
    {'iv', 14},
    {'delta', 17},
    {'gamma', 18},
    {'theta', 19},
    {'vega', 20}
)

strategy = op.Strategy('Sample Strategy', [
    op.algos.DataFeed('../data/A.csv', data_struct),
    op.algos.DateRange(datetime.datetime(2016, 1, 1), datetime.datetime(2016, 12, 1))
])

# Create a strategy, each strategy should include a 'name', 'strategy_legs', 'date_range'.
strategy = {
    'name': 'Sample Strategy',
    'date_range': {
        'start': datetime.datetime(2016, 1, 1),
        'end': datetime.datetime(2016, 12, 1)
    },
    'components': (
        {
            'option_strategy': 'bull_put_spread',
            'data_path': '../data/A.csv',
            'data_struct': data_struct,
            'filters': (
                {
                    'name': 'entry_abs_delta',
                    'ideal': (0.4, 0.5, 0.6,),  # a tuple can be used to define multiple 'ideal' values to optimize with
                    'min_delta': 0.05,
                    'max_delta': 0.05
                },
                {
                    'name': 'entry_spread_price',
                    'ideal': (0.75, 1, 1.25,),
                    'min_delta': 0.05,
                    'max_delta': 0.05
                },
                {
                    'name': 'entry_days_to_expiration',
                    'ideal': 40,
                    'min_delta': 10,
                    'max_delta': 20
                },
                {
                    'name': 'entry_day_of_week',
                    'ideal': 4
                },
                {
                    'name': 'exit_hold_days',
                    'ideal': range(5, 10)  # an iterable can be used to define multiple 'ideal' values to optimize with
                }
            )
        },
        {
            'option_strategy': 'long_put',
            'data_path': '../data/B.csv',
            'data_struct': data_struct,
            'filters': (
                {'filter': 'entry_abs_delta', 'ideal': (0.4, 0.5, 0.6,), 'min_delta': 0.05, 'max_delta': 0.05},
                {'filter': 'entry_spread_price', 'ideal': (0.75, 1, 1.25,), 'min_delta': 0.05,
                 'max_delta': 0.05},
                {'filter': 'entry_days_to_expiration', 'ideal': 40, 'min_delta': 10, 'max_delta': 20},
                {'filter': 'entry_day_of_week', 'ideal': 4},
                {'filter': 'exit_hold_days', 'ideal': range(5, 10)}
            )
        }
    )
}


def run_strat():
    # Create an instance of Optopsy with strategy settings
    optopsy = op.Optopsy(strategy)

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
