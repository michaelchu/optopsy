from typing import Any, Callable, Dict, Tuple
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
        if k in param_checks:
            param_checks[k](k, v)
    _check_data_types(data)


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
}
