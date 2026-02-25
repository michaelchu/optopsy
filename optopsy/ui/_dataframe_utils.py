"""Shared DataFrame utilities for the UI layer."""

import pandas as pd


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
        or (
            isinstance(df[c].dtype, pd.CategoricalDtype)
            and isinstance(df[c].dtype.categories.dtype, pd.IntervalDtype)
        )
    ]
    if not interval_cols:
        return df
    if copy:
        df = df.copy()
    for col in interval_cols:
        df[col] = df[col].astype(str)
    return df
