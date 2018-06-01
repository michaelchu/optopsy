import datetime
import os.path
import sys
# import the backtest library
import optopsy as op

if __name__ == '__main__':
    # Create an instance of Optopsy
    optopsy = op.Optopsy()

    # Add a strategy
    params = (
        {'strategy': 'long_call_spread'},
        {'entry': 'date_range', 'start': datetime.datetime(2016, 1, 1), 'end': datetime.datetime(2016, 12, 1)},
        {'entry': 'abs_delta', 'ideal': (0.4, 0.5, 0.6,), 'min_delta': 0.05, 'max_delta': 0.05},
        {'entry': 'spread_price', 'ideal': (0.75, 1, 1.25,), 'min_delta': 0.05, 'max_delta': 0.05},
        {'entry': 'days_to_expiration', 'ideal': 40, 'min_delta': 10, 'max_delta': 20},
        {'entry': 'day_of_week', 'ideal': 4},
        {'exit': 'exit_hold_days', 'ideal': (5, 6, 7,)}
    )

    # Add optimization
    optopsy.add_strategy(params)

    # Data are in a sub-folder of the strategies folder. Find where this script is run,
    # and look for the sub-folder. This script can reside anywhere.
    currpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    datapath = os.path.join(currpath, 'data/vix.csv')

    # Create a Data Feed
    data = op.feeds.CboeCSVFeed(dataname=datapath)

    # Add the Data Feed to Optopsy
    optopsy.add_data(data)

    # Set our desired cash start
    optopsy.broker.setcash(100000.0)

    # Print out the starting conditions
    print('Starting Portfolio Value: %.2f' % optopsy.broker.getvalue())

    # Run over everything
    optopsy.run()

    # Print out the final result
    print('Final Portfolio Value: %.2f' % optopsy.broker.getvalue())
