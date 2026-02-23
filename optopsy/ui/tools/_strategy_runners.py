"""Strategy execution tool handlers: run_strategy, scan_strategies."""

import itertools as _itertools

import pandas as pd

from ._executor import _register, _require_dataset
from ._helpers import (
    _SIGNAL_PARAM_KEYS,
    _df_to_markdown,
    _make_result_key,
    _make_result_summary,
    _resolve_signals_for_strategy,
    _run_one_strategy,
    _strategy_llm_summary,
)
from ._schemas import (
    CALENDAR_EXTRA_PARAMS,
    CALENDAR_STRATEGIES,
    STRATEGIES,
    STRATEGY_NAMES,
)


@_register("run_strategy")
def _handle_run_strategy(arguments, dataset, signals, datasets, results, _result):
    strategy_name = arguments.get("strategy_name")
    if not strategy_name or strategy_name not in STRATEGIES:
        return _result(
            f"Unknown strategy '{strategy_name}'. "
            f"Available: {', '.join(STRATEGY_NAMES)}",
        )
    active_ds, _, err = _require_dataset(arguments, dataset, datasets, _result)
    if err:
        return err
    assert active_ds is not None
    dataset = active_ds  # shadow for the rest of the block
    func, _, _ = STRATEGIES[strategy_name]
    # Build a clean kwargs dict without mutating the original arguments.
    # Strip signal params — handled separately below.
    strat_kwargs = {
        k: v
        for k, v in arguments.items()
        if k not in _SIGNAL_PARAM_KEYS
        and (strategy_name in CALENDAR_STRATEGIES or k not in CALENDAR_EXTRA_PARAMS)
    }

    # Resolve entry/exit signals (slots and inline) via shared helper
    sig_update, sig_err = _resolve_signals_for_strategy(arguments, signals, dataset)
    if sig_err:
        return _result(sig_err)
    strat_kwargs.update(sig_update)

    result_df, err = _run_one_strategy(strategy_name, dataset, strat_kwargs)
    if err:
        return _result(f"Error running {strategy_name}: {err}")
    if result_df is None or result_df.empty:
        params_used = {k: v for k, v in arguments.items() if k != "strategy_name"}
        return _result(
            f"{strategy_name} returned no results with parameters: "
            f"{params_used or 'defaults'}.",
        )
    is_raw = arguments.get("raw", False)
    mode = "raw trades" if is_raw else "aggregated stats"
    table = _df_to_markdown(result_df)
    display = f"**{strategy_name}** — {len(result_df)} {mode}\n\n{table}"
    # LLM gets a compact summary instead of a full table to save tokens.
    llm_summary = _strategy_llm_summary(result_df, strategy_name, mode)
    result_key = _make_result_key(strategy_name, arguments)
    updated_results = {
        **results,
        result_key: _make_result_summary(strategy_name, result_df, arguments),
    }
    return _result(llm_summary, user_display=display, res=updated_results)


@_register("scan_strategies")
def _handle_scan_strategies(arguments, dataset, signals, datasets, results, _result):
    strategy_names = arguments.get("strategy_names", [])
    if not strategy_names:
        return _result("'strategy_names' must be a non-empty list.")
    invalid = [s for s in strategy_names if s not in STRATEGIES]
    if invalid:
        return _result(
            f"Unknown strategies: {invalid}. Available: {', '.join(STRATEGY_NAMES)}"
        )

    active_ds, _, err = _require_dataset(arguments, dataset, datasets, _result)
    if err:
        return err
    assert active_ds is not None

    max_combos = int(arguments.get("max_combinations", 50))
    slippage = arguments.get("slippage", "mid")
    dte_values = arguments.get("max_entry_dte_values") or [90]
    exit_values = arguments.get("exit_dte_values") or [0]
    otm_values = arguments.get("max_otm_pct_values") or [0.5]

    all_combos = list(
        _itertools.product(strategy_names, dte_values, exit_values, otm_values)
    )
    truncated = len(all_combos) > max_combos
    combos_to_run = all_combos[:max_combos]

    rows = []
    errors = []
    scan_results = dict(results)

    for strat, max_dte, exit_dte, max_otm in combos_to_run:
        if strat in CALENDAR_STRATEGIES:
            errors.append(
                f"{strat}: skipped (calendar strategy — no front/back DTE sweep; "
                "use run_strategy directly)"
            )
            continue

        combo_args = {
            "max_entry_dte": max_dte,
            "exit_dte": exit_dte,
            "max_otm_pct": max_otm,
            "slippage": slippage,
        }
        result_df, err = _run_one_strategy(strat, active_ds, combo_args)

        if err:
            errors.append(
                f"{strat}(dte={max_dte},exit={exit_dte},otm={max_otm:.2f}): {err}"
            )
            continue

        if result_df is None or result_df.empty:
            rows.append(
                {
                    "strategy": strat,
                    "max_entry_dte": max_dte,
                    "exit_dte": exit_dte,
                    "max_otm_pct": max_otm,
                    "count": 0,
                    "mean_return": float("nan"),
                    "std": float("nan"),
                    "win_rate": float("nan"),
                    "profit_factor": float("nan"),
                }
            )
            continue

        summary = _make_result_summary(strat, result_df, combo_args)
        rows.append(
            {
                "strategy": strat,
                "max_entry_dte": max_dte,
                "exit_dte": exit_dte,
                "max_otm_pct": max_otm,
                "count": summary["count"],
                "mean_return": summary["mean_return"],
                "std": summary["std"],
                "win_rate": summary["win_rate"],
                "profit_factor": summary["profit_factor"],
            }
        )
        key = _make_result_key(strat, combo_args)
        scan_results[key] = {**summary, "source": "scan_strategies"}

    if not rows and not errors:
        return _result("scan_strategies: no combinations produced results.")

    leaderboard = (
        pd.DataFrame(rows)
        .sort_values("mean_return", ascending=False)
        .reset_index(drop=True)
    )
    n_ok = int(leaderboard["mean_return"].notna().sum())
    n_empty = int((leaderboard["count"] == 0).sum())

    header_parts = [
        f"scan_strategies: {len(combos_to_run)} combination(s) run, "
        f"{n_ok} with results, {n_empty} empty, {len(errors)} error(s)"
    ]
    if truncated:
        header_parts.append(
            f"WARNING: {len(all_combos) - max_combos} combination(s) skipped "
            f"(exceeded max_combinations={max_combos})"
        )
    if errors:
        header_parts.append("Errors/skipped: " + "; ".join(errors))

    best_rows = leaderboard[leaderboard["mean_return"].notna()]
    if not best_rows.empty:
        best = best_rows.iloc[0]
        header_parts.append(
            f"Best: {best['strategy']} "
            f"(dte={best['max_entry_dte']}, exit={best['exit_dte']}, "
            f"otm={best['max_otm_pct']:.2f}) — "
            f"mean={best['mean_return']:.4f}, win_rate={best['win_rate']:.2%}"
        )

    llm_summary = "\n".join(header_parts)
    table = _df_to_markdown(leaderboard)
    user_display = f"### Strategy Scan Results\n\n{llm_summary}\n\n{table}"
    return _result(llm_summary, user_display=user_display, res=scan_results)
