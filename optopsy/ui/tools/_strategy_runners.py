"""Strategy execution tool handlers: run_strategy, scan_strategies."""

import itertools as _itertools

import pandas as pd

from ..providers.result_store import ResultStore
from ._executor import _register, _require_dataset
from ._helpers import (
    _build_strat_kwargs,
    _cached_run,
    _df_to_markdown,
    _make_result_key,
    _make_result_summary,
    _pop_internal_keys,
    _resolve_signals_for_strategy,
    _run_one_strategy,
    _strategy_llm_summary,
    _validate_strategy_and_dataset,
    _with_cache_key,
)
from ._schemas import (
    CALENDAR_STRATEGIES,
    STRATEGIES,
    STRATEGY_NAMES,
)


@_register("run_strategy")
def _handle_run_strategy(arguments, dataset, signals, datasets, results, _result):
    strategy_name, func, active_ds, err = _validate_strategy_and_dataset(
        arguments, dataset, datasets, _result
    )
    if err:
        return err
    assert active_ds is not None
    dataset = active_ds

    ds_fp = _pop_internal_keys(arguments)
    strat_kwargs = _build_strat_kwargs(arguments, strategy_name)

    # Resolve entry/exit signals (slots and inline) via shared helper
    sig_update, sig_err = _resolve_signals_for_strategy(arguments, signals, dataset)
    if sig_err:
        return _result(sig_err)
    strat_kwargs.update(sig_update)

    store = ResultStore()
    result_df, cache_key, run_err = _cached_run(
        store,
        strategy_name,
        strat_kwargs,
        ds_fp,
        execute_fn=lambda: _run_one_strategy(strategy_name, dataset, strat_kwargs),
        metadata={
            "type": "strategy",
            "strategy": strategy_name,
            "display_key": _make_result_key(strategy_name, arguments),
            "params": {
                k: v for k, v in strat_kwargs.items() if not isinstance(v, pd.DataFrame)
            },
        },
    )
    if run_err:
        return _result(f"Error running {strategy_name}: {run_err}")
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
    llm_summary = _strategy_llm_summary(result_df, strategy_name, mode)
    result_key = _make_result_key(strategy_name, arguments)
    summary = _make_result_summary(strategy_name, result_df, arguments)
    updated_results = {
        **results,
        result_key: _with_cache_key(summary, cache_key),
    }
    return _result(
        llm_summary, user_display=display, res=updated_results, result_df=result_df
    )


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

    ds_fp = _pop_internal_keys(arguments)

    max_combos = int(arguments.get("max_combinations", 50))
    slippage = arguments.get("slippage", "mid")
    dte_values = arguments.get("max_entry_dte_values") or [90]
    exit_values = arguments.get("exit_dte_values") or [0]

    all_combos = list(_itertools.product(strategy_names, dte_values, exit_values))
    truncated = len(all_combos) > max_combos
    combos_to_run = all_combos[:max_combos]

    store = ResultStore()
    rows = []
    errors = []
    scan_results = dict(results)

    for strat, max_dte, exit_dte in combos_to_run:
        if strat in CALENDAR_STRATEGIES:
            errors.append(
                f"{strat}: skipped (calendar strategy — no front/back DTE sweep; "
                "use run_strategy directly)"
            )
            continue

        combo_args = {
            "max_entry_dte": max_dte,
            "exit_dte": exit_dte,
            "slippage": slippage,
        }

        result_df, cache_key, combo_err = _cached_run(
            store,
            strat,
            combo_args,
            ds_fp,
            execute_fn=lambda s=strat, a=combo_args, ds=active_ds: _run_one_strategy(
                s, ds, a
            ),
            metadata={
                "type": "strategy",
                "strategy": strat,
                "display_key": _make_result_key(strat, combo_args),
                "params": combo_args,
            },
        )

        if combo_err:
            errors.append(f"{strat}(dte={max_dte},exit={exit_dte}): {combo_err}")
            continue

        if result_df is None or result_df.empty:
            rows.append(
                {
                    "strategy": strat,
                    "max_entry_dte": max_dte,
                    "exit_dte": exit_dte,
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
                "count": summary["count"],
                "mean_return": summary["mean_return"],
                "std": summary["std"],
                "win_rate": summary["win_rate"],
                "profit_factor": summary["profit_factor"],
            }
        )
        key = _make_result_key(strat, combo_args)
        scan_results[key] = _with_cache_key(
            {**summary, "source": "scan_strategies"}, cache_key
        )

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
            f"(dte={best['max_entry_dte']}, exit={best['exit_dte']}) — "
            f"mean={best['mean_return']:.4f}, win_rate={best['win_rate']:.2%}"
        )

    llm_summary = "\n".join(header_parts)
    table = _df_to_markdown(leaderboard)
    user_display = f"### Strategy Scan Results\n\n{llm_summary}\n\n{table}"

    return _result(
        llm_summary, user_display=user_display, res=scan_results, result_df=leaderboard
    )
