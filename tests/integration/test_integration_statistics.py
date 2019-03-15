# from datetime import datetime
# import os
# import optopsy as op
# import pandas as pd

# data = pd.read_csv(filepath(), parse_dates=True, infer_datetime_format=True)


# def filepath():
#     curr_file = os.path.abspath(os.path.dirname(__file__))
#     return os.path.join(curr_file, "../test_data/data_full.csv")


# def test_avg_profit_long_singles():
#     filters = {
#         "start_date": datetime(2018, 1, 1),
#         "end_date": datetime(2018, 2, 28),
#         "entry_dte": 7,
#         "leg1_delta": 0.50,
#         "contract_size": 1,
#         "expr_type": "SPXW",
#     }
#     spread = long_call(DATA, filters)
#     result = spread.avg_profit()
#     print(spread)
#     assert result == 0


# def test_avg_loss_long_singles():
#     filters = {
#         "start_date": datetime(2018, 1, 1),
#         "end_date": datetime(2018, 2, 28),
#         "entry_dte": 7,
#         "leg1_delta": 0.50,
#         "contract_size": 1,
#         "expr_type": "SPXW",
#     }
#     spread = long_call(DATA, filters)
#     result = spread.avg_loss()
#     print(result)
#     assert result == 1495


# def test_avg_profit_short_singles():
#     filters = {
#         "start_date": datetime(2018, 1, 1),
#         "end_date": datetime(2018, 2, 28),
#         "entry_dte": 7,
#         "leg1_delta": 0.50,
#         "contract_size": 1,
#         "expr_type": "SPXW",
#     }
#     spread = short_call(DATA, filters)
#     result = spread.avg_profit()
#     print(spread)
#     assert result == 1057.5


# def test_avg_loss_short_singles():
#     filters = {
#         "start_date": datetime(2018, 1, 1),
#         "end_date": datetime(2018, 2, 28),
#         "entry_dte": 7,
#         "leg1_delta": 0.50,
#         "contract_size": 1,
#         "expr_type": "SPXW",
#     }
#     spread = short_call(DATA, filters)
#     result = spread.avg_loss()
#     print(result)
#     assert result == 0


# def test_avg_profit_verticals():
#     filters = {
#         "start_date": datetime(2018, 1, 1),
#         "end_date": datetime(2018, 2, 28),
#         "entry_dte": 7,
#         "leg1_delta": 0.50,
#         "leg2_delta": 0.30,
#         "contract_size": 1,
#         "expr_type": "SPXW",
#     }
#     spread = long_call_spread(DATA, filters)
#     result = spread.avg_profit()
#     print(spread)
#     assert result == 0


# def test_avg_loss_verticals():
#     filters = {
#         "start_date": datetime(2018, 1, 1),
#         "end_date": datetime(2018, 2, 28),
#         "entry_dte": 7,
#         "leg1_delta": 0.50,
#         "leg2_delta": 0.30,
#         "contract_size": 1,
#         "expr_type": "SPXW",
#     }
#     spread = long_call_spread(DATA, filters)
#     result = spread.avg_loss()
#     print(result)
#     assert result == 720


# def test_win_rate_singles():
#     filters = {
#         "start_date": datetime(2018, 1, 1),
#         "end_date": datetime(2018, 2, 28),
#         "entry_dte": 31,
#         "leg1_delta": 0.50,
#         "contract_size": 1,
#         "expr_type": "SPXW",
#     }
#     spread = long_call(DATA, filters)
#     result = spread.calc_win_rate()
#     print(spread)
#     assert result == 0.5


# def test_win_rate_verticals():
#     filters = {
#         "start_date": datetime(2018, 1, 1),
#         "end_date": datetime(2018, 2, 28),
#         "entry_dte": 31,
#         "leg1_delta": 0.50,
#         "leg2_delta": 0.30,
#         "contract_size": 1,
#         "expr_type": "SPXW",
#     }
#     spread = long_call_spread(DATA, filters)
#     result = spread.calc_win_rate()
#     print(spread)
#     assert result == 0


# def test_trade_singles():
#     filters = {
#         "start_date": datetime(2018, 1, 1),
#         "end_date": datetime(2018, 2, 28),
#         "entry_dte": 31,
#         "leg1_delta": 0.50,
#         "contract_size": 1,
#         "expr_type": "SPXW",
#     }
#     spread = long_call(DATA, filters)
#     result = spread.trades()


# def test_trade_verticals():
#     filters = {
#         "start_date": datetime(2018, 1, 1),
#         "end_date": datetime(2018, 2, 28),
#         "entry_dte": 31,
#         "leg1_delta": 0.50,
#         "leg2_delta": 0.30,
#         "contract_size": 1,
#         "expr_type": "SPXW",
#     }
#     spread = long_call_spread(DATA, filters)
#     result = spread.trades()
