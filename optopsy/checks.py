import datetime

filters = {
    "start_date": datetime.date,
    "end_date": datetime.date,
    "std_expr": bool,
    "contract_size": int,
    "entry_dte": (int, tuple),
    "entry_days": int,
    "leg1_delta": (int, float, tuple),
    "leg2_delta": (int, float, tuple),
    "leg3_delta": (int, float, tuple),
    "leg4_delta": (int, float, tuple),
    "leg1_strike_pct": (int, float, tuple),
    "leg2_strike_pct": (int, float, tuple),
    "leg3_strike_pct": (int, float, tuple),
    "leg4_strike_pct": (int, float, tuple),
    "entry_spread_price": (int, float, tuple),
    "entry_spread_delta": (int, float, tuple),
    "entry_spread_yield": (int, float, tuple),
    "exit_dte": int,
    "exit_hold_days": int,
    "exit_leg_1_delta": (int, float, tuple),
    "exit_leg_1_otm_pct": (int, float, tuple),
    "exit_profit_loss_pct": (int, float, tuple),
    "exit_spread_delta": (int, float, tuple),
    "exit_spread_price": (int, float, tuple),
    "exit_strike_diff_pct": (int, float, tuple),
}


def _type_check(filter):
    return all([isinstance(filter[f], filters[f]) for f in filter])


def _date_check(f):
    return "start_date" in f and "end_date" in f


def singles_checks(f):
    return "leg1_delta" in f and _date_check(f) and _type_check(f)


def _sanitize(filters, f):
    return filters[f][1] if isinstance(filters[f], tuple) else filters[f]


def call_spread_checks(f):
    return (
        "leg1_delta" in f
        and "leg2_delta" in f
        and _date_check(f)
        and _type_check(f)
        and (_sanitize(f, "leg1_delta") > _sanitize(f, "leg2_delta"))
    )


def put_spread_checks(f):
    return (
        "leg1_delta" in f
        and "leg2_delta" in f
        and _date_check(f)
        and _type_check(f)
        and (_sanitize(f, "leg1_delta") < _sanitize(f, "leg2_delta"))
    )


def iron_condor_checks(f):
    return (
        "leg1_delta" in f
        and "leg2_delta" in f
        and "leg3_delta" in f
        and "leg4_delta" in f
        and _date_check(f)
        and _type_check(f)
        and (_sanitize(f, "leg1_delta") < _sanitize(f, "leg2_delta"))
        and (_sanitize(f, "leg3_delta") > _sanitize(f, "leg4_delta"))
    )


def iron_condor_spread_check(ic):
    return (
        ic.assign(d_strike=lambda r: ic.duplicated(subset="strike", keep=False))
        .groupby(ic.index)
        .filter(lambda r: (r.d_strike == False).all())
        .drop(columns="d_strike")
    )
