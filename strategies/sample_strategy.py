import optopsy as op
import os
from datetime import datetime

CURRENT_FILE = os.path.abspath(os.path.dirname(__file__))
FILE = os.path.join(CURRENT_FILE, 'vxx_2016.csv')

FILE_STRUCT = (
    ('option_symbol', 0),
    ('underlying_symbol', 1),
    ('quote_date', 2),
    ('expiration', 4),
    ('strike', 5),
    ('option_type', 6),
    ('bid', 13),
    ('ask', 15),
    ('underlying_price', 16),
    ('delta', 18),
    ('gamma', 19),
    ('theta', 20),
    ('vega', 21)
)


def run_strategy():
    data = op.get(FILE, FILE_STRUCT, prompt=False)

    filters = {
        'entry_dte': 31,
        'leg1_delta': 0.30,
        'leg2_delta': 0.50,
        'contract_size': 10
    }

    start = datetime(2016, 1, 1)
    end = datetime(2016, 12, 31)

    trades = op.strategies.short_call_spread(data, start, end, filters)

    backtest = op.run(data, trades, filters)
    print("Total Profit: %s" % backtest[0])


if __name__ == '__main__':
    run_strategy()
