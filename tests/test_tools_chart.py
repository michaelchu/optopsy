"""Tests for the create_chart tool."""

import datetime

import pandas as pd
import pytest

pytest.importorskip("pyarrow", reason="UI extras not installed")
pytest.importorskip("plotly", reason="plotly not installed")

from optopsy.ui.tools import execute_tool

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def option_data():
    """Small option dataset for charting tests."""
    exp_date = datetime.datetime(2018, 1, 31)
    quote_dates = [datetime.datetime(2018, 1, 1), datetime.datetime(2018, 1, 31)]
    cols = [
        "underlying_symbol",
        "underlying_price",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
    ]
    d = [
        ["SPX", 213.93, "call", exp_date, quote_dates[0], 212.5, 7.35, 7.45],
        ["SPX", 213.93, "call", exp_date, quote_dates[0], 215.0, 6.00, 6.05],
        ["SPX", 213.93, "put", exp_date, quote_dates[0], 212.5, 5.70, 5.80],
        ["SPX", 220.0, "call", exp_date, quote_dates[1], 212.5, 7.45, 7.55],
        ["SPX", 220.0, "call", exp_date, quote_dates[1], 215.0, 4.96, 5.05],
        ["SPX", 220.0, "put", exp_date, quote_dates[1], 212.5, 0.10, 0.20],
    ]
    return pd.DataFrame(data=d, columns=cols)


@pytest.fixture
def ohlcv_data():
    """Small OHLCV DataFrame for candlestick tests."""
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
            "open": [100.0, 102.0, 101.0],
            "high": [103.0, 104.0, 105.0],
            "low": [99.0, 101.0, 100.0],
            "close": [102.0, 103.0, 104.0],
            "volume": [1000, 1100, 1200],
            "underlying_symbol": ["SPY", "SPY", "SPY"],
        }
    )


# ---------------------------------------------------------------------------
# Chart type tests
# ---------------------------------------------------------------------------


class TestLineChart:
    def test_line_chart(self, option_data):
        result = execute_tool(
            "create_chart",
            {"chart_type": "line", "data_source": "dataset", "x": "strike", "y": "bid"},
            option_data,
        )
        assert result.chart_figure is not None
        assert "line" in result.llm_summary.lower()
        assert len(result.chart_figure.data) == 1
        assert result.chart_figure.data[0].mode == "lines"

    def test_line_chart_missing_columns(self, option_data):
        result = execute_tool(
            "create_chart",
            {"chart_type": "line", "data_source": "dataset", "x": "strike"},
            option_data,
        )
        assert result.chart_figure is None
        assert "requires" in result.llm_summary.lower()

    def test_line_chart_nonexistent_column(self, option_data):
        result = execute_tool(
            "create_chart",
            {
                "chart_type": "line",
                "data_source": "dataset",
                "x": "strike",
                "y": "nonexistent",
            },
            option_data,
        )
        assert result.chart_figure is None
        assert "not found" in result.llm_summary.lower()


class TestBarChart:
    def test_bar_chart(self, option_data):
        result = execute_tool(
            "create_chart",
            {"chart_type": "bar", "data_source": "dataset", "x": "strike", "y": "bid"},
            option_data,
        )
        assert result.chart_figure is not None
        assert len(result.chart_figure.data) == 1
        assert result.chart_figure.data[0].type == "bar"


class TestScatterChart:
    def test_scatter_chart(self, option_data):
        result = execute_tool(
            "create_chart",
            {
                "chart_type": "scatter",
                "data_source": "dataset",
                "x": "strike",
                "y": "bid",
            },
            option_data,
        )
        assert result.chart_figure is not None
        assert result.chart_figure.data[0].mode == "markers"


