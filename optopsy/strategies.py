from typing import Any, Dict, List, Tuple
import pandas as pd
from .core import _calls, _puts, _process_strategy
from .definitions import (
    single_strike_external_cols,
    single_strike_internal_cols,
    double_strike_external_cols,
    double_strike_internal_cols,
    triple_strike_external_cols,
    triple_strike_internal_cols,
    quadruple_strike_external_cols,
    quadruple_strike_internal_cols,
    straddle_internal_cols,
)
from .rules import (
    _rule_non_overlapping_strike,
    _rule_butterfly_strikes,
    _rule_iron_condor_strikes,
    _rule_iron_butterfly_strikes,
)
from enum import Enum

default_kwargs: Dict[str, Any] = {
    "dte_interval": 7,
    "max_entry_dte": 90,
    "exit_dte": 0,
    "otm_pct_interval": 0.05,
    "max_otm_pct": 0.5,
    "min_bid_ask": 0.05,
    "drop_nan": True,
    "raw": False,
}


class Side(Enum):
    """Enum representing long or short position side with multiplier values."""

    long = 1
    short = -1


def _singles(data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Any) -> pd.DataFrame:
    """Process single-leg option strategies (calls or puts)."""
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=single_strike_internal_cols,
        external_cols=single_strike_external_cols,
        leg_def=leg_def,
        params=params,
    )


def _straddles(data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Any) -> pd.DataFrame:
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


def _strangles(data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Any) -> pd.DataFrame:
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


def _call_spread(
    data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Any
) -> pd.DataFrame:
    """Process call spread strategies (long and short calls at different strikes)."""
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


def _put_spread(
    data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Any
) -> pd.DataFrame:
    """Process put spread strategies (long and short puts at different strikes)."""
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


def long_calls(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate long call strategy statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters (dte_interval, max_entry_dte, etc.)

    Returns:
        DataFrame with long call strategy performance statistics
    """
    return _singles(data, [(Side.long, _calls)], **kwargs)


def long_puts(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate long put strategy statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long put strategy performance statistics
    """
    return _singles(data, [(Side.long, _puts)], **kwargs)


def short_calls(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate short call strategy statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short call strategy performance statistics
    """
    return _singles(data, [(Side.short, _calls)], **kwargs)


def short_puts(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate short put strategy statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short put strategy performance statistics
    """
    return _singles(data, [(Side.short, _puts)], **kwargs)


def long_straddles(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate long straddle strategy statistics (long call + long put at same strike).

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long straddle strategy performance statistics
    """
    return _straddles(data, [(Side.long, _puts), (Side.long, _calls)], **kwargs)


def short_straddles(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate short straddle strategy statistics (short call + short put at same strike).

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short straddle strategy performance statistics
    """
    return _straddles(data, [(Side.short, _puts), (Side.short, _calls)], **kwargs)


def long_strangles(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate long strangle strategy statistics (long call + long put at different strikes).

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long strangle strategy performance statistics
    """
    return _strangles(data, [(Side.long, _puts), (Side.long, _calls)], **kwargs)


def short_strangles(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate short strangle strategy statistics (short call + short put at different strikes).

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short strangle strategy performance statistics
    """
    return _strangles(data, [(Side.short, _puts), (Side.short, _calls)], **kwargs)


def long_call_spread(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate long call spread (bull call spread) statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long call spread strategy performance statistics
    """
    return _call_spread(data, [(Side.long, _calls), (Side.short, _calls)], **kwargs)


def short_call_spread(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate short call spread (bear call spread) statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short call spread strategy performance statistics
    """
    return _call_spread(data, [(Side.short, _calls), (Side.long, _calls)], **kwargs)


def long_put_spread(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate long put spread (bear put spread) statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long put spread strategy performance statistics
    """
    return _put_spread(data, [(Side.short, _puts), (Side.long, _puts)], **kwargs)


def short_put_spread(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate short put spread (bull put spread) statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short put spread strategy performance statistics
    """
    return _put_spread(data, [(Side.long, _puts), (Side.short, _puts)], **kwargs)


# =============================================================================
# Butterfly Strategies (3 legs)
# =============================================================================


def _butterfly(data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Any) -> pd.DataFrame:
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


def long_call_butterfly(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
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


def short_call_butterfly(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
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


def long_put_butterfly(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
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


def short_put_butterfly(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
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
    data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Any
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
    data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Any
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


def iron_condor(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
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


def reverse_iron_condor(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
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


def iron_butterfly(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
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


def reverse_iron_butterfly(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
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
    data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Any
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


def covered_call(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
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


def protective_put(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
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
