"""Tests for Pydantic tool argument models and schema generation."""

import pytest

pydantic = pytest.importorskip("pydantic", reason="UI extras not installed")
ValidationError = pydantic.ValidationError

from optopsy.ui.tools._models import (  # noqa: E402
    TOOL_ARG_MODELS,
    BuildSignalArgs,
    ClearCacheArgs,
    CreateChartArgs,
    DescribeDataArgs,
    FetchOptionsDataArgs,
    FetchStockDataArgs,
    GetSimulationTradesArgs,
    InspectCacheArgs,
    ListResultsArgs,
    ListSignalsArgs,
    PreviewDataArgs,
    PreviewSignalArgs,
    RunStrategyArgs,
    ScanStrategiesArgs,
    SimulateArgs,
    SimulationResultEntry,
    StrategyResultSummary,
    SuggestStrategyParamsArgs,
    pydantic_to_openai_params,
)

# ---------------------------------------------------------------------------
# Validation happy path
# ---------------------------------------------------------------------------


class TestValidationHappyPath:
    def test_preview_data_defaults(self):
        m = PreviewDataArgs.model_validate({})
        assert m.dataset_name is None
        assert m.rows is None

    def test_preview_data_with_values(self):
        m = PreviewDataArgs.model_validate(
            {"dataset_name": "SPY", "rows": 10, "position": "tail", "sample": True}
        )
        assert m.dataset_name == "SPY"
        assert m.rows == 10
        assert m.position.value == "tail"
        assert m.sample is True

    def test_describe_data_with_columns(self):
        m = DescribeDataArgs.model_validate(
            {"dataset_name": "AAPL", "columns": ["strike", "bid"]}
        )
        assert m.columns == ["strike", "bid"]

    def test_run_strategy_minimal(self):
        m = RunStrategyArgs.model_validate({"strategy_name": "long_calls"})
        assert m.strategy_name == "long_calls"
        assert m.max_entry_dte is None

    def test_run_strategy_full(self):
        m = RunStrategyArgs.model_validate(
            {
                "strategy_name": "iron_condor",
                "max_entry_dte": 45,
                "exit_dte": 7,
                "max_otm_pct": 0.15,
                "slippage": "spread",
                "entry_signal": "rsi_below",
                "entry_signal_params": {"period": 14, "threshold": 25},
                "entry_signal_days": 3,
                "dataset_name": "SPY",
            }
        )
        assert m.strategy_name == "iron_condor"
        assert m.max_entry_dte == 45
        assert m.slippage.value == "spread"
        assert m.entry_signal == "rsi_below"
        assert m.entry_signal_days == 3

    def test_scan_strategies(self):
        m = ScanStrategiesArgs.model_validate(
            {
                "strategy_names": ["long_calls", "short_puts"],
                "max_entry_dte_values": [30, 60],
                "exit_dte_values": [0, 7],
                "slippage": "mid",
            }
        )
        assert len(m.strategy_names) == 2
        assert m.max_entry_dte_values == [30, 60]

    def test_build_signal(self):
        m = BuildSignalArgs.model_validate(
            {
                "slot": "entry",
                "signals": [
                    {"name": "rsi_below", "params": {"threshold": 30}},
                    {"name": "sma_above", "days": 3},
                ],
                "combine": "and",
            }
        )
        assert m.slot == "entry"
        assert len(m.signals) == 2
        assert m.signals[0].name == "rsi_below"
        assert m.signals[1].days == 3

    def test_simulate_args(self):
        m = SimulateArgs.model_validate(
            {
                "strategy_name": "short_puts",
                "capital": 50000,
                "quantity": 2,
                "max_positions": 5,
                "selector": "nearest",
                "max_entry_dte": 45,
            }
        )
        assert m.capital == 50000
        assert m.selector.value == "nearest"

    def test_create_chart(self):
        m = CreateChartArgs.model_validate(
            {
                "chart_type": "line",
                "data_source": "simulation",
                "x": "entry_date",
                "y": "equity",
            }
        )
        assert m.chart_type.value == "line"
        assert m.data_source.value == "simulation"

    def test_create_chart_with_indicators(self):
        m = CreateChartArgs.model_validate(
            {
                "chart_type": "candlestick",
                "data_source": "stock",
                "symbol": "SPY",
                "indicators": [
                    {"type": "sma", "period": 50},
                    {"type": "rsi", "period": 14},
                ],
            }
        )
        assert len(m.indicators) == 2
        assert m.indicators[0].type.value == "sma"

    def test_fetch_options_data(self):
        m = FetchOptionsDataArgs.model_validate(
            {"symbol": "AAPL", "start_date": "2024-01-01", "option_type": "call"}
        )
        assert m.symbol == "AAPL"

    def test_fetch_stock_data(self):
        m = FetchStockDataArgs.model_validate({"symbol": "QQQ"})
        assert m.symbol == "QQQ"

    def test_get_simulation_trades_empty(self):
        m = GetSimulationTradesArgs.model_validate({})
        assert m.simulation_key is None

    def test_suggest_strategy_params(self):
        m = SuggestStrategyParamsArgs.model_validate({"strategy_name": "iron_condor"})
        assert m.strategy_name == "iron_condor"

    def test_list_signals_empty(self):
        m = ListSignalsArgs.model_validate({})
        assert m is not None

    def test_inspect_cache(self):
        m = InspectCacheArgs.model_validate({"symbol": "SPY"})
        assert m.symbol == "SPY"

    def test_clear_cache(self):
        m = ClearCacheArgs.model_validate({})
        assert m.symbol is None

    def test_preview_signal(self):
        m = PreviewSignalArgs.model_validate({"slot": "entry"})
        assert m.slot == "entry"

    def test_list_results(self):
        m = ListResultsArgs.model_validate({"strategy_name": "long_calls"})
        assert m.strategy_name == "long_calls"


