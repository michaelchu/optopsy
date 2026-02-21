from enum import Enum
from typing import Any, Dict, List, Tuple

import pandas as pd
from typing_extensions import Unpack

from .core import _calls, _process_calendar_strategy, _process_strategy, _puts
from .definitions import (
    calendar_spread_external_cols,
    calendar_spread_internal_cols,
    diagonal_spread_external_cols,
    diagonal_spread_internal_cols,
    double_strike_external_cols,
    double_strike_internal_cols,
    quadruple_strike_external_cols,
    quadruple_strike_internal_cols,
    single_strike_external_cols,
    single_strike_internal_cols,
    straddle_internal_cols,
    triple_strike_external_cols,
    triple_strike_internal_cols,
)
from .rules import (
    _rule_butterfly_strikes,
    _rule_expiration_ordering,
    _rule_iron_butterfly_strikes,
    _rule_iron_condor_strikes,
    _rule_non_overlapping_strike,
)
from .types import StrategyParams

default_kwargs: Dict[str, Any] = {
    "dte_interval": 7,
    "max_entry_dte": 90,
    "exit_dte": 0,
    "exit_dte_tolerance": 0,
    "otm_pct_interval": 0.05,
    "max_otm_pct": 0.5,
    "min_bid_ask": 0.05,
    "drop_nan": True,
    "raw": False,
    # Greeks filtering (optional)
    "delta_min": None,
    "delta_max": None,
    # Greeks grouping (optional)
    "delta_interval": None,
    # Pre-computed signal dates (optional) — use apply_signal() to generate
    "entry_dates": None,
    "exit_dates": None,
    # Slippage settings
    "slippage": "mid",  # "mid", "spread", or "liquidity"
    "fill_ratio": 0.5,  # Base fill ratio for liquidity mode (0.0-1.0)
    "reference_volume": 1000,  # Volume threshold for liquid options
}

# Calendar strategies share most defaults but don't use delta or max_entry_dte,
# and override exit_dte with a different default.
_calendar_only_keys = {"max_entry_dte", "delta_min", "delta_max", "delta_interval"}
calendar_default_kwargs: Dict[str, Any] = {
    **{k: v for k, v in default_kwargs.items() if k not in _calendar_only_keys},
    "front_dte_min": 20,
    "front_dte_max": 40,
    "back_dte_min": 50,
    "back_dte_max": 90,
    "exit_dte": 7,
}


class Side(Enum):
    """Enum representing long or short position side with multiplier values."""

    long = 1
    short = -1


def _singles(
    data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """Process single-leg option strategies (calls or puts)."""
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=single_strike_internal_cols,
        external_cols=single_strike_external_cols,
        leg_def=leg_def,
        params=params,
    )