class TestHistogramChart:
    def test_histogram(self, option_data):
        result = execute_tool(
            "create_chart",
            {"chart_type": "histogram", "data_source": "dataset", "x": "bid"},
            option_data,
        )
        assert result.chart_figure is not None
        assert result.chart_figure.data[0].type == "histogram"

    def test_histogram_with_bins(self, option_data):
        result = execute_tool(
            "create_chart",
            {
                "chart_type": "histogram",
                "data_source": "dataset",
                "x": "bid",
                "bins": 5,
            },
            option_data,
        )
        assert result.chart_figure is not None
        assert result.chart_figure.data[0].nbinsx == 5

    def test_histogram_missing_column(self, option_data):
        result = execute_tool(
            "create_chart",
            {"chart_type": "histogram", "data_source": "dataset"},
            option_data,
        )
        assert result.chart_figure is None
        assert "requires" in result.llm_summary.lower()


class TestHeatmapChart:
    def test_heatmap(self, option_data):
        result = execute_tool(
            "create_chart",
            {
                "chart_type": "heatmap",
                "data_source": "dataset",
                "x": "option_type",
                "y": "strike",
                "heatmap_col": "bid",
            },
            option_data,
        )
        assert result.chart_figure is not None
        assert result.chart_figure.data[0].type == "heatmap"

    def test_heatmap_missing_heatmap_col(self, option_data):
        result = execute_tool(
            "create_chart",
            {
                "chart_type": "heatmap",
                "data_source": "dataset",
                "x": "option_type",
                "y": "strike",
            },
            option_data,
        )
        assert result.chart_figure is None
        assert "heatmap_col" in result.llm_summary.lower()


class TestCandlestickChart:
    def test_candlestick(self, ohlcv_data):
        result = execute_tool(
            "create_chart",
            {"chart_type": "candlestick", "data_source": "dataset"},
            ohlcv_data,
        )
        assert result.chart_figure is not None
        assert result.chart_figure.data[0].type == "candlestick"

    def test_candlestick_auto_detects_date(self, ohlcv_data):
        """Auto-detects 'date' column without explicit x parameter."""
        result = execute_tool(
            "create_chart",
            {"chart_type": "candlestick", "data_source": "dataset"},
            ohlcv_data,
        )
        assert result.chart_figure is not None

    def test_candlestick_explicit_x(self, ohlcv_data):
        """Accepts explicit x parameter for date column."""
        result = execute_tool(
            "create_chart",
            {"chart_type": "candlestick", "data_source": "dataset", "x": "date"},
            ohlcv_data,
        )
        assert result.chart_figure is not None

    def test_candlestick_missing_ohlc(self):
        """Fails gracefully when OHLC columns are missing."""
        df = pd.DataFrame({"date": pd.to_datetime(["2024-01-02"]), "close": [100.0]})
        result = execute_tool(
            "create_chart",
            {"chart_type": "candlestick", "data_source": "dataset"},
            df,
        )
        assert result.chart_figure is None
        assert "missing" in result.llm_summary.lower()

    def test_candlestick_no_date_col(self):
        """Fails gracefully when no date column exists."""
        df = pd.DataFrame(
            {
                "open": [100.0],
                "high": [103.0],
                "low": [99.0],
                "close": [102.0],
            }
        )
        result = execute_tool(
            "create_chart",
            {"chart_type": "candlestick", "data_source": "dataset"},
            df,
        )
        assert result.chart_figure is None
        assert "date column" in result.llm_summary.lower()

    def test_candlestick_quote_date(self):
        """Auto-detects 'quote_date' as fallback date column."""
        df = pd.DataFrame(
            {
                "quote_date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
                "open": [100.0, 101.0],
                "high": [103.0, 104.0],
                "low": [99.0, 100.0],
                "close": [102.0, 103.0],
            }
        )
        result = execute_tool(
            "create_chart",
            {"chart_type": "candlestick", "data_source": "dataset"},
            df,
        )
        assert result.chart_figure is not None


# ---------------------------------------------------------------------------
# Data source tests
# ---------------------------------------------------------------------------


