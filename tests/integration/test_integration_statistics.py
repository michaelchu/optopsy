from datetime import datetime
import os
from optopsy.option_strategies import long_call, short_call, long_call_spread
from optopsy.data import get

CURRENT_FILE = os.path.abspath(os.path.dirname(__file__))
TEST_FILE_PATH_FULL = os.path.join(
    CURRENT_FILE, "../test_data/test_options_data_full.csv"
)

HOD_STRUCT = (
    ("underlying_symbol", 0),
    ("underlying_price", 1),
    ("option_type", 5),
    ("expiration", 6),
    ("quote_date", 7),
    ("strike", 8),
    ("bid", 10),
    ("ask", 11),
    ("delta", 15),
    ("gamma", 16),
    ("theta", 17),
    ("vega", 18),
)

DATA = get(TEST_FILE_PATH_FULL, HOD_STRUCT, prompt=False)


def test_avg_profit_long_singles():
    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 7,
        "leg1_delta": 0.50,
        "contract_size": 1,
        "expr_type": "SPXW",
    }
    spread = long_call(DATA, filters)
    result = spread.avg_profit()
    print(spread)
    assert result == 0


def test_avg_loss_long_singles():
    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 7,
        "leg1_delta": 0.50,
        "contract_size": 1,
        "expr_type": "SPXW",
    }
    spread = long_call(DATA, filters)
    result = spread.avg_loss()
    print(result)
    assert result == 1495


def test_avg_profit_short_singles():
    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 7,
        "leg1_delta": 0.50,
        "contract_size": 1,
        "expr_type": "SPXW",
    }
    spread = short_call(DATA, filters)
    result = spread.avg_profit()
    print(spread)
    assert result == 1057.5


def test_avg_loss_short_singles():
    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 7,
        "leg1_delta": 0.50,
        "contract_size": 1,
        "expr_type": "SPXW",
    }
    spread = short_call(DATA, filters)
    result = spread.avg_loss()
    print(result)
    assert result == 0


def test_avg_profit_verticals():
    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 7,
        "leg1_delta": 0.50,
        "leg2_delta": 0.30,
        "contract_size": 1,
        "expr_type": "SPXW",
    }
    spread = long_call_spread(DATA, filters)
    result = spread.avg_profit()
    print(spread)
    assert result == 0


def test_avg_loss_verticals():
    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 7,
        "leg1_delta": 0.50,
        "leg2_delta": 0.30,
        "contract_size": 1,
        "expr_type": "SPXW",
    }
    spread = long_call_spread(DATA, filters)
    result = spread.avg_loss()
    print(result)
    assert result == 720


def test_win_rate_singles():
    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 31,
        "leg1_delta": 0.50,
        "contract_size": 1,
        "expr_type": "SPXW",
    }
    spread = long_call(DATA, filters)
    result = spread.calc_win_rate()
    print(spread)
    assert result == 0.5


def test_win_rate_verticals():
    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 31,
        "leg1_delta": 0.50,
        "leg2_delta": 0.30,
        "contract_size": 1,
        "expr_type": "SPXW",
    }
    spread = long_call_spread(DATA, filters)
    result = spread.calc_win_rate()
    print(spread)
    assert result == 0


def test_trade_singles():
    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 31,
        "leg1_delta": 0.50,
        "contract_size": 1,
        "expr_type": "SPXW",
    }
    spread = long_call(DATA, filters)
    result = spread.trades()


def test_trade_verticals():
    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 31,
        "leg1_delta": 0.50,
        "leg2_delta": 0.30,
        "contract_size": 1,
        "expr_type": "SPXW",
    }
    spread = long_call_spread(DATA, filters)
    result = spread.trades()
