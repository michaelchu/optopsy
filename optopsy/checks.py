import datetime
import logging


filters = {
    "start_date": datetime.date,
    "end_date": datetime.date,
    "expr_type": (str, list),
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
    logging.debug("Performing type checks...")
    if all([isinstance(filter[f], filters[f]) for f in filter]):
        return True
    else:
        logging.debug("Failed at value type check...")
        return False


def singles_checks(f):
    logging.debug("Performing singles checks...")
    if "leg1_delta" in f and _type_check(f):
        return True
        logging.debug("Checks passed...")
    else:
        logging.debug("Failed at singles checks...")
        return False


def _sanitize(filters, f):
    return filters[f][1] if isinstance(filters[f], tuple) else filters[f]


def call_spread_checks(f):
    logging.debug("Performing call spread checks...")
    if (
        "leg1_delta" in f
        and "leg2_delta" in f
        and _type_check(f)
        and (_sanitize(f, "leg1_delta") > _sanitize(f, "leg2_delta"))
    ):
        logging.debug("Checks passed...")
        return True
    else:
        logging.debug("Failed call spread checks...")
        return False


def put_spread_checks(f):
    logging.debug("Performing put spread checks...")
    if (
        "leg1_delta" in f
        and "leg2_delta" in f
        and _type_check(f)
        and (_sanitize(f, "leg1_delta") < _sanitize(f, "leg2_delta"))
    ):
        logging.debug("Checks passed...")
        return True
    else:
        logging.debug("Failed at put spread checks...")
        return False


def iron_condor_checks(f):
    logging.debug("Performing iron condor checks...")
    if (
        "leg1_delta" in f
        and "leg2_delta" in f
        and "leg3_delta" in f
        and "leg4_delta" in f
        and _type_check(f)
        and (_sanitize(f, "leg1_delta") < _sanitize(f, "leg2_delta"))
        and (_sanitize(f, "leg3_delta") > _sanitize(f, "leg4_delta"))
    ):
        logging.debug("Checks passed...")
        return True
    else:
        logging.debug("Failed at iron condor checks...")
        return False
