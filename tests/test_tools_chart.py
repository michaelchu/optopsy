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
        assert "unknown" in result.llm_summary.lower()

    def test_unknown_data_source(self, option_data):
        result = execute_tool(
            "create_chart",
            {"chart_type": "line", "data_source": "magic"},
            option_data,
        )
        assert result.chart_figure is None
        assert "unknown" in result.llm_summary.lower()

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
    def test_custom_title(self, option_data):
        result = execute_tool(
            "create_chart",
            {
                "chart_type": "line",
                "data_source": "dataset",
                "x": "strike",
                "y": "bid",
                "title": "My Custom Title",
            },
            option_data,
        )
        assert result.chart_figure is not None
        assert result.chart_figure.layout.title.text == "My Custom Title"
        assert "My Custom Title" in result.user_display

    def test_auto_generated_title(self, option_data):
        result = execute_tool(
            "create_chart",
            {"chart_type": "bar", "data_source": "dataset", "x": "strike", "y": "bid"},
            option_data,
        )
        assert result.chart_figure is not None
        assert "Bar" in result.chart_figure.layout.title.text

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
