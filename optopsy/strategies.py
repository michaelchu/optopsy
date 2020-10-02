from .core import (
    _process_entries_and_exits,
    _calls,
    _puts,
    _group_by_intervals,
    _calculate_profit_loss_pct,
    _select_final_output_column,
)

default_kwargs = {
    "dte_interval": 7,
    "max_entry_dte": 180,
    "exit_dte": 0,
    "strike_dist_pct_interval": 0.05,
    "max_strike_dist_pct": 1,
    "min_bid_ask": 0.05,
    "ret_profit": False,
    "side": None,
    "drop_nan": True,
}


def _singles(data, params):
    return (
        _process_entries_and_exits(
            data,
            dte_interval=params["dte_interval"],
            max_entry_dte=params["max_entry_dte"],
            exit_dte=params["exit_dte"],
            strike_dist_pct_interval=params["strike_dist_pct_interval"],
            max_strike_dist_pct=params["max_strike_dist_pct"],
            min_bid_ask=params["min_bid_ask"],
        )
        .pipe(_calculate_profit_loss_pct)
        .pipe(_group_by_intervals, params["drop_nan"])
        .reset_index()
        .pipe(_select_final_output_column, params["ret_profit"], params["side"])
    )


def singles_calls(data, **kwargs):
    params = {**default_kwargs, **kwargs}
    return data.pipe(_calls).pipe(_singles, params)


def singles_puts(data, **kwargs):
    params = {**default_kwargs, **kwargs}
    return data.pipe(_puts).pipe(_singles, params)


def straddles(
    data, dte_interval=7, strike_pct_interval=0.05, entry_dte=None, exit_dte=None
):
    pass


def strangles(
    data, dte_interval=7, strike_pct_interval=0.05, entry_dte=None, exit_dte=None
):
    pass