class TestDataSources:
    def test_no_dataset_loaded(self):
        result = execute_tool(
            "create_chart",
            {"chart_type": "line", "data_source": "dataset", "x": "a", "y": "b"},
            None,
        )
        assert result.chart_figure is None
        assert "no dataset" in result.llm_summary.lower()

    def test_named_dataset(self, option_data):
        """data_source='dataset' with dataset_name resolves named datasets."""
        datasets = {"SPX": option_data}
        result = execute_tool(
            "create_chart",
            {
                "chart_type": "line",
                "data_source": "dataset",
                "dataset_name": "SPX",
                "x": "strike",
                "y": "bid",
            },
            None,
            datasets=datasets,
        )
        assert result.chart_figure is not None

    def test_named_dataset_not_found(self, option_data):
        datasets = {"SPX": option_data}
        result = execute_tool(
            "create_chart",
            {
                "chart_type": "line",
                "data_source": "dataset",
                "dataset_name": "QQQ",
                "x": "a",
                "y": "b",
            },
            None,
            datasets=datasets,
        )
        assert result.chart_figure is None
        assert "not found" in result.llm_summary.lower()
        assert "SPX" in result.llm_summary  # shows available

    def test_result_data_source(self, option_data):
        results = {
            "long_calls:dte=90": {
                "strategy": "long_calls",
                "count": 10,
                "mean_return": 0.05,
            }
        }
        result = execute_tool(
            "create_chart",
            {
                "chart_type": "bar",
                "data_source": "result",
                "result_key": "long_calls:dte=90",
                "x": "strategy",
                "y": "mean_return",
            },
            option_data,
            results=results,
        )
        assert result.chart_figure is not None

    def test_result_not_found(self, option_data):
        result = execute_tool(
            "create_chart",
            {
                "chart_type": "bar",
                "data_source": "result",
                "result_key": "nonexistent",
                "x": "a",
                "y": "b",
            },
            option_data,
            results={},
        )
        assert result.chart_figure is None
        assert "not found" in result.llm_summary.lower()

    def test_result_no_runs(self, option_data):
        """No result_key and empty results registry."""
        result = execute_tool(
            "create_chart",
            {"chart_type": "bar", "data_source": "result", "x": "a", "y": "b"},
            option_data,
            results={},
        )
        assert result.chart_figure is None
        assert "no strategy results" in result.llm_summary.lower()

    def test_signal_data_source(self, option_data):
        valid_dates = pd.DataFrame(
            {
                "underlying_symbol": ["SPX", "SPX"],
                "quote_date": pd.to_datetime(["2018-01-03", "2018-01-04"]),
            }
        )
        signals = {"entry": valid_dates}
        result = execute_tool(
            "create_chart",
            {
                "chart_type": "scatter",
                "data_source": "signal",
                "signal_slot": "entry",
                "x": "quote_date",
                "y": "underlying_symbol",
            },
            option_data,
            signals=signals,
        )
        assert result.chart_figure is not None

    def test_signal_not_found(self, option_data):
        result = execute_tool(
            "create_chart",
            {
                "chart_type": "scatter",
                "data_source": "signal",
                "signal_slot": "nonexistent",
            },
            option_data,
        )
        assert result.chart_figure is None
        assert "not found" in result.llm_summary.lower()

    def test_stock_no_symbol(self, option_data):
        result = execute_tool(
            "create_chart",
            {"chart_type": "candlestick", "data_source": "stock"},
            option_data,
        )
        assert result.chart_figure is None
        assert "symbol" in result.llm_summary.lower()


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


class TestChartErrors:
    def test_missing_chart_type(self, option_data):
        result = execute_tool(
            "create_chart",
            {"data_source": "dataset"},
            option_data,
        )
        assert result.chart_figure is None
        assert "chart_type" in result.llm_summary.lower()

    def test_missing_data_source(self, option_data):
        result = execute_tool(
            "create_chart",
            {"chart_type": "line"},
            option_data,
        )
        assert result.chart_figure is None
        assert "data_source" in result.llm_summary.lower()

    def test_unknown_chart_type(self, option_data):
        result = execute_tool(
            "create_chart",
            {"chart_type": "pie", "data_source": "dataset"},
            option_data,
        )
        assert result.chart_figure is None
        summary = result.llm_summary.lower()
        assert "invalid arguments for create_chart" in summary

    def test_unknown_data_source(self, option_data):
        result = execute_tool(
            "create_chart",
            {"chart_type": "line", "data_source": "magic"},
            option_data,
        )
        assert result.chart_figure is None
        summary = result.llm_summary.lower()
        assert "invalid arguments for create_chart" in summary

    def test_empty_dataframe(self):
        empty = pd.DataFrame(columns=["a", "b"])
        result = execute_tool(
            "create_chart",
            {"chart_type": "line", "data_source": "dataset", "x": "a", "y": "b"},
            empty,
        )
        assert result.chart_figure is None
        assert "empty" in result.llm_summary.lower()


