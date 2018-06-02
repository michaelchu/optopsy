import datetime
import os.path
import settings
# import the backtest library
import optopsy as op

if __name__ == '__main__':

    config = settings.from_file(
        settings.DEFAULT_CONFIG_FILENAME, testing=True
    )

    # Create an instance of Optopsy
    optopsy = op.Optopsy(config)

    # Add a strategy
    strategy = (
        {'strategy': 'long_call_spread'},
        {'entry': 'date_range', 'start': datetime.datetime(2016, 1, 1), 'end': datetime.datetime(2016, 12, 1)},
        {'entry': 'abs_delta', 'ideal': (0.4, 0.5, 0.6,), 'min_delta': 0.05, 'max_delta': 0.05},
        {'entry': 'spread_price', 'ideal': (0.75, 1, 1.25,), 'min_delta': 0.05, 'max_delta': 0.05},
        {'entry': 'days_to_expiration', 'ideal': 40, 'min_delta': 10, 'max_delta': 20},
        {'entry': 'day_of_week', 'ideal': 4},
        {'exit': 'exit_hold_days', 'ideal': (5, 6, 7,)}
    )

    # Add optimization
    optopsy.add_strategy(strategy)

    # Data are in a sub-folder of the strategies folder. Find where this script is run,
    # and look for the sub-folder. This script can reside anywhere.
    # current_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    # file_path = os.path.join(settings.ROOT_DIR, 'tests', 'data', 'VIX.csv')

    # Create a Data Feed
    data = op.feeds.CboeCSVFeed()

    # Add the Data Feed to Optopsy
    optopsy.add_data(data)

    # Set our desired cash start
    optopsy.broker.set_cash(100000.0)

    # Print out the starting conditions
    print('Starting Portfolio Value: %.2f' % optopsy.broker.get_value())

    # Run over everything
    optopsy.run()

    # Print out the final result
    print('Final Portfolio Value: %.2f' % optopsy.broker.get_value())
