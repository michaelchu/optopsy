import optopsy as op
import os
from datetime import datetime

# absolute file path to our input file
CURRENT_FILE = os.path.abspath(os.path.dirname(__file__))
FILE = os.path.join(CURRENT_FILE, 'data', 'SPX_2016.csv')

# Here we define the struct to match the format of our csv file
# the struct indices are 0-indexed where first column of the csv file
# is mapped to 0
SPX_FILE_STRUCT = (
    ('underlying_symbol', 0),
    ('underlying_price', 1),
    ('option_symbol', 3),
    ('option_type', 5),
    ('expiration', 6),
    ('quote_date', 7),
    ('strike', 8),
    ('bid', 10),
    ('ask', 11),
    ('delta', 15),
    ('gamma', 16),
    ('theta', 17),
    ('vega', 18)
)


def run_strategy():

    # provide the absolute file path and data struct to be used.
    data = op.get(FILE, SPX_FILE_STRUCT, prompt=False)

    # define the entry and exit filters to use for this strategy, full list of
    # filters is listed in the documentation (WIP).
    filters = {
        'entry_dte': (27, 30, 31),
        'leg1_delta': 0.30,
        'leg2_delta': 0.50,
        'contract_size': 10
    }

    # set the start and end dates for the backtest, the dates are inclusive
    start = datetime(2016, 1, 1)
    end = datetime(2016, 12, 31)

    # create the option spread that matches the entry filters
    trades = op.strategies.short_call_spread(data, start, end, filters)
    trades.to_csv('./strategies/results/trades.csv')

    # call the run method with our data, option spreads and filters to run the backtest
    backtest = op.run(data, trades, filters)

    # backtest will return a tuple with the profit amount and a dataframe
    # containing the backtest results(the return format may be subject to change)
    backtest[1].to_csv('./strategies/results/results.csv')
    print("Total Profit: %s" % backtest[0])


if __name__ == '__main__':
    run_strategy()
