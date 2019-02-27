#     Optopsy - Python Backtesting library for options trading strategies
#     Copyright (C) 2018  Michael Chu

#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging
from .enums import OptionType
from .backtest import create_spread 
from .filters import filter_data, func_map
from .checks import (
	data_checks,
    singles_checks,
    call_spread_checks,
    put_spread_checks,
    iron_condor_checks,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _process_legs(data, legs, fil, check_func, mode):
    logging.debug(f"Filters: {fil}")
    if _filter_checks(fil, check_func):
        logging.debug(f"Processing {len(data.index)} rows...")
        return create_spread(data, legs, fil, mode)


def _filter_checks(filter, func=None):
    return True if func is None else func(filter)


def long_call(data, filters, mode="market"):
    logger.debug("Creating Long Calls...")
    legs = [(OptionType.CALL, 1)]
    return _process_legs(data, legs, filters, singles_checks, mode)


def short_call(data, filters, mode="market"):
    logger.debug("Creating Short Calls...")
    legs = [(OptionType.CALL, -1)]
    return _process_legs(data, legs, filters, singles_checks, mode)


def long_put(data, filters, mode="market"):
    logger.debug("Creating Long Puts...")
    legs = [(OptionType.PUT, 1)]
    return _process_legs(data, legs, filters, singles_checks, mode)


def short_put(data, filters, mode="market"):
    logger.debug("Creating Short Puts...")
    legs = [(OptionType.PUT, -1)]
    return _process_legs(data, legs, filters, singles_checks, mode)


def long_call_spread(data, filters, mode="market"):
    logger.debug("Creating Long Call Spreads...")
    legs = [(OptionType.CALL, 1), (OptionType.CALL, -1)]
    return _process_legs(data, legs, filters, call_spread_checks, mode)


def short_call_spread(data, filters, mode="market"):
    logger.debug("Creating Short Call Spreads...")
    legs = [(OptionType.CALL, -1), (OptionType.CALL, 1)]
    return _process_legs(data, legs, filters, call_spread_checks, mode)


def long_put_spread(data, filters, mode="market"):
    logger.debug("Creating Long Put Spreads...")
    legs = [(OptionType.PUT, -1), (OptionType.PUT, 1)]
    return _process_legs(data, legs, filters, put_spread_checks, mode)


def short_put_spread(data, filters, mode="market"):
    logger.debug("Creating Short Put Spreads...")
    legs = [(OptionType.PUT, 1), (OptionType.PUT, -1)]
    return _process_legs(data, legs, filters, put_spread_checks, mode)


def _iron_condor(data, legs, filters, mode):
    spread = _process_legs(data, legs, filters, iron_condor_checks, mode)

    if spread is None:
        return None
    else:
        return (
            spread.assign(
                d_strike=lambda r: spread.duplicated(subset="strike", keep=False)
            )
            .groupby(spread.index)
            .filter(lambda r: (r.d_strike == False).all())
            .drop(columns="d_strike")
        )


def long_iron_condor(data, filters, mode="market"):
    logger.debug("Creating Long Iron Condors...")
    legs = [
        (OptionType.PUT, 1),
        (OptionType.PUT, -1),
        (OptionType.CALL, -1),
        (OptionType.CALL, 1),
    ]
    return _iron_condor(data, legs, filters, mode)


def short_iron_condor(data, filters, mode="market"):
    logger.debug("Creating Short Iron Condors...")
    legs = [
        (OptionType.PUT, -1),
        (OptionType.PUT, 1),
        (OptionType.CALL, 1),
        (OptionType.CALL, -1),
    ]
    return _iron_condor(data, legs, filters, mode)
