import datetime

# import the backtest library
import optopsy as op
import optopsy.data as feeds
import optopsy.strategy as strategies

# List of test data sets to use
test_file_paths = ['../data/A.csv']

# Set the data struct for the test input file,
# should correspond to the order of files in test_file_paths
test_file_structs = [(
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
)]

# Define a basic strategy to test with, can be overridden with actual test strategy in sub-classes
test_filters = (
    {'strategy': 'long_call_spread'},
    {'entry': 'date_range', 'start': datetime.datetime(2016, 1, 1), 'end': datetime.datetime(2016, 12, 1)},
    {'entry': 'abs_delta', 'ideal': (0.4, 0.5, 0.6,), 'min_delta': 0.05, 'max_delta': 0.05},
    {'entry': 'spread_price', 'ideal': (0.75, 1, 1.25,), 'min_delta': 0.05, 'max_delta': 0.05},
    {'entry': 'days_to_expiration', 'ideal': 40, 'min_delta': 10, 'max_delta': 20},
    {'entry': 'day_of_week', 'ideal': 4},
    {'exit': 'exit_hold_days', 'ideal': (5, 6, 7,)}
)


def run_test(data, struct, strategy):
    """
    Define a base test function that will take care of creating an Optopsy
    instance to test with.

    :param data: Path to test data file to use
    :param struct: Default data struct to use
    :param strategy: Default strategy to run tests with
    :return:
    """
    # Create an instance of Optopsy to test with
    optopsy = op.Optopsy()

    # Add the strategy for Optopsy to run
    optopsy.add_strategy(strategy)

    # Tell which data feed config for Optopsy to use
    optopsy.add_data(feeds.PandasFeed(file_path=data, struct=struct))

    # Run over everything
    optopsy.run()


class TestStrategy(strategies.Strategy):

    def __init__(self, filters):
        super(TestStrategy, filters).__init__()

    def stop(self):
        """
        Here we override standard stop logic and check our strategy specific assertions.
        :return:
        """
        pass
