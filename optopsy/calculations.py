import numpy as np
from functools import reduce


def calc_opt_px(data, action):
    ask = data[f"ask_{action}"] * data["ratio"]
    bid = data[f"bid_{action}"] * data["ratio"]

    if action == "entry":
        return np.where(data["ratio"] > 0, ask, bid)
    elif action == "exit":
        return np.where(data["ratio"] > 0, bid * -1, ask * -1)


def calc_entry_px(data, mode="midpoint"):
    return _assign_opt_px(data, mode, "entry")


def calc_exit_px(data, mode="midpoint"):
    return _assign_opt_px(data, mode, "exit")


def assign_trade_num(data, groupby):
    data["trade_num"] = data.groupby(groupby).ngroup()
    data = data.set_index("trade_num")
    return data


def calc_pnl(data):
    data["entry_price"] = data["entry_opt_price"] * data["contracts"] * 100
    data["exit_price"] = data["exit_opt_price"] * data["contracts"] * 100
    data["cost"] = data["exit_price"] + data["entry_price"]
    return data.round(2)


def _calc_midpint_opt_px(data, action):
    bid_ask = [f"bid_{action}", f"ask_{action}"]
    if action == "entry":
        return data[bid_ask].mean(axis=1) * data["ratio"]
    elif action == "exit":
        return data[bid_ask].mean(axis=1) * data["ratio"] * -1


def _assign_opt_px(data, mode, action):
    if mode == "midpoint":
        data[f"{action}_opt_price"] = _calc_midpint_opt_px(data, action)
    elif mode == "market":
        data[f"{action}_opt_price"] = calc_opt_px(data, action)
    return data
