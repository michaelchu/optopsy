"""Data quality check tool handler: check_data_quality."""

import pandas as pd

from ._executor import (
    _STRIKE_THRESHOLDS,
    _check_per_date_uniqueness,
    _register,
    _require_dataset,
)
from ._schemas import CALENDAR_STRATEGIES, STRATEGY_OPTION_TYPE


@_register("check_data_quality")
def _handle_check_data_quality(arguments, dataset, signals, datasets, results, _result):
    active_ds, label, err = _require_dataset(arguments, dataset, datasets, _result)
    if err:
        return err
    assert active_ds is not None

    df = active_ds
    findings: list[str] = []
    display_parts: list[str] = [f"### Data Quality: {label}\n"]

    # ---------------------------------------------------------------
    # 1. Required columns check
    # ---------------------------------------------------------------
    _CORE_REQUIRED_COLS: dict[str, tuple[str, ...]] = {
        "underlying_symbol": ("object", "str"),
        "option_type": ("object", "str"),
        "expiration": ("datetime64[ns]", "datetime64[us]"),
        "quote_date": ("datetime64[ns]", "datetime64[us]"),
        "strike": ("int64", "float64"),
        "bid": ("int64", "float64"),
        "ask": ("int64", "float64"),
        "delta": ("int64", "float64"),
    }

    df_types = df.dtypes.astype(str).to_dict()
    missing_cols: list[str] = []
    dtype_mismatches: list[str] = []
    for col, expected in _CORE_REQUIRED_COLS.items():
        if col not in df_types:
            missing_cols.append(col)
        elif all(df_types[col] != t for t in expected):
            dtype_mismatches.append(f"{col} (got {df_types[col]})")

    if missing_cols:
        findings.append(f"FAIL: missing required columns: {', '.join(missing_cols)}")
        display_parts.append(
            f"**Required Columns** — MISSING: {', '.join(missing_cols)}\n"
        )
    elif dtype_mismatches:
        findings.append(f"WARN: dtype mismatches: {'; '.join(dtype_mismatches)}")
        display_parts.append(
            f"**Required Columns** — dtype mismatches: {'; '.join(dtype_mismatches)}\n"
        )
    else:
        findings.append("PASS: all 8 required columns present with correct dtypes")
        display_parts.append(
            "**Required Columns** — all 8 present with correct dtypes\n"
        )

    # ---------------------------------------------------------------
    # 2. Optional columns availability
    # ---------------------------------------------------------------
    _OPTIONAL_COLS = {
        "greeks": ["gamma", "theta", "vega"],
        "volatility": ["implied_volatility"],
        "liquidity": ["volume", "open_interest"],
    }
    available_optional: list[str] = []
    for _group, cols in _OPTIONAL_COLS.items():
        present = [c for c in cols if c in df.columns]
        available_optional.extend(present)

    if available_optional:
        features: list[str] = []
        if "implied_volatility" in available_optional:
            features.append("IV surface/signals available")
        if "volume" in available_optional:
            features.append("liquidity slippage available")
        feat_str = "; ".join(features) if features else ""
        findings.append(
            f"INFO: optional columns available: {', '.join(available_optional)}"
            + (f" ({feat_str})" if feat_str else "")
        )
        display_parts.append(
            f"**Optional Columns** — {', '.join(available_optional)}\n"
        )
    else:
        findings.append("INFO: no optional columns (Greeks, volume, IV) found")
        display_parts.append("**Optional Columns** — none found\n")

    # ---------------------------------------------------------------
    # 3. Null analysis on critical columns
    # ---------------------------------------------------------------
    _NULL_CHECK_COLS = [
        "delta",
        "bid",
        "ask",
        "volume",
        "open_interest",
    ]
    null_rows: list[str] = []
    null_display_rows: list[str] = []
    n_rows = len(df)
    for col in _NULL_CHECK_COLS:
        if col not in df.columns:
            continue
        n_null = int(df[col].isna().sum())
        if n_null > 0:
            pct = n_null / n_rows * 100
            null_rows.append(f"{col} {pct:.1f}% null")
            null_display_rows.append(f"| {col} | {n_null:,} | {pct:.1f}% |")

    if null_rows:
        findings.append(f"WARN: {'; '.join(null_rows)}")
        display_parts.append(
            "**Null Analysis**\n\n"
            "| Column | Null Count | % |\n|---|---|---|\n"
            + "\n".join(null_display_rows)
            + "\n"
        )
    else:
        present_checked = [c for c in _NULL_CHECK_COLS if c in df.columns]
        if present_checked:
            display_parts.append(
                f"**Null Analysis** — no nulls in {', '.join(present_checked)}\n"
            )

    # ---------------------------------------------------------------
    # 4. Bid/ask quality
    # ---------------------------------------------------------------
    if "bid" in df.columns and "ask" in df.columns:
        bid = pd.to_numeric(df["bid"], errors="coerce")
        ask = pd.to_numeric(df["ask"], errors="coerce")

        # Zero-bid rows
        non_null_bid = bid.dropna()
        n_zero_bid = int((non_null_bid == 0).sum())
        zero_bid_pct = n_zero_bid / n_rows * 100 if n_rows > 0 else 0

        # Crossed markets (bid > ask), ignoring NaN
        valid_mask = bid.notna() & ask.notna()
        n_crossed = int((bid[valid_mask] > ask[valid_mask]).sum())

        # Spread stats
        spread = (ask - bid).dropna()
        if not spread.empty:
            spread_mean = float(spread.mean())
            spread_median = float(spread.median())
            spread_max = float(spread.max())
        else:
            spread_mean = spread_median = spread_max = 0.0

        ba_parts: list[str] = []
        if n_zero_bid > 0:
            ba_parts.append(f"{zero_bid_pct:.1f}% zero-bid rows")
        if n_crossed > 0:
            ba_parts.append(f"{n_crossed:,} crossed markets (bid > ask)")

        if ba_parts:
            findings.append(f"WARN: {'; '.join(ba_parts)}")
        else:
            findings.append("PASS: no zero-bid or crossed-market rows")

        display_parts.append(
            "**Bid/Ask Quality**\n\n"
            f"| Metric | Value |\n|---|---|\n"
            f"| Zero-bid rows | {n_zero_bid:,} ({zero_bid_pct:.1f}%) |\n"
            f"| Crossed markets | {n_crossed:,} |\n"
            f"| Spread mean | {spread_mean:.4f} |\n"
            f"| Spread median | {spread_median:.4f} |\n"
            f"| Spread max | {spread_max:.4f} |\n"
        )

    # ---------------------------------------------------------------
    # 5. Date coverage & gaps + 6. Monthly row distribution
    # ---------------------------------------------------------------
    _parsed_dates = (
        pd.to_datetime(df["quote_date"], errors="coerce").dropna()
        if "quote_date" in df.columns
        else pd.Series(dtype="datetime64[ns]")
    )

    if not _parsed_dates.empty:
        date_min = _parsed_dates.min().date()
        date_max = _parsed_dates.max().date()
        unique_dates = sorted(_parsed_dates.dt.date.unique())
        n_unique = len(unique_dates)

        # Find gaps > 4 calendar days (non-trading day gaps)
        gaps: list[str] = []
        for i in range(1, len(unique_dates)):
            gap_days = (unique_dates[i] - unique_dates[i - 1]).days
            if gap_days > 4:
                gaps.append(f"{unique_dates[i - 1]} → {unique_dates[i]} ({gap_days}d)")

        gap_str = f", {len(gaps)} gap(s) > 4d" if gaps else ", no gaps"
        findings.append(
            f"INFO: quote_date {date_min} to {date_max}, "
            f"{n_unique} trading days{gap_str}"
        )
        display_parts.append(
            f"**Date Coverage**\n\n"
            f"Range: {date_min} to {date_max} ({n_unique} unique trading days)\n"
        )
        if gaps:
            gap_lines = "\n".join(f"- {g}" for g in gaps[:10])
            if len(gaps) > 10:
                gap_lines += f"\n- ... and {len(gaps) - 10} more"
            display_parts.append(f"Gaps (> 4 calendar days):\n{gap_lines}\n")

    if not _parsed_dates.empty:
        monthly = _parsed_dates.dt.to_period("M").value_counts().sort_index()
        min_month = monthly.idxmin()
        min_count = int(monthly.min())
        max_count = int(monthly.max())
        median_count = int(monthly.median())

        # Flag thin months (< 25% of median)
        thin_threshold = median_count * 0.25
        thin_months = monthly[monthly < thin_threshold]  # type: ignore[operator]
        if not thin_months.empty:
            thin_list = [f"{str(p)} ({c:,})" for p, c in thin_months.items()]
            findings.append(
                f"WARN: {len(thin_list)} thin month(s) "
                f"(< 25% of median {median_count:,}): " + ", ".join(thin_list[:5])
            )
        display_parts.append(
            f"**Monthly Distribution** — "
            f"min {min_count:,} ({min_month}), "
            f"median {median_count:,}, max {max_count:,} rows/month\n"
        )

    # ---------------------------------------------------------------
    # 7. Duplicate rows
    # ---------------------------------------------------------------
    _DEDUP_COLS = ["quote_date", "expiration", "strike", "option_type"]
    dedup_present = [c for c in _DEDUP_COLS if c in df.columns]
    if len(dedup_present) == len(_DEDUP_COLS):
        n_dupes = int(df.duplicated(subset=_DEDUP_COLS).sum())
        if n_dupes > 0:
            dupe_pct = n_dupes / n_rows * 100 if n_rows > 0 else 0
            findings.append(
                f"WARN: {n_dupes:,} duplicate rows ({dupe_pct:.1f}%) "
                f"on ({', '.join(_DEDUP_COLS)})"
            )
            display_parts.append(
                f"**Duplicate Rows** — {n_dupes:,} duplicates "
                f"({dupe_pct:.1f}%) on ({', '.join(_DEDUP_COLS)})\n"
            )
        else:
            findings.append("PASS: no duplicate rows")
            display_parts.append("**Duplicate Rows** — none found\n")

    # ---------------------------------------------------------------
    # 8. Negative values
    # ---------------------------------------------------------------
    _NEG_CHECK_COLS = ["bid", "ask", "strike"]
    neg_parts: list[str] = []
    neg_display: list[str] = []
    for col in _NEG_CHECK_COLS:
        if col not in df.columns:
            continue
        numeric_col = pd.to_numeric(df[col], errors="coerce")
        n_neg = int((numeric_col < 0).sum())
        if n_neg > 0:
            neg_parts.append(f"{col} has {n_neg:,} negative values")
            neg_display.append(f"| {col} | {n_neg:,} |")
    if neg_parts:
        findings.append(f"WARN: {'; '.join(neg_parts)}")
        display_parts.append(
            "**Negative Values**\n\n"
            "| Column | Count |\n|---|---|\n" + "\n".join(neg_display) + "\n"
        )
    else:
        present_neg = [c for c in _NEG_CHECK_COLS if c in df.columns]
        if present_neg:
            findings.append("PASS: no negative bid/ask/strike values")
            display_parts.append("**Negative Values** — none found\n")

    # ---------------------------------------------------------------
    # 9-11. Strategy-specific checks
    # ---------------------------------------------------------------
    strategy_name = arguments.get("strategy_name")

    # 9. Option type balance
    if strategy_name and "option_type" in df.columns:
        required_type = STRATEGY_OPTION_TYPE.get(strategy_name)
        types_present = set(df["option_type"].dropna().unique())

        if required_type is None:
            # Strategy needs both calls and puts
            missing_types = {"call", "put"} - types_present
            if missing_types:
                findings.append(
                    f"FAIL: {strategy_name} requires both calls and puts, "
                    f"but missing: {', '.join(sorted(missing_types))}"
                )
                display_parts.append(
                    f"**Option Type Balance** — MISSING "
                    f"{', '.join(sorted(missing_types))} "
                    f"(required for {strategy_name})\n"
                )
            else:
                call_count = int((df["option_type"] == "call").sum())
                put_count = int((df["option_type"] == "put").sum())
                findings.append(
                    f"PASS: both calls ({call_count:,}) and puts "
                    f"({put_count:,}) present for {strategy_name}"
                )
                display_parts.append(
                    f"**Option Type Balance** — calls: {call_count:,}, "
                    f"puts: {put_count:,}\n"
                )
        else:
            # Strategy needs a specific type
            if required_type not in types_present:
                findings.append(
                    f"FAIL: {strategy_name} requires '{required_type}' options, "
                    f"but only found: {', '.join(sorted(types_present))}"
                )
                display_parts.append(
                    f"**Option Type Balance** — MISSING '{required_type}' "
                    f"(required for {strategy_name})\n"
                )
            else:
                required_count = int((df["option_type"] == required_type).sum())
                findings.append(
                    f"PASS: required option type '{required_type}' present "
                    f"({required_count:,}) for {strategy_name}"
                )
                display_parts.append(
                    f"**Option Type Balance** — '{required_type}' options: "
                    f"{required_count:,}\n"
                )

    # 10. Strike density
    if (
        strategy_name
        and strategy_name in _STRIKE_THRESHOLDS
        and "quote_date" in df.columns
        and "strike" in df.columns
    ):
        _check_per_date_uniqueness(
            df,
            "strike",
            _STRIKE_THRESHOLDS[strategy_name],
            "Strike Density",
            "distinct strikes",
            strategy_name,
            findings,
            display_parts,
        )

    # 11. Expiration coverage (calendar/diagonal strategies)
    if (
        strategy_name
        and strategy_name in CALENDAR_STRATEGIES
        and "quote_date" in df.columns
        and "expiration" in df.columns
    ):
        _check_per_date_uniqueness(
            df,
            "expiration",
            2,
            "Expiration Coverage",
            "distinct expirations",
            strategy_name,
            findings,
            display_parts,
        )

    # ---------------------------------------------------------------
    # 12. Actionable recommendations
    # ---------------------------------------------------------------
    recommendations: list[str] = []
    # Slippage recommendation
    if "volume" in df.columns:
        vol_null_pct = df["volume"].isna().sum() / n_rows * 100 if n_rows > 0 else 0
        if vol_null_pct > 10:
            recommendations.append(
                f"use slippage='mid' (volume is {vol_null_pct:.0f}% null)"
            )
        else:
            recommendations.append(
                "volume data available — slippage='liquidity' viable"
            )
    else:
        recommendations.append("use slippage='mid' or 'spread' (no volume column)")

    if recommendations:
        findings.append("RECO: " + "; ".join(recommendations))
        display_parts.append(
            "**Recommendations**\n\n"
            + "\n".join(f"- {r}" for r in recommendations)
            + "\n"
        )

    # ---------------------------------------------------------------
    # Build output
    # ---------------------------------------------------------------
    llm_summary = (
        f"check_data_quality({label}): {len(findings)} findings\n"
        + "\n".join(f"- {f}" for f in findings)
    )
    user_display = "\n".join(display_parts)
    return _result(llm_summary, user_display=user_display)
