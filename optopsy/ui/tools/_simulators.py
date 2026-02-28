"""Simulation tool handlers: simulate, get_simulation_trades."""

from ..providers.result_store import ResultStore
from ._executor import _fmt_pf, _register
from ._helpers import (
    _SIM_PARAM_KEYS,
    _build_strat_kwargs,
    _df_to_markdown,
    _pop_internal_keys,
    _resolve_result_key,
    _resolve_signals_for_strategy,
    _session_result_key,
    _validate_strategy_and_dataset,
    _with_cache_key,
)


@_register("simulate")
def _handle_simulate(arguments, dataset, signals, datasets, results, _result):
    from optopsy.simulator import simulate as _simulate

    strategy_name, func, active_ds, err = _validate_strategy_and_dataset(
        arguments, dataset, datasets, _result
    )
    if err:
        return err
    assert active_ds is not None

    ds_fp = _pop_internal_keys(arguments)

    # Extract simulation-specific params
    sim_params: dict = {}
    for key in _SIM_PARAM_KEYS:
        if key in arguments:
            sim_params[key] = arguments[key]

    # Build strategy kwargs — strip sim-specific and signal keys
    strat_kwargs = _build_strat_kwargs(
        arguments, strategy_name, extra_exclude=_SIM_PARAM_KEYS
    )

    # Resolve entry/exit signals (slots and inline) via shared helper
    sig_update, sig_err = _resolve_signals_for_strategy(arguments, signals, active_ds)
    if sig_err:
        return _result(sig_err)
    strat_kwargs.update(sig_update)

    store = ResultStore()
    all_params = {**sim_params, **strat_kwargs}

    # For cache: we need to handle the simulation differently because
    # on cache hit we need the summary from metadata, not re-derived.
    cache_key = (
        store.make_key(f"sim:{strategy_name}", all_params, ds_fp) if ds_fp else None
    )

    trade_log = None
    s = None
    cache_hit = bool(cache_key and store.has(cache_key))

    if cache_hit:
        trade_log = store.read(cache_key)
        s = (store.get_metadata(cache_key) or {}).get("summary")
        # Fall back to re-executing if cached summary is missing/corrupt
        if not isinstance(s, dict) or not s:
            cache_hit = False
            trade_log = None
            s = None

    if not cache_hit:
        try:
            result = _simulate(active_ds, func, **sim_params, **strat_kwargs)
        except Exception as e:
            return _result(f"Error running simulation: {e}")

        trade_log = result.trade_log
        s = result.summary

        if cache_key and not trade_log.empty:
            try:
                store.write(
                    cache_key,
                    trade_log,
                    {
                        "type": "simulation",
                        "strategy": strategy_name,
                        "display_key": f"sim:{strategy_name}",
                        "params": {
                            k: v
                            for k, v in all_params.items()
                            if isinstance(v, (str, int, float, bool, type(None)))
                        },
                        "summary": s,
                    },
                )
            except OSError:
                pass

    if trade_log is None or trade_log.empty or not s or s.get("total_trades", 0) == 0:
        return _result(f"simulate({strategy_name}): no trades generated.")

    # Build human-readable display key from all params
    key_parts = [f"sim:{strategy_name}"]
    for k in sorted(arguments.keys()):
        if k not in ("strategy_name", "dataset_name", "_dataset_fingerprint"):
            key_parts.append(f"{k}={arguments[k]}")
    sim_display_key = ":".join(key_parts) if len(key_parts) > 1 else key_parts[0]
    sim_session_key = _session_result_key(cache_key, sim_display_key)

    from ._models import SimulationResultEntry

    updated_results = dict(results)
    entry = SimulationResultEntry(
        strategy=strategy_name,
        display_key=sim_display_key,
        dataset_fingerprint=ds_fp,
        summary=s,
    ).model_dump()
    updated_results[sim_session_key] = _with_cache_key(entry, cache_key)

    # Format output
    pf_str = _fmt_pf(s["profit_factor"])
    llm_summary = (
        f"simulate({strategy_name}): {s['total_trades']} trades, "
        f"win_rate={s['win_rate']:.1%}, "
        f"total_return={s['total_return']:.2%}, "
        f"max_drawdown={s['max_drawdown']:.2%}, "
        f"profit_factor={pf_str}, "
        f"sharpe={s['sharpe_ratio']:.2f}, "
        f"sortino={s['sortino_ratio']:.2f}"
    )

    # Summary stats table
    stats_rows = [
        ("Total Trades", s["total_trades"]),
        ("Winning Trades", s["winning_trades"]),
        ("Losing Trades", s["losing_trades"]),
        ("Win Rate", f"{s['win_rate']:.1%}"),
        ("Total P&L", f"${s['total_pnl']:,.2f}"),
        ("Total Return", f"{s['total_return']:.2%}"),
        ("Avg P&L", f"${s['avg_pnl']:,.2f}"),
        ("Avg Win", f"${s['avg_win']:,.2f}"),
        ("Avg Loss", f"${s['avg_loss']:,.2f}"),
        ("Max Win", f"${s['max_win']:,.2f}"),
        ("Max Loss", f"${s['max_loss']:,.2f}"),
        ("Profit Factor", pf_str),
        ("Max Drawdown", f"{s['max_drawdown']:.2%}"),
        ("Avg Days in Trade", f"{s['avg_days_in_trade']:.1f}"),
        ("Sharpe Ratio", f"{s['sharpe_ratio']:.2f}"),
        ("Sortino Ratio", f"{s['sortino_ratio']:.2f}"),
        ("VaR (95%)", f"{s['var_95']:.2%}"),
        ("CVaR (95%)", f"{s['cvar_95']:.2%}"),
        ("Calmar Ratio", f"{s['calmar_ratio']:.2f}"),
    ]
    stats_table = "| Metric | Value |\n|---|---|\n"
    stats_table += "\n".join(f"| {m} | {v} |" for m, v in stats_rows)

    # Trade log preview
    preview_cols = [
        "trade_id",
        "entry_date",
        "exit_date",
        "days_held",
        "entry_cost",
        "exit_proceeds",
        "realized_pnl",
        "equity",
    ]
    available_cols = [c for c in preview_cols if c in trade_log.columns]
    preview = trade_log[available_cols].head(20)

    user_display = (
        f"### Simulation: {strategy_name}\n\n"
        f"{stats_table}\n\n"
        f"**Trade Log** (first {min(20, len(trade_log))} of "
        f"{len(trade_log)} trades)\n\n"
        f"{_df_to_markdown(preview)}"
    )

    return _result(llm_summary, user_display=user_display, res=updated_results)


