import optopsy as op
import os
from datetime import datetime

CURRENT_FILE = os.path.abspath(os.path.dirname(__file__))
FILE = os.path.join(CURRENT_FILE, 'data', 'SPX_2016.csv')


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
    data = op.get(FILE, SPX_FILE_STRUCT, prompt=False)

    filters = {
        'entry_dte': (27, 30, 31),
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
