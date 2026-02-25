"""Parameter and data validation for option strategy inputs.

This module validates two things before a strategy runs:

1. **Parameter checks** — User-supplied parameters (DTE intervals,
   slippage mode, etc.) are validated via Pydantic models defined in
   ``types.py`` (``StrategyParams``, ``CalendarStrategyParams``).  The models
   are the single source of truth for both defaults and validation.

2. **DataFrame schema checks** — The input DataFrame must contain the required
   columns (``expected_types``) with compatible dtypes.  The ``delta`` column
   is always required (included in ``expected_types``).  Optional columns for
   liquidity (``optional_liquidity_types``) are validated only when the
   corresponding features are enabled.

Entry points:
- ``_run_checks()`` — standard strategies (validates params and dtypes)
- ``_run_calendar_checks()`` — calendar/diagonal spreads

Both return a validated params dict with defaults applied by the Pydantic model.
"""

from typing import Any, Dict, Tuple, Type

import pandas as pd
from pydantic import BaseModel, ValidationError

from .types import CalendarStrategyParams, StrategyParams


def _format_validation_error(e: ValidationError) -> str:
    """Format a Pydantic ValidationError into a concise, user-friendly message."""
    errors = e.errors(include_input=False)
    parts = []
    for err in errors:
        loc = err.get("loc") or ()
        loc_str = ".".join(str(part) for part in loc) if loc else ""
        msg = err.get("msg") or "Invalid value"
        parts.append(f"{loc_str}: {msg}" if loc_str else msg)
    return "; ".join(parts) if parts else "Invalid parameters"


# Required columns and their accepted dtypes for option chain DataFrames.
expected_types: Dict[str, Tuple[str, ...]] = {
    "underlying_symbol": ("object", "str"),
    "underlying_price": ("int64", "float64"),
    "option_type": ("object", "str"),
    "expiration": ("datetime64[ns]", "datetime64[us]"),
    "quote_date": ("datetime64[ns]", "datetime64[us]"),
    "strike": ("int64", "float64"),
    "bid": ("int64", "float64"),
    "ask": ("int64", "float64"),
    "delta": ("int64", "float64"),
}

# Optional Greek columns — validated only when delta filtering/grouping is enabled.
optional_greek_types: Dict[str, Tuple[str, ...]] = {
    "delta": ("int64", "float64"),
    "gamma": ("int64", "float64"),
    "theta": ("int64", "float64"),
    "vega": ("int64", "float64"),
    "implied_volatility": ("int64", "float64"),
}

# Optional liquidity columns — validated only when slippage="liquidity" is enabled.
optional_liquidity_types: Dict[str, Tuple[str, ...]] = {
    "volume": ("int64", "float64"),
    "open_interest": ("int64", "float64"),
}


def _validate_and_check(
    model_cls: Type[BaseModel], params: Dict[str, Any], data: pd.DataFrame
) -> Dict[str, Any]:
    """Validate parameters via Pydantic model and check DataFrame schema.

    Returns a validated params dict with defaults applied.
    """
    try:
        model = model_cls.model_validate(params)
    except ValidationError as e:
        raise ValueError(_format_validation_error(e)) from e

    _check_data_types(data)

    validated = model.model_dump()

    if _requires_volume(validated):
        _check_volume_column(data)

    return validated


def _run_checks(params: Dict[str, Any], data: pd.DataFrame) -> Dict[str, Any]:
    """Validate parameters and DataFrame for standard strategies.

    Returns a validated params dict with defaults applied by the Pydantic model.
    """
    return _validate_and_check(StrategyParams, params, data)


def _run_calendar_checks(params: Dict[str, Any], data: pd.DataFrame) -> Dict[str, Any]:
    """Validate parameters and DataFrame for calendar/diagonal strategies.

    Returns a validated params dict with defaults applied by the Pydantic model.
    """
    return _validate_and_check(CalendarStrategyParams, params, data)


def _check_data_types(data: pd.DataFrame) -> None:
    """Validate that DataFrame has required columns with correct data types."""
    df_type_dict = data.dtypes.astype(str).to_dict()
    for k, et in expected_types.items():
        if k not in df_type_dict:
            raise ValueError(f"Expected column: {k} not found in DataFrame")
        if all(df_type_dict[k] != t for t in et):
            raise ValueError(
                f"{df_type_dict[k]} of {k} does not match expected types: {expected_types[k]}"
            )


def _check_greek_column(data: pd.DataFrame, greek: str) -> None:
    """Validate that an optional Greek column exists and has correct data type."""
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


def _requires_volume(params: Dict[str, Any]) -> bool:
    """Check if liquidity slippage is enabled, which requires volume column."""
    return params.get("slippage") == "liquidity"


def _check_volume_column(data: pd.DataFrame) -> None:
    """Validate that volume column exists and has correct data type."""
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
