"""Tests for optopsy/data/cli.py — additional coverage for download and cache commands."""

import argparse

import pytest

pytest.importorskip("pyarrow", reason="UI extras not installed")

from unittest.mock import MagicMock, patch

from optopsy.data.cli import _cmd_cache_clear, _cmd_download, _format_bytes, _load_env

# ---------------------------------------------------------------------------
# _format_bytes edge cases
# ---------------------------------------------------------------------------


def test_format_bytes_tb():
    """Values >= 1 TB should format as TB."""
    result = _format_bytes(2 * 1024**4)
    assert "TB" in result
    assert "2.0" in result


def test_format_bytes_gb():
    result = _format_bytes(1.5 * 1024**3)
    assert "GB" in result


# ---------------------------------------------------------------------------
# _load_env fallback
# ---------------------------------------------------------------------------


@patch("dotenv.find_dotenv", return_value="")
@patch("dotenv.load_dotenv")
def test_load_env_fallback(mock_load, mock_find):
    """When find_dotenv returns empty string, should use fallback path."""
    _load_env()
    mock_load.assert_called_once()
    call_path = mock_load.call_args[0][0]
    assert call_path.endswith(".env")
    assert len(call_path) > 4


# ---------------------------------------------------------------------------
# _cmd_download
# ---------------------------------------------------------------------------


@patch("optopsy.data.cli._load_env")
@patch("optopsy.data.providers.get_provider_for_tool", return_value=None)
def test_cmd_download_no_provider(mock_get_provider, mock_env, capsys):
    """When no provider is configured, should print an error."""
    args = argparse.Namespace(symbols=["SPY"], verbose=False)
    _cmd_download(args)
    captured = capsys.readouterr()
    assert "No data provider" in captured.out


@patch("optopsy.data.cli._load_env")
@patch("optopsy.data.providers.get_provider_for_tool")
def test_cmd_download_generic_provider(mock_get_provider, mock_env, capsys):
    """Non-EODHD provider should use the generic download path."""
    mock_provider = MagicMock(
        spec=[]
    )  # empty spec so isinstance(EODHDProvider) is False
    mock_provider.execute = MagicMock(return_value=("Downloaded 100 rows", None))
    mock_get_provider.return_value = mock_provider

    args = argparse.Namespace(symbols=["SPY", "AAPL"], verbose=False)
    _cmd_download(args)

    assert mock_provider.execute.call_count == 2
    captured = capsys.readouterr()
    assert "Downloaded 100 rows" in captured.out


# ---------------------------------------------------------------------------
# _cmd_cache_clear with symbol filter
# ---------------------------------------------------------------------------


@patch("optopsy.data.providers.cache.ParquetCache")
def test_cmd_cache_clear_with_symbol(mock_cache_cls, capsys):
    """Clearing cache for a specific symbol should pass the symbol filter."""
    mock_cache = MagicMock()
    mock_cache.clear.return_value = 2
    mock_cache_cls.return_value = mock_cache

    args = argparse.Namespace(symbol="spy")
    _cmd_cache_clear(args)

    mock_cache.clear.assert_called_once_with(symbol="spy")
    captured = capsys.readouterr()
    assert "SPY" in captured.out
    assert "2" in captured.out


@patch("optopsy.data.providers.cache.ParquetCache")
def test_cmd_cache_clear_all(mock_cache_cls, capsys):
    """Clearing all cache should pass symbol=None."""
    mock_cache = MagicMock()
    mock_cache.clear.return_value = 5
    mock_cache_cls.return_value = mock_cache

    args = argparse.Namespace(symbol=None)
    _cmd_cache_clear(args)

    mock_cache.clear.assert_called_once_with(symbol=None)
    captured = capsys.readouterr()
    assert "5" in captured.out
    assert "SPY" not in captured.out
