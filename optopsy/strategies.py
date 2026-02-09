"""Public API for options strategy generation.

This module exposes all 28 supported options strategies. Each public function
accepts a DataFrame of option chain data (produced by :func:`optopsy.datafeeds.csv_data`)
and optional keyword parameters that control filtering, grouping, and slippage.

Strategy families:
    - **Singles**: long/short calls and puts.
    - **Straddles & Strangles**: paired call + put at same or different strikes.
    - **Vertical Spreads**: bull/bear call and put spreads.
    - **Butterflies**: 3-leg strategies with equal-width wings.
    - **Iron Condors & Iron Butterflies**: 4-leg strategies combining puts and calls.
    - **Covered Strategies**: covered calls and protective puts.
    - **Calendar Spreads**: same strike, different expirations.
    - **Diagonal Spreads**: different strikes and expirations.

Common keyword arguments accepted by all strategies:
    dte_interval (int): DTE bucket width for grouping (default: 7).
    max_entry_dte (int): Maximum days-to-expiration at entry (default: 90).
    exit_dte (int): Days-to-expiration at which to exit (default: 0).
    otm_pct_interval (float): OTM percentage bucket width (default: 0.05).
    max_otm_pct (float): Maximum OTM percentage to consider (default: 0.5).
    min_bid_ask (float): Minimum bid/ask to filter worthless options (default: 0.05).
    raw (bool): Return raw trade-level data instead of grouped statistics
        (default: False).
    drop_nan (bool): Drop rows with NaN statistics (default: True).
    slippage (str): Fill-price model — ``"mid"``, ``"spread"``, or ``"liquidity"``
        (default: ``"mid"``).
    fill_ratio (float): Base fill ratio for liquidity mode, 0.0-1.0 (default: 0.5).
    reference_volume (int): Volume threshold for liquid options (default: 1000).
"""

from typing import Any, Dict, List, Tuple
import pandas as pd
from .core import _calls, _puts, _process_strategy, _process_calendar_strategy
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
    calendar_spread_internal_cols,
    calendar_spread_external_cols,
    diagonal_spread_internal_cols,
    diagonal_spread_external_cols,
)
from .rules import (
    _rule_non_overlapping_strike,
    _rule_butterfly_strikes,
    _rule_iron_condor_strikes,
    _rule_iron_butterfly_strikes,
    _rule_expiration_ordering,
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
    # Greeks filtering (optional)
    "delta_min": None,
    "delta_max": None,
    # Greeks grouping (optional)
    "delta_interval": None,
    # Slippage settings
    "slippage": "mid",  # "mid", "spread", or "liquidity"
    "fill_ratio": 0.5,  # Base fill ratio for liquidity mode (0.0-1.0)
    "reference_volume": 1000,  # Volume threshold for liquid options
}

