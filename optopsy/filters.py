from .option_queries import *


def _process_tuple_val(leg, val, col):
    if not isinstance(val, tuple):
        return leg

    return (leg
            .pipe(between, column=col, start=val[0], end=val[2])
            )


def abs_delta(leg, val):
    return _process_tuple_val(leg, val, "delta")


def dte(leg, val):
    return _process_tuple_val(leg, val, "dte")
