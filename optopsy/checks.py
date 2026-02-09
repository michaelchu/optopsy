"""Input validation for strategy parameters and option chain DataFrames.

This module validates that user-supplied parameters (DTE ranges, OTM percentages,
slippage settings, etc.) and input DataFrames conform to the expected types and
value ranges before any processing begins.

Validation entry points:
    :func:`_run_checks` — for standard (same-expiration) strategies.
    :func:`_run_calendar_checks` — for calendar/diagonal spread strategies,
    which have additional front/back DTE range constraints.
"""

from typing import Any, Callable, Dict, Optional, Tuple
import pandas as pd

expected_types: Dict[str, Tuple[str, ...]] = {
    "underlying_symbol": ("object", "str"),
    "underlying_price": ("int64", "float64"),
    "option_type": ("object", "str"),
    "expiration": ("datetime64[ns]", "datetime64[us]"),
    "quote_date": ("datetime64[ns]", "datetime64[us]"),
    "strike": ("int64", "float64"),
    "bid": ("int64", "float64"),
    "ask": ("int64", "float64"),
}

# Optional Greek columns - only validated when Greeks filtering/grouping is enabled
optional_greek_types: Dict[str, Tuple[str, ...]] = {
    "delta": ("int64", "float64"),
    "gamma": ("int64", "float64"),
    "theta": ("int64", "float64"),
    "vega": ("int64", "float64"),
}

# Optional liquidity columns - only validated when liquidity slippage is enabled
optional_liquidity_types: Dict[str, Tuple[str, ...]] = {
    "volume": ("int64", "float64"),
    "open_interest": ("int64", "float64"),
}


def _run_checks(params: Dict[str, Any], data: pd.DataFrame) -> None:
    """
    Run all validation checks on parameters and data.

    Args:
        params: Dictionary of strategy parameters
        data: DataFrame containing option chain data

    Raises:
        ValueError: If any validation check fails
    """
    for k, v in params.items():
        if k in param_checks and v is not None:
            param_checks[k](k, v)
    _check_data_types(data)

    # Check for delta column if delta filtering/grouping is enabled
    if _requires_delta(params):
        _check_greek_column(data, "delta")

    # Check for volume column if liquidity slippage is enabled
    if _requires_volume(params):
        _check_volume_column(data)


def _run_calendar_checks(params: Dict[str, Any], data: pd.DataFrame) -> None:
    """
    Run validation checks for calendar/diagonal spread parameters.

    Args:
        params: Dictionary of strategy parameters
        data: DataFrame containing option chain data

    Raises:
        ValueError: If any validation check fails
    """
    for k, v in params.items():
        if k in param_checks and v is not None:
            param_checks[k](k, v)
    _check_data_types(data)

    # Validate DTE range ordering
    front_dte_min = params.get("front_dte_min")
    front_dte_max = params.get("front_dte_max")
    back_dte_min = params.get("back_dte_min")
    back_dte_max = params.get("back_dte_max")

    if front_dte_min is not None and front_dte_max is not None:
        if front_dte_min > front_dte_max:
            raise ValueError(
                f"front_dte_min ({front_dte_min}) must be <= "
                f"front_dte_max ({front_dte_max})"
            )

    if back_dte_min is not None and back_dte_max is not None:
        if back_dte_min > back_dte_max:
            raise ValueError(
                f"back_dte_min ({back_dte_min}) must be <= "
                f"back_dte_max ({back_dte_max})"
            )

    # Validate no overlap between front and back DTE ranges
    if front_dte_max is not None and back_dte_min is not None:
        if front_dte_max >= back_dte_min:
            raise ValueError(
                f"front_dte_max ({front_dte_max}) must be < "
                f"back_dte_min ({back_dte_min}) to avoid overlapping ranges"
            )

    # Check for volume column if liquidity slippage is enabled
    if _requires_volume(params):
        _check_volume_column(data)


def _check_positive_integer(key: str, value: Any) -> None:
    """Validate that value is a positive integer."""
    if value <= 0 or not isinstance(value, int):
        raise ValueError(f"Invalid setting for {key}, must be positive integer")


def _check_positive_integer_inclusive(key: str, value: Any) -> None:
    """Validate that value is a non-negative integer (zero allowed)."""
    if value < 0 or not isinstance(value, int):
        raise ValueError(f"Invalid setting for {key}, must be positive integer, or 0")


def _check_positive_float(key: str, value: Any) -> None:
    """Validate that value is a positive float."""
    if value <= 0 or not isinstance(value, float):
        raise ValueError(f"Invalid setting for {key}, must be positive float type")


def _check_side(key: str, value: Any) -> None:
    """Validate that value is either 'long' or 'short'."""
    if value != "long" and value != "short":
        raise ValueError(f"Invalid setting for '{key}', must be only 'long' or 'short'")


