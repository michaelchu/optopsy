"""Simulation tool handlers: simulate, get_simulation_trades."""

from ._executor import _fmt_pf, _register, _require_dataset
from ._helpers import (
    _SIGNAL_PARAM_KEYS,
    _SIM_PARAM_KEYS,
    _df_to_markdown,
    _resolve_signals_for_strategy,
    read_sim_trade_log,
    write_sim_trade_log,
)
from ._schemas import (
    CALENDAR_EXTRA_PARAMS,
    CALENDAR_STRATEGIES,
    STRATEGIES,
    STRATEGY_NAMES,
)


@_register("simulate")
def _handle_simulate(arguments, dataset, signals, datasets, results, _result):
    from optopsy.simulator import simulate as _simulate

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

    func, _, _ = STRATEGIES[strategy_name]

    # Extract simulation-specific params
    sim_params: dict = {}
    for key in _SIM_PARAM_KEYS:
        if key in arguments:
            sim_params[key] = arguments[key]

    # Build strategy kwargs — strip sim-specific and signal keys
    _non_strat_keys = _SIGNAL_PARAM_KEYS | _SIM_PARAM_KEYS | {"dataset_name"}
    strat_kwargs = {
        k: v
        for k, v in arguments.items()
        if k not in _non_strat_keys
        and (strategy_name in CALENDAR_STRATEGIES or k not in CALENDAR_EXTRA_PARAMS)
    }

    # Resolve entry/exit signals (slots and inline) via shared helper
    sig_update, sig_err = _resolve_signals_for_strategy(arguments, signals, active_ds)
    if sig_err:
        return _result(sig_err)
    strat_kwargs.update(sig_update)

    try:
        result = _simulate(active_ds, func, **sim_params, **strat_kwargs)
    except Exception as e:
        return _result(f"Error running simulation: {e}")

    s = result.summary
    if s["total_trades"] == 0:
        return _result(f"simulate({strategy_name}): no trades generated.")

    # Build result key — include all params that affect output
    key_parts = [f"sim:{strategy_name}"]
    for k in sorted(arguments.keys()):
        if k not in ("strategy_name", "dataset_name"):
            key_parts.append(f"{k}={arguments[k]}")
    sim_key = ":".join(key_parts) if len(key_parts) > 1 else key_parts[0]

    # Persist trade log to disk; keep only summary stats in session memory
    write_sim_trade_log(sim_key, result.trade_log)

    from ._models import SimulationResultEntry

    updated_results = dict(results)
    updated_results[sim_key] = SimulationResultEntry(
        strategy=strategy_name,
        summary=s,
    ).model_dump()

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
    available_cols = [c for c in preview_cols if c in result.trade_log.columns]
    preview = result.trade_log[available_cols].head(20)

    user_display = (
        f"### Simulation: {strategy_name}\n\n"
        f"{stats_table}\n\n"
        f"**Trade Log** (first {min(20, len(result.trade_log))} of "
        f"{len(result.trade_log)} trades)\n\n"
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
        entry = results.get(sim_key)
        if entry is None or entry.get("type") != "simulation":
            sim_keys = [k for k, v in results.items() if v.get("type") == "simulation"]
            return _result(
                f"No simulation found for key '{sim_key}'. "
                f"Available: {sim_keys or 'none — run simulate first'}"
            )
    else:
        # Find most recent simulation
        sim_entries = [
            (k, v) for k, v in results.items() if v.get("type") == "simulation"
        ]
        if not sim_entries:
            return _result("No simulations run yet. Use simulate first.")
        sim_key, entry = sim_entries[-1]

    trade_log = read_sim_trade_log(sim_key)
    if trade_log is None:
        return _result(f"Simulation '{sim_key}' has no trades.")

    llm_summary = f"get_simulation_trades({sim_key}): {len(trade_log)} trades"
    user_display = f"### Trade Log: {sim_key}\n\n{_df_to_markdown(trade_log)}"
    return _result(llm_summary, user_display=user_display)