# ---------------------------------------------------------------------------
# Styling / layout tests
# ---------------------------------------------------------------------------


class TestChartStyling:
    def test_no_title_or_legend(self, option_data):
        result = execute_tool(
            "create_chart",
            {"chart_type": "bar", "data_source": "dataset", "x": "strike", "y": "bid"},
            option_data,
        )
        assert result.chart_figure is not None
        assert result.chart_figure.layout.title.text is None
        assert result.chart_figure.layout.showlegend is False

    def test_custom_dimensions(self, option_data):
        result = execute_tool(
            "create_chart",
            {
                "chart_type": "line",
                "data_source": "dataset",
                "x": "strike",
                "y": "bid",
                "figsize_width": 1200,
                "figsize_height": 800,
            },
            option_data,
        )
        assert result.chart_figure is not None
        assert result.chart_figure.layout.width == 1200
        assert result.chart_figure.layout.height == 800

    def test_color_parameter(self, option_data):
        result = execute_tool(
            "create_chart",
            {
                "chart_type": "line",
                "data_source": "dataset",
                "x": "strike",
                "y": "bid",
                "color": "red",
            },
            option_data,
        )
        assert result.chart_figure is not None
        assert result.chart_figure.data[0].line.color == "red"


# ---------------------------------------------------------------------------
# Indicator chart tests
# ---------------------------------------------------------------------------


@pytest.fixture
def ohlcv_long():
    """Longer OHLCV dataset (30 rows) for indicator computation."""
    import numpy as np

    np.random.seed(42)
    n = 60
    dates = pd.bdate_range("2024-01-02", periods=n)
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    return pd.DataFrame(
        {
            "date": dates,
            "open": close - np.random.rand(n) * 0.5,
            "high": close + np.random.rand(n) * 1.0,
            "low": close - np.random.rand(n) * 1.0,
            "close": close,
            "volume": np.random.randint(1000, 5000, n),
        }
    )