def _check_bool_type(key: str, value: Any) -> None:
    """Validate that value is a boolean."""
    if not isinstance(value, bool):
        raise ValueError(f"Invalid setting for {key}, must be boolean type")


def _check_list_type(key: str, value: Any) -> None:
    """Validate that value is a list."""
    if not isinstance(value, list):
        raise ValueError(f"Invalid setting for {key}, must be a list type")


def _check_optional_float(key: str, value: Any) -> None:
    """Validate that value is a float or None."""
    if value is not None and not isinstance(value, (int, float)):
        raise ValueError(f"Invalid setting for {key}, must be float type or None")


def _check_slippage(key: str, value: Any) -> None:
    """Validate that value is a valid slippage mode."""
    if value not in ("mid", "spread", "liquidity"):
        raise ValueError(
            f"Invalid setting for {key}, must be 'mid', 'spread', or 'liquidity'"
        )


def _check_fill_ratio(key: str, value: Any) -> None:
    """Validate that value is a float between 0 and 1."""
    if not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise ValueError(f"Invalid setting for {key}, must be a number between 0 and 1")


def _check_data_types(data: pd.DataFrame) -> None:
    """
    Validate that DataFrame has required columns with correct data types.

    Args:
        data: DataFrame to validate

    Raises:
        ValueError: If required column is missing or has incorrect type
    """
    df_type_dict = data.dtypes.astype(str).to_dict()
    for k, et in expected_types.items():
        if k not in df_type_dict:
            raise ValueError(f"Expected column: {k} not found in DataFrame")
        if all(df_type_dict[k] != t for t in et):
            raise ValueError(
                f"{df_type_dict[k]} of {k} does not match expected types: {expected_types[k]}"
            )


def _check_greek_column(data: pd.DataFrame, greek: str) -> None:
    """
    Validate that an optional Greek column exists and has correct data type.

    Args:
        data: DataFrame to validate
        greek: Name of the Greek column to check (e.g., 'delta', 'gamma')

    Raises:
        ValueError: If Greek column is missing or has incorrect type
    """
    df_type_dict = data.dtypes.astype(str).to_dict()
    if greek not in df_type_dict:
        raise ValueError(
            f"Greek column '{greek}' not found in DataFrame. "
            f"Required for delta filtering/grouping."
        )
    expected = optional_greek_types.get(greek, ("int64", "float64"))
    if all(df_type_dict[greek] != t for t in expected):
        raise ValueError(
            f"{df_type_dict[greek]} of {greek} does not match expected types: {expected}"
        )


def _requires_delta(params: Dict[str, Any]) -> bool:
    """Check if any delta-related parameters are set."""
    return any(
        params.get(key) is not None
        for key in ["delta_min", "delta_max", "delta_interval"]
    )


def _requires_volume(params: Dict[str, Any]) -> bool:
    """Check if liquidity slippage is enabled, which requires volume column."""
    return params.get("slippage") == "liquidity"


def _check_volume_column(data: pd.DataFrame) -> None:
    """
    Validate that volume column exists and has correct data type.

    Args:
        data: DataFrame to validate

    Raises:
        ValueError: If volume column is missing or has incorrect type
    """
    df_type_dict = data.dtypes.astype(str).to_dict()
    if "volume" not in df_type_dict:
        raise ValueError(
            "Column 'volume' not found in DataFrame. "
            "Required for liquidity-based slippage."
        )
    expected = optional_liquidity_types.get("volume", ("int64", "float64"))
    if all(df_type_dict["volume"] != t for t in expected):
        raise ValueError(
            f"{df_type_dict['volume']} of volume does not match expected types: {expected}"
        )


param_checks: Dict[str, Callable[[str, Any], None]] = {
    "dte_interval": _check_positive_integer,
    "max_entry_dte": _check_positive_integer,
    "exit_dte": _check_positive_integer_inclusive,
    "otm_pct_interval": _check_positive_float,
    "max_otm_pct": _check_positive_float,
    "min_bid_ask": _check_positive_float,
    "side": _check_side,
    "drop_nan": _check_bool_type,
    "raw": _check_bool_type,
    # Greeks parameters (optional)
    "delta_min": _check_optional_float,
    "delta_max": _check_optional_float,
    "delta_interval": _check_optional_float,
    # Calendar/diagonal spread parameters
    "front_dte_min": _check_positive_integer,
    "front_dte_max": _check_positive_integer,
    "back_dte_min": _check_positive_integer,
    "back_dte_max": _check_positive_integer,
    # Slippage parameters
    "slippage": _check_slippage,
    "fill_ratio": _check_fill_ratio,
    "reference_volume": _check_positive_integer,
}