@_register("get_simulation_trades")
def _handle_get_simulation_trades(
    arguments, dataset, signals, datasets, results, _result
):
    sim_key = arguments.get("simulation_key")

    # Find the simulation result
    if sim_key:
        canonical = _resolve_result_key(results, sim_key)
        entry = results.get(canonical) if canonical else None
        if entry is None or entry.get("type") != "simulation":
            sim_keys = [
                v.get("display_key", k)
                for k, v in results.items()
                if v.get("type") == "simulation"
            ]
            return _result(
                f"No simulation found for key '{sim_key}'. "
                f"Available: {sim_keys or 'none — run simulate first'}"
            )
        sim_key = canonical
    else:
        # Find most recent simulation
        sim_entries = [
            (k, v) for k, v in results.items() if v.get("type") == "simulation"
        ]
        if not sim_entries:
            return _result("No simulations run yet. Use simulate first.")
        sim_key, entry = sim_entries[-1]

    display_label = entry.get("display_key", sim_key)

    # Read trade log from ResultStore via _cache_key
    cache_key = entry.get("_cache_key")
    store = ResultStore()
    trade_log = store.read(cache_key) if cache_key else None

    if trade_log is None:
        return _result(f"Simulation '{display_label}' has no cached trade log.")

    llm_summary = f"get_simulation_trades({display_label}): {len(trade_log)} trades"
    user_display = f"### Trade Log: {display_label}\n\n{_df_to_markdown(trade_log)}"
    return _result(llm_summary, user_display=user_display)