class TestIndicatorCharts:
    def test_candlestick_with_rsi(self, ohlcv_long):
        result = execute_tool(
            "create_chart",
            {
                "chart_type": "candlestick",
                "data_source": "dataset",
                "indicators": [{"type": "rsi", "period": 14}],
            },
            ohlcv_long,
        )
        assert result.chart_figure is not None
        # Should have candlestick + RSI trace = 2 traces minimum
        assert len(result.chart_figure.data) >= 2
        # First trace is candlestick
        assert result.chart_figure.data[0].type == "candlestick"

    def test_candlestick_with_sma_overlay(self, ohlcv_long):
        result = execute_tool(
            "create_chart",
            {
                "chart_type": "candlestick",
                "data_source": "dataset",
                "indicators": [{"type": "sma", "period": 10}],
            },
            ohlcv_long,
        )
        assert result.chart_figure is not None
        # Candlestick + SMA trace
        assert len(result.chart_figure.data) == 2
        assert result.chart_figure.data[1].name == "SMA(10)"

    def test_candlestick_with_ema_overlay(self, ohlcv_long):
        result = execute_tool(
            "create_chart",
            {
                "chart_type": "candlestick",
                "data_source": "dataset",
                "indicators": [{"type": "ema", "period": 10}],
            },
            ohlcv_long,
        )
        assert result.chart_figure is not None
        assert result.chart_figure.data[1].name == "EMA(10)"

    def test_candlestick_with_multiple_indicators(self, ohlcv_long):
        result = execute_tool(
            "create_chart",
            {
                "chart_type": "candlestick",
                "data_source": "dataset",
                "indicators": [
                    {"type": "sma", "period": 10},
                    {"type": "rsi", "period": 14},
                    {"type": "volume"},
                ],
            },
            ohlcv_long,
        )
        assert result.chart_figure is not None
        # Candlestick + SMA + RSI + Volume = at least 4 traces
        assert len(result.chart_figure.data) >= 4

    def test_macd_subplot(self, ohlcv_long):
        result = execute_tool(
            "create_chart",
            {
                "chart_type": "candlestick",
                "data_source": "dataset",
                "indicators": [{"type": "macd", "fast": 12, "slow": 26, "signal": 9}],
            },
            ohlcv_long,
        )
        assert result.chart_figure is not None
        # Candlestick + MACD line + Signal line + Histogram = 4 traces
        assert len(result.chart_figure.data) >= 4
        trace_names = [t.name for t in result.chart_figure.data]
        assert "MACD" in trace_names
        assert "Signal" in trace_names
        assert "Histogram" in trace_names

    def test_bbands_overlay(self, ohlcv_long):
        result = execute_tool(
            "create_chart",
            {
                "chart_type": "candlestick",
                "data_source": "dataset",
                "indicators": [{"type": "bbands", "period": 20, "std": 2.0}],
            },
            ohlcv_long,
        )
        assert result.chart_figure is not None
        # Candlestick + upper + lower + mid = 4 traces
        assert len(result.chart_figure.data) == 4
        trace_names = [t.name for t in result.chart_figure.data]
        assert any("BB Upper" in n for n in trace_names)
        assert any("BB Lower" in n for n in trace_names)
        assert any("BB Mid" in n for n in trace_names)

    def test_volume_subplot(self, ohlcv_long):
        result = execute_tool(
            "create_chart",
            {
                "chart_type": "candlestick",
                "data_source": "dataset",
                "indicators": [{"type": "volume"}],
            },
            ohlcv_long,
        )
        assert result.chart_figure is not None
        assert len(result.chart_figure.data) == 2
        assert result.chart_figure.data[1].name == "Volume"
        assert result.chart_figure.data[1].type == "bar"

    def test_invalid_indicator_type(self, ohlcv_long):
        result = execute_tool(
            "create_chart",
            {
                "chart_type": "candlestick",
                "data_source": "dataset",
                "indicators": [{"type": "stochastic"}],
            },
            ohlcv_long,
        )
        assert result.chart_figure is None
        summary = result.llm_summary.lower()
        assert "invalid arguments for create_chart" in summary

    def test_indicators_require_close_column(self):
        """Indicators on data without a close column should error."""
        df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
                "open": [100.0, 101.0],
                "high": [103.0, 104.0],
                "low": [99.0, 100.0],
                "value": [102.0, 103.0],
            }
        )
        result = execute_tool(
            "create_chart",
            {
                "chart_type": "candlestick",
                "data_source": "dataset",
                "indicators": [{"type": "rsi"}],
            },
            df,
        )
        assert result.chart_figure is None
        assert "close" in result.llm_summary.lower()

    def test_volume_requires_volume_column(self, ohlcv_data):
        """Volume indicator on data without volume column should error."""
        df = ohlcv_data.drop(columns=["volume"])
        result = execute_tool(
            "create_chart",
            {
                "chart_type": "candlestick",
                "data_source": "dataset",
                "indicators": [{"type": "volume"}],
            },
            df,
        )
        assert result.chart_figure is None
        assert "volume" in result.llm_summary.lower()

    def test_auto_height_scaling(self, ohlcv_long):
        """Height auto-scales based on number of subplot panels."""
        result = execute_tool(
            "create_chart",
            {
                "chart_type": "candlestick",
                "data_source": "dataset",
                "indicators": [
                    {"type": "rsi"},
                    {"type": "macd"},
                ],
            },
            ohlcv_long,
        )
        assert result.chart_figure is not None
        # 500 base + 200*2 subplots = 900
        assert result.chart_figure.layout.height == 900

    def test_candlestick_without_indicators_unchanged(self, ohlcv_data):
        """Candlestick without indicators still works as before."""
        result = execute_tool(
            "create_chart",
            {"chart_type": "candlestick", "data_source": "dataset"},
            ohlcv_data,
        )
        assert result.chart_figure is not None
        assert len(result.chart_figure.data) == 1
        assert result.chart_figure.data[0].type == "candlestick"
