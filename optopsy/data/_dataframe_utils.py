"""Shared DataFrame utilities."""

from __future__ import annotations

import pandas as pd


def _is_categorical_interval(dtype: object) -> bool:
    """Check if *dtype* is a CategoricalDtype whose categories are Intervals."""
    if not isinstance(dtype, pd.CategoricalDtype):
        return False
    return isinstance(dtype.categories.dtype, pd.IntervalDtype)


def stringify_interval_cols(df: pd.DataFrame, *, copy: bool = True) -> pd.DataFrame:
    """Convert Interval columns to strings.

    PyArrow cannot serialise pandas ``IntervalDtype`` to Parquet, and
    JSON/browser renderers display them as ``[object Object]``.  This
    helper converts any Interval or Categorical-with-Interval columns
    to plain strings.

    When *copy* is True (default) the original DataFrame is not mutated.
    Pass ``copy=False`` to modify in place.
    """
    interval_cols = [
        c
        for c in df.columns
        if isinstance(df[c].dtype, pd.IntervalDtype)
        or _is_categorical_interval(df[c].dtype)
    ]
    if not interval_cols:
        return df
    if copy:
        df = df.copy()
    for col in interval_cols:
        df[col] = df[col].astype(str)
    return df