def _straddles(
    data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """Process straddle strategies (call and put at same strike)."""
    params = {**default_kwargs, **kwargs}

    return _process_strategy(
        data,
        internal_cols=straddle_internal_cols,
        external_cols=single_strike_external_cols,
        leg_def=leg_def,
        join_on=[
            "underlying_symbol",
            "expiration",
            "strike",
            "dte_entry",
            "dte_range",
            "otm_pct_range",
            "underlying_price_entry",
        ],
        params=params,
    )


def _strangles(
    data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """Process strangle strategies (call and put at different strikes)."""
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=double_strike_internal_cols,
        external_cols=double_strike_external_cols,
        leg_def=leg_def,
        rules=_rule_non_overlapping_strike,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=params,
    )


def _spread(
    data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """Process vertical spread strategies (call or put spreads at different strikes)."""
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=double_strike_internal_cols,
        external_cols=double_strike_external_cols,
        leg_def=leg_def,
        rules=_rule_non_overlapping_strike,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=params,
    )


def long_calls(data: pd.DataFrame, **kwargs: Unpack[StrategyParams]) -> pd.DataFrame:
    """
    Generate long call strategy statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters (see StrategyParams)

    Returns:
        DataFrame with long call strategy performance statistics
    """
    return _singles(data, [(Side.long, _calls)], **kwargs)


def long_puts(data: pd.DataFrame, **kwargs: Unpack[StrategyParams]) -> pd.DataFrame:
    """
    Generate long put strategy statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long put strategy performance statistics
    """
    return _singles(data, [(Side.long, _puts)], **kwargs)


def short_calls(data: pd.DataFrame, **kwargs: Unpack[StrategyParams]) -> pd.DataFrame:
    """
    Generate short call strategy statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short call strategy performance statistics
    """
    return _singles(data, [(Side.short, _calls)], **kwargs)


def short_puts(data: pd.DataFrame, **kwargs: Unpack[StrategyParams]) -> pd.DataFrame:
    """
    Generate short put strategy statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short put strategy performance statistics
    """
    return _singles(data, [(Side.short, _puts)], **kwargs)


def long_straddles(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate long straddle strategy statistics (long call + long put at same strike).

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long straddle strategy performance statistics
    """
    return _straddles(data, [(Side.long, _puts), (Side.long, _calls)], **kwargs)


def short_straddles(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate short straddle strategy statistics (short call + short put at same strike).

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short straddle strategy performance statistics
    """
    return _straddles(data, [(Side.short, _puts), (Side.short, _calls)], **kwargs)


def long_strangles(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate long strangle strategy statistics (long call + long put at different strikes).

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long strangle strategy performance statistics
    """
    return _strangles(data, [(Side.long, _puts), (Side.long, _calls)], **kwargs)


def short_strangles(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate short strangle strategy statistics (short call + short put at different strikes).

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short strangle strategy performance statistics
    """
    return _strangles(data, [(Side.short, _puts), (Side.short, _calls)], **kwargs)


def long_call_spread(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate long call spread (bull call spread) statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long call spread strategy performance statistics
    """
    return _spread(data, [(Side.long, _calls), (Side.short, _calls)], **kwargs)


def short_call_spread(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate short call spread (bear call spread) statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short call spread strategy performance statistics
    """
    return _spread(data, [(Side.short, _calls), (Side.long, _calls)], **kwargs)


def long_put_spread(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate long put spread (bear put spread) statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long put spread strategy performance statistics
    """
    return _spread(data, [(Side.short, _puts), (Side.long, _puts)], **kwargs)


def short_put_spread(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate short put spread (bull put spread) statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short put spread strategy performance statistics
    """
    return _spread(data, [(Side.long, _puts), (Side.short, _puts)], **kwargs)


# =============================================================================
# Butterfly Strategies (3 legs)
# =============================================================================


def _butterfly(
    data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """Process butterfly strategies (3 legs at different strikes)."""
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=triple_strike_internal_cols,
        external_cols=triple_strike_external_cols,
        leg_def=leg_def,
        rules=_rule_butterfly_strikes,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=params,
    )


def long_call_butterfly(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate long call butterfly strategy statistics.

    A long call butterfly consists of:
    - Long 1 call at lower strike (wing)
    - Short 2 calls at middle strike (body)
    - Long 1 call at upper strike (wing)

    This is a neutral strategy that profits when the underlying stays near
    the middle strike at expiration. Maximum profit occurs at the middle strike.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long call butterfly strategy performance statistics
    """
    return _butterfly(
        data,
        [
            (Side.long, _calls, 1),
            (Side.short, _calls, 2),
            (Side.long, _calls, 1),
        ],
        **kwargs,
    )


def short_call_butterfly(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate short call butterfly strategy statistics.

    A short call butterfly consists of:
    - Short 1 call at lower strike (wing)
    - Long 2 calls at middle strike (body)
    - Short 1 call at upper strike (wing)

    This strategy profits when the underlying moves significantly away from
    the middle strike in either direction.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short call butterfly strategy performance statistics
    """
    return _butterfly(
        data,
        [
            (Side.short, _calls, 1),
            (Side.long, _calls, 2),
            (Side.short, _calls, 1),
        ],
        **kwargs,
    )


def long_put_butterfly(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate long put butterfly strategy statistics.

    A long put butterfly consists of:
    - Long 1 put at lower strike (wing)
    - Short 2 puts at middle strike (body)
    - Long 1 put at upper strike (wing)

    This is a neutral strategy that profits when the underlying stays near
    the middle strike at expiration. Maximum profit occurs at the middle strike.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long put butterfly strategy performance statistics
    """
    return _butterfly(
        data,
        [
            (Side.long, _puts, 1),
            (Side.short, _puts, 2),
            (Side.long, _puts, 1),
        ],
        **kwargs,
    )


def short_put_butterfly(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate short put butterfly strategy statistics.

    A short put butterfly consists of:
    - Short 1 put at lower strike (wing)
    - Long 2 puts at middle strike (body)
    - Short 1 put at upper strike (wing)

    This strategy profits when the underlying moves significantly away from
    the middle strike in either direction.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short put butterfly strategy performance statistics
    """
    return _butterfly(
        data,
        [
            (Side.short, _puts, 1),
            (Side.long, _puts, 2),
            (Side.short, _puts, 1),
        ],
        **kwargs,
    )


# =============================================================================
# Iron Condor and Iron Butterfly Strategies (4 legs)
# =============================================================================


def _iron_condor(
    data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """Process iron condor strategies (4 legs at different strikes)."""
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=quadruple_strike_internal_cols,
        external_cols=quadruple_strike_external_cols,
        leg_def=leg_def,
        rules=_rule_iron_condor_strikes,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=params,
    )


def _iron_butterfly(
    data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """Process iron butterfly strategies (4 legs, middle legs share strike)."""
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=quadruple_strike_internal_cols,
        external_cols=quadruple_strike_external_cols,
        leg_def=leg_def,
        rules=_rule_iron_butterfly_strikes,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=params,
    )


def iron_condor(data: pd.DataFrame, **kwargs: Unpack[StrategyParams]) -> pd.DataFrame:
    """
    Generate iron condor strategy statistics.

    An iron condor consists of:
    - Long 1 put at lowest strike (protection)
    - Short 1 put at lower-middle strike (income)
    - Short 1 call at upper-middle strike (income)
    - Long 1 call at highest strike (protection)

    This is a neutral income strategy that profits when the underlying stays
    between the two short strikes. Maximum profit is the net credit received.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with iron condor strategy performance statistics
    """
    return _iron_condor(
        data,
        [
            (Side.long, _puts),
            (Side.short, _puts),
            (Side.short, _calls),
            (Side.long, _calls),
        ],
        **kwargs,
    )


def reverse_iron_condor(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate reverse iron condor strategy statistics.

    A reverse iron condor consists of:
    - Short 1 put at lowest strike
    - Long 1 put at lower-middle strike
    - Long 1 call at upper-middle strike
    - Short 1 call at highest strike

    This strategy profits when the underlying makes a significant move
    in either direction.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with reverse iron condor strategy performance statistics
    """
    return _iron_condor(
        data,
        [
            (Side.short, _puts),
            (Side.long, _puts),
            (Side.long, _calls),
            (Side.short, _calls),
        ],
        **kwargs,
    )


def iron_butterfly(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate iron butterfly strategy statistics.

    An iron butterfly consists of:
    - Long 1 put at lowest strike (wing)
    - Short 1 put at middle strike (body)
    - Short 1 call at middle strike (body) - same strike as short put
    - Long 1 call at highest strike (wing)

    This is a neutral income strategy with higher profit potential than
    an iron condor, but a narrower profit zone. Maximum profit occurs
    when the underlying is exactly at the middle strike at expiration.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with iron butterfly strategy performance statistics
    """
    return _iron_butterfly(
        data,
        [
            (Side.long, _puts),
            (Side.short, _puts),
            (Side.short, _calls),
            (Side.long, _calls),
        ],
        **kwargs,
    )


def reverse_iron_butterfly(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate reverse iron butterfly strategy statistics.

    A reverse iron butterfly consists of:
    - Short 1 put at lowest strike (wing)
    - Long 1 put at middle strike (body)
    - Long 1 call at middle strike (body) - same strike as long put
    - Short 1 call at highest strike (wing)

    This strategy profits when the underlying makes a significant move
    away from the middle strike in either direction.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with reverse iron butterfly strategy performance statistics
    """
    return _iron_butterfly(
        data,
        [
            (Side.short, _puts),
            (Side.long, _puts),
            (Side.long, _calls),
            (Side.short, _calls),
        ],
        **kwargs,
    )


# =============================================================================
# Covered Strategies
# =============================================================================


def _covered_call(
    data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Process covered call strategy.

    Note: This implementation simulates a covered call using options data only,
    approximating the underlying position through the relationship between
    option premiums and underlying price changes.
    """
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=double_strike_internal_cols,
        external_cols=double_strike_external_cols,
        leg_def=leg_def,
        rules=_rule_non_overlapping_strike,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=params,
    )


def covered_call(data: pd.DataFrame, **kwargs: Unpack[StrategyParams]) -> pd.DataFrame:
    """
    Generate covered call strategy statistics.

    A covered call consists of:
    - Long underlying position (simulated via long deep ITM call)
    - Short 1 call at higher strike

    This is an income strategy that profits from time decay on the short call
    while maintaining upside exposure up to the short strike. The long deep
    ITM call acts as a synthetic long stock position.

    Note: This implementation uses a synthetic approach with options only.
    For true covered call analysis with actual stock positions, additional
    data integration would be required.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with covered call strategy performance statistics
    """
    return _covered_call(
        data,
        [
            (Side.long, _calls),
            (Side.short, _calls),
        ],
        **kwargs,
    )


def protective_put(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate protective put (married put) strategy statistics.

    A protective put consists of:
    - Long underlying position (simulated via long deep ITM call)
    - Long 1 put at lower strike for protection

    This strategy provides downside protection while maintaining upside
    potential. The long deep ITM call acts as a synthetic long stock position.

    Note: This implementation uses a synthetic approach with options only.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with protective put strategy performance statistics
    """
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=double_strike_internal_cols,
        external_cols=double_strike_external_cols,
        leg_def=[
            (Side.long, _calls),
            (Side.long, _puts),
        ],
        rules=_rule_non_overlapping_strike,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=params,
    )


# =============================================================================
# Calendar and Diagonal Spread Strategies
# =============================================================================


def _calendar_spread(
    data: pd.DataFrame,
    leg_def: List[Tuple],
    same_strike: bool = True,
    **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Process calendar or diagonal spread strategies.

    Calendar spreads have the same strike but different expirations.
    Diagonal spreads have different strikes and different expirations.

    Args:
        data: DataFrame containing option chain data
        leg_def: List of tuples defining strategy legs [(side, option_filter), ...]
        same_strike: True for calendar spreads, False for diagonal spreads
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with calendar/diagonal spread strategy results
    """
    params = {**calendar_default_kwargs, **kwargs}
    internal_cols = (
        calendar_spread_internal_cols if same_strike else diagonal_spread_internal_cols
    )
    external_cols = (
        calendar_spread_external_cols if same_strike else diagonal_spread_external_cols
    )

    return _process_calendar_strategy(
        data,
        internal_cols=internal_cols,
        external_cols=external_cols,
        leg_def=leg_def,
        rules=_rule_expiration_ordering,
        same_strike=same_strike,
        params=params,
    )


def long_call_calendar(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate long call calendar spread strategy statistics.

    A long call calendar consists of:
    - Short 1 front-month call (near-term expiration)
    - Long 1 back-month call (longer-term expiration)
    - Both at the same strike

    This is a neutral strategy that profits from time decay differential
    between the two expirations. Maximum profit occurs when the underlying
    is at the strike price at front-month expiration.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters including:
            - front_dte_min: Minimum DTE for front leg (default: 20)
            - front_dte_max: Maximum DTE for front leg (default: 40)
            - back_dte_min: Minimum DTE for back leg (default: 50)
            - back_dte_max: Maximum DTE for back leg (default: 90)
            - exit_dte: Days before front expiration to exit (default: 7)

    Returns:
        DataFrame with long call calendar spread strategy performance statistics
    """
    return _calendar_spread(
        data, [(Side.short, _calls), (Side.long, _calls)], same_strike=True, **kwargs
    )


def short_call_calendar(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate short call calendar spread strategy statistics.

    A short call calendar consists of:
    - Long 1 front-month call (near-term expiration)
    - Short 1 back-month call (longer-term expiration)
    - Both at the same strike

    This strategy profits when the underlying moves significantly away
    from the strike price before front-month expiration.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short call calendar spread strategy performance statistics
    """
    return _calendar_spread(
        data, [(Side.long, _calls), (Side.short, _calls)], same_strike=True, **kwargs
    )


def long_put_calendar(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate long put calendar spread strategy statistics.

    A long put calendar consists of:
    - Short 1 front-month put (near-term expiration)
    - Long 1 back-month put (longer-term expiration)
    - Both at the same strike

    This is a neutral strategy that profits from time decay differential
    between the two expirations.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long put calendar spread strategy performance statistics
    """
    return _calendar_spread(
        data, [(Side.short, _puts), (Side.long, _puts)], same_strike=True, **kwargs
    )


def short_put_calendar(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate short put calendar spread strategy statistics.

    A short put calendar consists of:
    - Long 1 front-month put (near-term expiration)
    - Short 1 back-month put (longer-term expiration)
    - Both at the same strike

    This strategy profits when the underlying moves significantly away
    from the strike price before front-month expiration.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short put calendar spread strategy performance statistics
    """
    return _calendar_spread(
        data, [(Side.long, _puts), (Side.short, _puts)], same_strike=True, **kwargs
    )


def long_call_diagonal(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate long call diagonal spread strategy statistics.

    A long call diagonal consists of:
    - Short 1 front-month call (near-term expiration)
    - Long 1 back-month call (longer-term expiration)
    - Different strikes for each leg

    This strategy combines elements of a calendar spread and a vertical spread.
    All strike combinations are evaluated.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long call diagonal spread strategy performance statistics
    """
    return _calendar_spread(
        data, [(Side.short, _calls), (Side.long, _calls)], same_strike=False, **kwargs
    )


def short_call_diagonal(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate short call diagonal spread strategy statistics.

    A short call diagonal consists of:
    - Long 1 front-month call (near-term expiration)
    - Short 1 back-month call (longer-term expiration)
    - Different strikes for each leg

    This strategy combines elements of a calendar spread and a vertical spread.
    All strike combinations are evaluated.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short call diagonal spread strategy performance statistics
    """
    return _calendar_spread(
        data, [(Side.long, _calls), (Side.short, _calls)], same_strike=False, **kwargs
    )


def long_put_diagonal(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate long put diagonal spread strategy statistics.

    A long put diagonal consists of:
    - Short 1 front-month put (near-term expiration)
    - Long 1 back-month put (longer-term expiration)
    - Different strikes for each leg

    This strategy combines elements of a calendar spread and a vertical spread.
    All strike combinations are evaluated.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long put diagonal spread strategy performance statistics
    """
    return _calendar_spread(
        data, [(Side.short, _puts), (Side.long, _puts)], same_strike=False, **kwargs
    )


def short_put_diagonal(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate short put diagonal spread strategy statistics.

    A short put diagonal consists of:
    - Long 1 front-month put (near-term expiration)
    - Short 1 back-month put (longer-term expiration)
    - Different strikes for each leg

    This strategy combines elements of a calendar spread and a vertical spread.
    All strike combinations are evaluated.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short put diagonal spread strategy performance statistics
    """
    return _calendar_spread(
        data, [(Side.long, _puts), (Side.short, _puts)], same_strike=False, **kwargs
    )
