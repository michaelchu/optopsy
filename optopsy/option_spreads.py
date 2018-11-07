from .option_queries import nearest, eq, opt_type
import pandas as pd


def create_legs(data, legs):
    def _create_leg(leg):
        return (
            data
            .pipe(opt_type, option_type=leg[0])
            .pipe(nearest, 'delta', leg[1])
            .pipe(eq, 'dte', leg[2])
            .assign(ratio=leg[3])
        )

    spread = [_create_leg(legs[l]) for l in range(0, len(legs))]
    return spread[0] if len(legs) == 1 else pd.concat(spread).reset_index(drop=True)