# ---------------------------------------------------------------------------
# Validation rejection
# ---------------------------------------------------------------------------


class TestValidationRejection:
    def test_run_strategy_missing_required(self):
        with pytest.raises(ValidationError):
            RunStrategyArgs.model_validate({})

    def test_run_strategy_invalid_strategy(self):
        with pytest.raises(ValidationError, match="Unknown strategy"):
            RunStrategyArgs.model_validate({"strategy_name": "not_a_strategy"})

    def test_scan_strategies_empty_list(self):
        with pytest.raises(ValidationError):
            ScanStrategiesArgs.model_validate({"strategy_names": []})

    def test_scan_strategies_invalid_names(self):
        with pytest.raises(ValidationError, match="Unknown strategies"):
            ScanStrategiesArgs.model_validate(
                {"strategy_names": ["long_calls", "fake_strategy"]}
            )

    def test_build_signal_missing_slot(self):
        with pytest.raises(ValidationError):
            BuildSignalArgs.model_validate({"signals": [{"name": "rsi_below"}]})

    def test_build_signal_empty_signals(self):
        with pytest.raises(ValidationError):
            BuildSignalArgs.model_validate({"slot": "test", "signals": []})

    def test_build_signal_invalid_signal_name(self):
        with pytest.raises(ValidationError, match="Unknown signal"):
            BuildSignalArgs.model_validate(
                {"slot": "test", "signals": [{"name": "not_a_signal"}]}
            )

    def test_preview_signal_missing_slot(self):
        with pytest.raises(ValidationError):
            PreviewSignalArgs.model_validate({})

    def test_fetch_stock_data_missing_symbol(self):
        with pytest.raises(ValidationError):
            FetchStockDataArgs.model_validate({})

    def test_create_chart_missing_required(self):
        with pytest.raises(ValidationError):
            CreateChartArgs.model_validate({"chart_type": "line"})

    def test_preview_data_invalid_position(self):
        with pytest.raises(ValidationError):
            PreviewDataArgs.model_validate({"position": "middle"})

    def test_simulate_invalid_strategy(self):
        with pytest.raises(ValidationError, match="Unknown strategy"):
            SimulateArgs.model_validate({"strategy_name": "bogus"})

    def test_entry_signal_days_zero(self):
        with pytest.raises(ValidationError):
            RunStrategyArgs.model_validate(
                {"strategy_name": "long_calls", "entry_signal_days": 0}
            )

    def test_quantity_zero(self):
        with pytest.raises(ValidationError):
            SimulateArgs.model_validate({"strategy_name": "long_calls", "quantity": 0})

    def test_simulate_rejects_raw(self):
        with pytest.raises(ValidationError, match="does not support"):
            SimulateArgs.model_validate({"strategy_name": "long_calls", "raw": True})

    def test_invalid_entry_signal(self):
        with pytest.raises(ValidationError, match="Unknown signal"):
            RunStrategyArgs.model_validate(
                {"strategy_name": "long_calls", "entry_signal": "bogus_signal"}
            )

    def test_invalid_exit_signal(self):
        with pytest.raises(ValidationError, match="Unknown signal"):
            RunStrategyArgs.model_validate(
                {"strategy_name": "long_calls", "exit_signal": "bogus_signal"}
            )


# ---------------------------------------------------------------------------
# Type coercion
# ---------------------------------------------------------------------------


class TestTypeCoercion:
    def test_string_to_int_rows(self):
        """Pydantic should coerce '5' to 5 for integer fields."""
        m = PreviewDataArgs.model_validate({"rows": "5"})
        assert m.rows == 5
        assert isinstance(m.rows, int)

    def test_string_to_float_otm(self):
        m = RunStrategyArgs.model_validate(
            {"strategy_name": "long_calls", "max_otm_pct": "0.3"}
        )
        assert m.max_otm_pct == 0.3

    def test_int_to_float_capital(self):
        m = SimulateArgs.model_validate(
            {"strategy_name": "long_calls", "capital": 100000}
        )
        assert m.capital == 100000.0


# ---------------------------------------------------------------------------
# Schema generation
# ---------------------------------------------------------------------------


