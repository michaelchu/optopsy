from .option_query import *


def _process_tuple_val(leg, val, col):
    if not isinstance(val, tuple):
        return leg

    return (leg
            .pipe(nearest, column=col, val=val[1])
            .pipe(between, column=col, start=val[0], end=val[2])
            )


def leg_1_abs_delta(leg, val):
    return abs_delta(leg, val, num=1)


def leg_2_abs_delta(leg, val):
    return abs_delta(leg, val, num=2)


def leg_3_abs_delta(leg, val):
    return abs_delta(leg, val, num=3)


def leg_4_abs_delta(leg, val):
    return abs_delta(leg, val, num=4)


def leg_1_dte(leg, val):
    return dte(leg, val, num=1)


def leg_2_dte(leg, val):
    return dte(leg, val, num=2)


def leg_3_dte(leg, val):
    return dte(leg, val, num=3)


def leg_4_dte(leg, val):
    return dte(leg, val, num=4)


def spread_price(legs, val):
    pass