calendar_default_kwargs: Dict[str, Any] = {
    "front_dte_min": 20,
    "front_dte_max": 40,
    "back_dte_min": 50,
    "back_dte_max": 90,
    "exit_dte": 7,
    "dte_interval": 7,
    "otm_pct_interval": 0.05,
    "max_otm_pct": 0.5,
    "min_bid_ask": 0.05,
    "drop_nan": True,
    "raw": False,
    # Slippage settings
    "slippage": "mid",  # "mid", "spread", or "liquidity"
    "fill_ratio": 0.5,  # Base fill ratio for liquidity mode (0.0-1.0)
    "reference_volume": 1000,  # Volume threshold for liquid options
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


def _spread(data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Any) -> pd.DataFrame:
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


def long_calls(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """Generate long call strategy statistics.

    A single-leg bullish strategy that purchases a call option, granting
    the right to buy the underlying at the strike price. Risk is limited
    to the premium paid, while potential profit is theoretically unlimited
    as the underlying appreciates above the strike.

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters (dte_interval, max_entry_dte, etc.)

    Returns:
        DataFrame with long call strategy performance statistics.
    """
    return _singles(data, [(Side.long, _calls)], **kwargs)


def long_puts(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """Generate long put strategy statistics.

    A single-leg bearish strategy that purchases a put option, granting
    the right to sell the underlying at the strike price. Risk is limited
    to the premium paid, while profit increases as the underlying declines
    below the strike. Commonly used for directional bearish exposure or
    as portfolio insurance against downside moves.

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with long put strategy performance statistics.
    """
    return _singles(data, [(Side.long, _puts)], **kwargs)


def short_calls(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """Generate short call strategy statistics.

    A single-leg strategy that sells a call option to collect premium,
    expressing a neutral-to-bearish outlook. Maximum profit is the
    premium received if the underlying remains below the strike at
    expiration. Risk is theoretically unlimited as the underlying
    rises above the strike. Benefits from time decay (theta).

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with short call strategy performance statistics.
    """
    return _singles(data, [(Side.short, _calls)], **kwargs)


def short_puts(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """Generate short put strategy statistics.

    A single-leg strategy that sells a put option to collect premium,
    expressing a neutral-to-bullish outlook. Maximum profit is the
    premium received if the underlying remains above the strike at
    expiration. Risk is substantial if the underlying declines
    significantly below the strike. Benefits from time decay (theta).

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with short put strategy performance statistics.
    """
    return _singles(data, [(Side.short, _puts)], **kwargs)


def long_straddles(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """Generate long straddle strategy statistics.

    A volatility strategy that purchases both a call and a put at the
    same strike, profiting from a large move in either direction. The
    position requires the underlying to move beyond the combined premium
    paid to become profitable. Commonly deployed ahead of anticipated
    high-volatility events such as earnings or regulatory decisions.

    Structure: long call + long put at the same strike.

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with long straddle strategy performance statistics.
    """
    return _straddles(data, [(Side.long, _puts), (Side.long, _calls)], **kwargs)


def short_straddles(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """Generate short straddle strategy statistics.

    A premium-collection strategy that sells both a call and a put at the
    same strike, profiting when the underlying remains near that strike.
    Maximum profit occurs if the underlying expires exactly at the strike.
    Risk is unlimited in both directions, making this a strategy suited
    for low-volatility environments where significant movement is not
    expected.

    Structure: short call + short put at the same strike.

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with short straddle strategy performance statistics.
    """
    return _straddles(data, [(Side.short, _puts), (Side.short, _calls)], **kwargs)


def long_strangles(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """Generate long strangle strategy statistics.

    A volatility strategy that purchases an out-of-the-money call and an
    out-of-the-money put at different strikes. Lower cost than a straddle
    due to both options being OTM, but requires a larger move in the
    underlying to become profitable. Suitable when a significant price
    movement is anticipated but direction is uncertain.

    Structure: long put (lower strike) + long call (higher strike).

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with long strangle strategy performance statistics.
    """
    return _strangles(data, [(Side.long, _puts), (Side.long, _calls)], **kwargs)


def short_strangles(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """Generate short strangle strategy statistics.

    A premium-collection strategy that sells an out-of-the-money put and
    an out-of-the-money call at different strikes. Provides a wider
    profit zone than a short straddle in exchange for lower premium
    collected. Profitable when the underlying remains between the two
    strikes, with risk increasing as the underlying moves beyond either
    strike.

    Structure: short put (lower strike) + short call (higher strike).

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with short strangle strategy performance statistics.
    """
    return _strangles(data, [(Side.short, _puts), (Side.short, _calls)], **kwargs)


def long_call_spread(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """Generate long call spread (bull call spread) statistics.

    A defined-risk bullish strategy that buys a lower-strike call and
    sells a higher-strike call at the same expiration. Both maximum profit
    and maximum loss are capped, making this a controlled-risk approach
    to bullish exposure. The short call reduces the net premium paid
    relative to an outright long call, at the cost of capping the upside.

    Structure: long call (lower strike) + short call (higher strike).

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with long call spread strategy performance statistics.
    """
    return _spread(data, [(Side.long, _calls), (Side.short, _calls)], **kwargs)


def short_call_spread(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """Generate short call spread (bear call spread) statistics.

    A defined-risk credit strategy that sells a lower-strike call and
    buys a higher-strike call for protection, collecting a net credit.
    Maximum profit is the credit received if the underlying stays below
    the short strike. Maximum loss is the width of the strikes minus
    the credit received. Expresses a neutral-to-bearish outlook.

    Structure: short call (lower strike) + long call (higher strike).

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with short call spread strategy performance statistics.
    """
    return _spread(data, [(Side.short, _calls), (Side.long, _calls)], **kwargs)


def long_put_spread(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """Generate long put spread (bear put spread) statistics.

    A defined-risk bearish strategy that buys a higher-strike put and
    sells a lower-strike put at the same expiration. Both maximum profit
    and maximum loss are capped. The short put reduces the net premium
    paid relative to an outright long put, at the cost of limiting profit
    potential below the lower strike.

    Structure: short put (lower strike) + long put (higher strike).

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with long put spread strategy performance statistics.
    """
    return _spread(data, [(Side.short, _puts), (Side.long, _puts)], **kwargs)


def short_put_spread(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """Generate short put spread (bull put spread) statistics.

    A defined-risk credit strategy that sells a higher-strike put and
    buys a lower-strike put for protection, collecting a net credit.
    Maximum profit is the credit received if the underlying stays above
    the short strike. Maximum loss is the width of the strikes minus
    the credit received. Expresses a neutral-to-bullish outlook.

    Structure: long put (lower strike) + short put (higher strike).

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with short put spread strategy performance statistics.
    """
    return _spread(data, [(Side.long, _puts), (Side.short, _puts)], **kwargs)


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
    """Generate long call butterfly strategy statistics.

    A three-leg defined-risk strategy constructed with calls that targets
    a specific price at expiration. The position achieves maximum profit
    when the underlying expires at the middle strike, and maximum loss is
    limited to the net debit paid. The equal-width wings finance the
    body, resulting in a low-cost entry with a narrow profit zone.

    Structure:
        - Long 1 call at lower strike (wing)
        - Short 2 calls at middle strike (body)
        - Long 1 call at upper strike (wing)

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with long call butterfly strategy performance statistics.
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
    """Generate short call butterfly strategy statistics.

    A three-leg defined-risk strategy constructed with calls that profits
    when the underlying moves away from the middle strike. The position
    collects a small credit and reaches maximum loss only if the
    underlying expires exactly at the middle strike. Suitable when
    expecting significant price movement in either direction.

    Structure:
        - Short 1 call at lower strike (wing)
        - Long 2 calls at middle strike (body)
        - Short 1 call at upper strike (wing)

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with short call butterfly strategy performance statistics.
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
    """Generate long put butterfly strategy statistics.

    A three-leg defined-risk strategy constructed with puts that targets
    a specific price at expiration. Functionally equivalent to a long call
    butterfly in terms of payoff profile, but may offer different pricing
    due to put-call skew. Maximum profit occurs at the middle strike;
    maximum loss is the net debit paid.

    Structure:
        - Long 1 put at lower strike (wing)
        - Short 2 puts at middle strike (body)
        - Long 1 put at upper strike (wing)

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with long put butterfly strategy performance statistics.
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
    """Generate short put butterfly strategy statistics.

    A three-leg defined-risk strategy constructed with puts that profits
    when the underlying moves away from the middle strike. Collects a
    small credit at entry and achieves maximum loss only if the underlying
    expires at the middle strike. Expresses a view on increased
    volatility or directional movement.

    Structure:
        - Short 1 put at lower strike (wing)
        - Long 2 puts at middle strike (body)
        - Short 1 put at upper strike (wing)

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with short put butterfly strategy performance statistics.
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
    """Generate iron condor strategy statistics.

    A four-leg defined-risk credit strategy that combines a bull put
    spread and a bear call spread, establishing a range within which
    the position is profitable. Maximum profit is the net credit received
    if the underlying remains between the two short strikes at expiration.
    Maximum loss is limited to the width of either spread minus the
    credit received.

    Structure:
        - Long 1 put at lowest strike (protection)
        - Short 1 put at lower-middle strike (income)
        - Short 1 call at upper-middle strike (income)
        - Long 1 call at highest strike (protection)

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with iron condor strategy performance statistics.
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
    """Generate reverse iron condor strategy statistics.

    A four-leg defined-risk debit strategy that profits when the
    underlying breaks out of a defined range in either direction. The
    inverse of a standard iron condor: the position pays a net debit
    at entry and achieves maximum profit when the underlying moves
    beyond either long strike at expiration. Maximum loss is the net
    debit paid if the underlying remains between the short strikes.

    Structure:
        - Short 1 put at lowest strike
        - Long 1 put at lower-middle strike
        - Long 1 call at upper-middle strike
        - Short 1 call at highest strike

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with reverse iron condor strategy performance statistics.
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
    """Generate iron butterfly strategy statistics.

    A four-leg defined-risk credit strategy that sells a straddle at the
    middle strike and buys protective wings. Collects a larger credit
    than an iron condor due to the at-the-money short strikes, but has
    a narrower profit zone. Maximum profit occurs when the underlying
    expires exactly at the shared middle strike. Maximum loss is the
    wing width minus the credit received.

    Structure:
        - Long 1 put at lowest strike (wing)
        - Short 1 put at middle strike (body)
        - Short 1 call at middle strike (body) — same strike as short put
        - Long 1 call at highest strike (wing)

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with iron butterfly strategy performance statistics.
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
    """Generate reverse iron butterfly strategy statistics.

    A four-leg defined-risk debit strategy that buys a straddle at the
    middle strike and sells protective wings. Profits when the underlying
    moves significantly away from the middle strike in either direction,
    with gains capped at the wing width. A lower-cost alternative to a
    long straddle, with defined risk equal to the net debit paid.

    Structure:
        - Short 1 put at lowest strike (wing)
        - Long 1 put at middle strike (body)
        - Long 1 call at middle strike (body) — same strike as long put
        - Short 1 call at highest strike (wing)

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with reverse iron butterfly strategy performance statistics.
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
    """Generate covered call strategy statistics.

    A two-leg income strategy that holds a long position in the
    underlying (simulated via a deep in-the-money call) and sells a
    call at a higher strike to collect premium. Upside is capped at
    the short strike, while downside risk remains if the underlying
    declines. Primarily used to generate income on an existing position.

    Structure:
        - Long underlying position (simulated via long deep ITM call)
        - Short 1 call at higher strike

    Note: This implementation uses a synthetic approach with options only.

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with covered call strategy performance statistics.
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
    """Generate protective put (married put) strategy statistics.

    A two-leg hedging strategy that holds a long position in the
    underlying (simulated via a deep in-the-money call) and purchases
    a put at a lower strike for downside protection. Upside potential
    remains unlimited above the long position's cost basis, while losses
    are floored at the put strike minus the premium paid. Commonly used
    for portfolio protection during periods of uncertainty.

    Structure:
        - Long underlying position (simulated via long deep ITM call)
        - Long 1 put at lower strike for protection

    Note: This implementation uses a synthetic approach with options only.

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with protective put strategy performance statistics.
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
    data: pd.DataFrame, leg_def: List[Tuple], same_strike: bool = True, **kwargs: Any
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


def long_call_calendar(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """Generate long call calendar spread strategy statistics.

    A time-spread strategy that sells a near-term call and buys a
    longer-term call at the same strike. Profits primarily from the
    accelerated time decay of the front-month option relative to the
    back-month option. Most profitable when the underlying remains near
    the shared strike through front-month expiration.

    Structure:
        - Short 1 front-month call (near-term expiration)
        - Long 1 back-month call (longer-term expiration)
        - Both at the same strike

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters including:

            - front_dte_min: Minimum DTE for front leg (default: 20).
            - front_dte_max: Maximum DTE for front leg (default: 40).
            - back_dte_min: Minimum DTE for back leg (default: 50).
            - back_dte_max: Maximum DTE for back leg (default: 90).
            - exit_dte: Days before front expiration to exit (default: 7).

    Returns:
        DataFrame with long call calendar spread strategy performance statistics.
    """
    return _calendar_spread(
        data, [(Side.short, _calls), (Side.long, _calls)], same_strike=True, **kwargs
    )


def short_call_calendar(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """Generate short call calendar spread strategy statistics.

    A time-spread strategy that buys a near-term call and sells a
    longer-term call at the same strike. The inverse of a long call
    calendar, this position profits when the underlying moves
    significantly away from the strike or when implied volatility
    declines, reducing the back-month option's value.

    Structure:
        - Long 1 front-month call (near-term expiration)
        - Short 1 back-month call (longer-term expiration)
        - Both at the same strike

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with short call calendar spread strategy performance statistics.
    """
    return _calendar_spread(
        data, [(Side.long, _calls), (Side.short, _calls)], same_strike=True, **kwargs
    )


def long_put_calendar(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """Generate long put calendar spread strategy statistics.

    A time-spread strategy that sells a near-term put and buys a
    longer-term put at the same strike. Functionally similar to a long
    call calendar in terms of time-decay dynamics, but constructed with
    puts. May offer different pricing characteristics due to put-call
    skew, and carries a slightly bearish bias relative to its call
    counterpart.

    Structure:
        - Short 1 front-month put (near-term expiration)
        - Long 1 back-month put (longer-term expiration)
        - Both at the same strike

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with long put calendar spread strategy performance statistics.
    """
    return _calendar_spread(
        data, [(Side.short, _puts), (Side.long, _puts)], same_strike=True, **kwargs
    )


def short_put_calendar(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """Generate short put calendar spread strategy statistics.

    A time-spread strategy that buys a near-term put and sells a
    longer-term put at the same strike. The inverse of a long put
    calendar, this position profits from significant movement in the
    underlying or a decline in implied volatility.

    Structure:
        - Long 1 front-month put (near-term expiration)
        - Short 1 back-month put (longer-term expiration)
        - Both at the same strike

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with short put calendar spread strategy performance statistics.
    """
    return _calendar_spread(
        data, [(Side.long, _puts), (Side.short, _puts)], same_strike=True, **kwargs
    )


def long_call_diagonal(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """Generate long call diagonal spread strategy statistics.

    A strategy that combines elements of both calendar and vertical
    spreads by selling a near-term call and buying a longer-term call
    at a different strike. The differing strikes introduce a directional
    bias in addition to the time-decay dynamics of a calendar spread,
    offering flexibility to express both a directional view and a
    volatility thesis simultaneously.

    Structure:
        - Short 1 front-month call (near-term expiration)
        - Long 1 back-month call (longer-term expiration)
        - Different strikes for each leg

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with long call diagonal spread strategy performance statistics.
    """
    return _calendar_spread(
        data, [(Side.short, _calls), (Side.long, _calls)], same_strike=False, **kwargs
    )


def short_call_diagonal(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """Generate short call diagonal spread strategy statistics.

    A strategy that buys a near-term call and sells a longer-term call
    at a different strike. The inverse of a long call diagonal, this
    position profits from significant movement in the underlying or a
    decline in implied volatility. The strike difference introduces a
    directional component to the volatility position.

    Structure:
        - Long 1 front-month call (near-term expiration)
        - Short 1 back-month call (longer-term expiration)
        - Different strikes for each leg

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with short call diagonal spread strategy performance statistics.
    """
    return _calendar_spread(
        data, [(Side.long, _calls), (Side.short, _calls)], same_strike=False, **kwargs
    )


def long_put_diagonal(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """Generate long put diagonal spread strategy statistics.

    A strategy that sells a near-term put and buys a longer-term put
    at a different strike, combining time-decay income with a
    directional view. The differing strikes allow precise calibration
    of the position's directional bias, from moderately bearish to
    approximately neutral.

    Structure:
        - Short 1 front-month put (near-term expiration)
        - Long 1 back-month put (longer-term expiration)
        - Different strikes for each leg

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with long put diagonal spread strategy performance statistics.
    """
    return _calendar_spread(
        data, [(Side.short, _puts), (Side.long, _puts)], same_strike=False, **kwargs
    )


def short_put_diagonal(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """Generate short put diagonal spread strategy statistics.

    A strategy that buys a near-term put and sells a longer-term put
    at a different strike. The inverse of a long put diagonal, this
    position profits from significant movement in the underlying or a
    decline in implied volatility. The strike difference allows
    directional bias to be incorporated into the volatility position.

    Structure:
        - Long 1 front-month put (near-term expiration)
        - Short 1 back-month put (longer-term expiration)
        - Different strikes for each leg

    Args:
        data: DataFrame containing option chain data.
        **kwargs: Optional strategy parameters.

    Returns:
        DataFrame with short put diagonal spread strategy performance statistics.
    """
    return _calendar_spread(
        data, [(Side.long, _puts), (Side.short, _puts)], same_strike=False, **kwargs
    )