class TestSchemaGeneration:
    def test_all_tools_have_models(self):
        """Ensure TOOL_ARG_MODELS covers all expected tools."""
        expected = {
            "preview_data",
            "describe_data",
            "suggest_strategy_params",
            "run_strategy",
            "scan_strategies",
            "build_signal",
            "preview_signal",
            "list_signals",
            "list_results",
            "inspect_cache",
            "clear_cache",
            "fetch_stock_data",
            "create_chart",
            "simulate",
            "get_simulation_trades",
            "fetch_options_data",
        }
        assert set(TOOL_ARG_MODELS.keys()) == expected

    def test_pydantic_to_openai_params_basic(self):
        params = pydantic_to_openai_params(PreviewDataArgs)
        assert params["type"] == "object"
        assert "properties" in params
        assert "required" in params
        assert "dataset_name" in params["properties"]

    def test_pydantic_to_openai_params_required_fields(self):
        params = pydantic_to_openai_params(RunStrategyArgs)
        assert "strategy_name" in params["required"]

    def test_pydantic_to_openai_params_no_refs(self):
        """Schema should not contain $ref after resolution."""
        params = pydantic_to_openai_params(BuildSignalArgs)
        schema_str = str(params)
        assert "$ref" not in schema_str

    def test_pydantic_to_openai_params_no_titles(self):
        """Schema should not contain title keys."""
        params = pydantic_to_openai_params(CreateChartArgs)
        schema_str = str(params)
        assert "'title'" not in schema_str

    def test_pydantic_to_openai_params_enum_values(self):
        params = pydantic_to_openai_params(CreateChartArgs)
        chart_type_prop = params["properties"]["chart_type"]
        assert "enum" in chart_type_prop
        assert "line" in chart_type_prop["enum"]
        assert "candlestick" in chart_type_prop["enum"]

    def test_pydantic_to_openai_params_nested_model(self):
        """BuildSignalArgs has nested SignalSpec — ensure it resolves."""
        params = pydantic_to_openai_params(BuildSignalArgs)
        signals_prop = params["properties"]["signals"]
        assert signals_prop["type"] == "array"
        items = signals_prop["items"]
        assert "properties" in items
        assert "name" in items["properties"]

    def test_pydantic_to_openai_params_simulate(self):
        params = pydantic_to_openai_params(SimulateArgs)
        assert "strategy_name" in params["required"]
        props = params["properties"]
        # Should have strategy params (from mixin)
        assert "max_entry_dte" in props
        # Should have signal params (from mixin)
        assert "entry_signal" in props
        # Should have calendar params (from mixin)
        assert "front_dte_min" in props
        # Should have simulation-specific params
        assert "capital" in props
        assert "selector" in props


# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------


class TestOutputModels:
    def test_strategy_result_summary(self):
        s = StrategyResultSummary(
            strategy="long_calls",
            max_entry_dte=45,
            exit_dte=7,
            max_otm_pct=0.2,
            slippage="mid",
            dataset="SPY",
            count=100,
            mean_return=0.05,
            std=0.1,
            win_rate=0.6,
        )
        d = s.model_dump()
        assert d["strategy"] == "long_calls"
        assert d["count"] == 100
        assert d["win_rate"] == 0.6

    def test_strategy_result_summary_defaults(self):
        s = StrategyResultSummary(strategy="long_calls")
        assert s.max_entry_dte == 90
        assert s.exit_dte == 0
        assert s.slippage == "mid"
        assert s.count == 0

    def test_simulation_result_entry(self):
        e = SimulationResultEntry(
            strategy="short_puts",
            summary={"total_trades": 10, "win_rate": 0.7},
        )
        assert e.type == "simulation"
        assert e.strategy == "short_puts"


# ---------------------------------------------------------------------------
# exclude_none behavior
# ---------------------------------------------------------------------------


class TestExcludeNone:
    def test_model_dump_exclude_none(self):
        """Confirm that exclude_none=True drops unset optional fields."""
        m = RunStrategyArgs.model_validate(
            {"strategy_name": "long_calls", "max_entry_dte": 45}
        )
        d = m.model_dump(exclude_none=True)
        assert "strategy_name" in d
        assert "max_entry_dte" in d
        assert "exit_dte" not in d
        assert "entry_signal" not in d

    def test_model_dump_preserves_false(self):
        """Confirm that explicit False is not dropped by exclude_none."""
        m = RunStrategyArgs.model_validate(
            {"strategy_name": "long_calls", "raw": False}
        )
        d = m.model_dump(exclude_none=True)
        assert "raw" in d
        assert d["raw"] is False


# ---------------------------------------------------------------------------
# get_tool_schemas integration
# ---------------------------------------------------------------------------


class TestGetToolSchemas:
    def test_schemas_generated_from_models(self):
        from optopsy.ui.tools._schemas import get_tool_schemas

        schemas = get_tool_schemas()
        assert isinstance(schemas, list)
        assert len(schemas) > 0

        # Check that core tools are present
        names = {s["function"]["name"] for s in schemas}
        assert "run_strategy" in names
        assert "preview_data" in names
        assert "simulate" in names
        assert "create_chart" in names

    def test_schema_structure(self):
        from optopsy.ui.tools._schemas import get_tool_schemas

        schemas = get_tool_schemas()
        for schema in schemas:
            assert schema["type"] == "function"
            func = schema["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func
            params = func["parameters"]
            assert params["type"] == "object"
            assert "properties" in params
