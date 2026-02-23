import argparse
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("pyarrow", reason="UI extras not installed")


class TestCLIParsing:
    def test_default_launches_run(self):
        from optopsy.ui.cli import main

        with patch("optopsy.ui.cli._cmd_run") as mock_run:
            main([])
            mock_run.assert_called_once()

    def test_run_with_options(self):
        from optopsy.ui.cli import main

        with patch("optopsy.ui.cli._cmd_run") as mock_run:
            main(["run", "--port", "9000", "--headless"])
            args = mock_run.call_args[0][0]
            assert args.port == 9000
            assert args.headless is True

    def test_run_defaults(self):
        from optopsy.ui.cli import main

        with patch("optopsy.ui.cli._cmd_run") as mock_run:
            main(["run"])
            args = mock_run.call_args[0][0]
            assert args.host is None
            assert args.port is None
            assert args.headless is False
            assert args.debug is False
            assert args.watch is False

    def test_cache_size(self):
        from optopsy.ui.cli import main

        with patch("optopsy.ui.cli._cmd_cache_size") as mock_size:
            main(["cache", "size"])
            mock_size.assert_called_once()

    def test_cache_clear_all(self):
        from optopsy.ui.cli import main

        with patch("optopsy.ui.cli._cmd_cache_clear") as mock_clear:
            main(["cache", "clear"])
            args = mock_clear.call_args[0][0]
            assert args.symbol is None

    def test_cache_clear_symbol(self):
        from optopsy.ui.cli import main

        with patch("optopsy.ui.cli._cmd_cache_clear") as mock_clear:
            main(["cache", "clear", "SPY"])
            args = mock_clear.call_args[0][0]
            assert args.symbol == "SPY"


class TestFormatBytes:
    def test_bytes(self):
        from optopsy.ui.cli import _format_bytes

        assert _format_bytes(512) == "512.0 B"

    def test_kilobytes(self):
        from optopsy.ui.cli import _format_bytes

        assert _format_bytes(2048) == "2.0 KB"

    def test_megabytes(self):
        from optopsy.ui.cli import _format_bytes

        assert _format_bytes(1_500_000) == "1.4 MB"

    def test_gigabytes(self):
        from optopsy.ui.cli import _format_bytes

        assert _format_bytes(2_147_483_648) == "2.0 GB"

    def test_terabytes(self):
        from optopsy.ui.cli import _format_bytes

        assert _format_bytes(1_099_511_627_776) == "1.0 TB"

    def test_zero(self):
        from optopsy.ui.cli import _format_bytes

        assert _format_bytes(0) == "0.0 B"


# ---------------------------------------------------------------------------
# _cmd_run tests
# ---------------------------------------------------------------------------


class TestCmdRun:
    def _make_args(self, **overrides):
        defaults = {
            "host": None,
            "port": None,
            "headless": False,
            "debug": False,
            "watch": False,
        }
        defaults.update(overrides)
        return argparse.Namespace(**defaults)

    def _mock_chainlit_modules(self):
        """Set up mock chainlit modules in sys.modules for _cmd_run imports."""
        mock_config = MagicMock()
        mock_config.run = MagicMock()
        mock_config.ui = MagicMock()

        mock_config_module = MagicMock()
        mock_config_module.config = mock_config

        mock_cli_module = MagicMock()
        mock_cli_module.run_chainlit = MagicMock()

        mock_compat = MagicMock()
        mock_compat.import_optional_dependency = MagicMock()

        return mock_config, mock_config_module, mock_cli_module, mock_compat

    def test_host_port_env_vars(self, tmp_path):
        """--host and --port are set as env vars."""
        from optopsy.ui.cli import _cmd_run

        args = self._make_args(host="0.0.0.0", port=9000)
        mock_config, mock_config_mod, mock_cli_mod, mock_compat = (
            self._mock_chainlit_modules()
        )

        # Use a controlled env dict to prevent leaking into os.environ
        controlled_env = dict(os.environ)
        controlled_env["CHAINLIT_AUTH_SECRET"] = "test"
        # Remove any pre-existing values
        controlled_env.pop("CHAINLIT_HOST", None)
        controlled_env.pop("CHAINLIT_PORT", None)

        with (
            patch.dict(
                sys.modules,
                {
                    "chainlit.config": mock_config_mod,
                    "chainlit.cli": mock_cli_mod,
                },
            ),
            patch(
                "optopsy.ui._compat.import_optional_dependency",
                mock_compat.import_optional_dependency,
            ),
            patch.dict(os.environ, controlled_env, clear=True),
        ):
            _cmd_run(args)
            assert os.environ.get("CHAINLIT_HOST") == "0.0.0.0"
            assert os.environ.get("CHAINLIT_PORT") == "9000"

    def test_auth_secret_generation_writes_to_file(self):
        """Auth secret is generated and written to file when not present."""
        from optopsy.ui.cli import _cmd_run

        args = self._make_args()

        mock_config, mock_config_mod, mock_cli_mod, mock_compat = (
            self._mock_chainlit_modules()
        )

        # Remove CHAINLIT_AUTH_SECRET from env
        env_copy = {k: v for k, v in os.environ.items() if k != "CHAINLIT_AUTH_SECRET"}

        with (
            patch.dict(
                sys.modules,
                {
                    "chainlit.config": mock_config_mod,
                    "chainlit.cli": mock_cli_mod,
                },
            ),
            patch(
                "optopsy.ui._compat.import_optional_dependency",
                mock_compat.import_optional_dependency,
            ),
            patch.dict(os.environ, env_copy, clear=True),
        ):
            mock_path = MagicMock()
            mock_path.parent.mkdir = MagicMock()
            mock_path.exists.return_value = False
            mock_path.write_text = MagicMock()
            mock_path.read_text = MagicMock(return_value="generated")
            with patch("pathlib.Path.expanduser", return_value=mock_path):
                _cmd_run(args)
                assert "CHAINLIT_AUTH_SECRET" in os.environ
                # Verify the secret was actually written to file
                mock_path.write_text.assert_called_once()
                written = mock_path.write_text.call_args[0][0]
                assert len(written) == 64  # token_hex(32) produces 64 hex chars

    def test_auth_secret_read_from_file(self):
        """Existing auth secret file is read instead of generating new one."""
        from optopsy.ui.cli import _cmd_run

        args = self._make_args()
        mock_config, mock_config_mod, mock_cli_mod, mock_compat = (
            self._mock_chainlit_modules()
        )

        env_copy = {k: v for k, v in os.environ.items() if k != "CHAINLIT_AUTH_SECRET"}

        with (
            patch.dict(
                sys.modules,
                {
                    "chainlit.config": mock_config_mod,
                    "chainlit.cli": mock_cli_mod,
                },
            ),
            patch(
                "optopsy.ui._compat.import_optional_dependency",
                mock_compat.import_optional_dependency,
            ),
            patch.dict(os.environ, env_copy, clear=True),
        ):
            mock_path = MagicMock()
            mock_path.parent.mkdir = MagicMock()
            mock_path.exists.return_value = True
            mock_path.read_text.return_value = "existing_secret_value\n"
            with patch("pathlib.Path.expanduser", return_value=mock_path):
                _cmd_run(args)
                assert os.environ.get("CHAINLIT_AUTH_SECRET") == "existing_secret_value"
                # write_text should NOT have been called
                mock_path.write_text.assert_not_called()

    def test_chainlit_config_set(self):
        """Chainlit config values are set correctly."""
        from optopsy.ui.cli import _cmd_run

        args = self._make_args(headless=True, debug=True, watch=True)
        mock_config, mock_config_mod, mock_cli_mod, mock_compat = (
            self._mock_chainlit_modules()
        )

        with (
            patch.dict(
                sys.modules,
                {
                    "chainlit.config": mock_config_mod,
                    "chainlit.cli": mock_cli_mod,
                },
            ),
            patch(
                "optopsy.ui._compat.import_optional_dependency",
                mock_compat.import_optional_dependency,
            ),
            patch.dict(os.environ, {"CHAINLIT_AUTH_SECRET": "test"}, clear=False),
        ):
            _cmd_run(args)

        assert mock_config.run.headless is True
        assert mock_config.run.debug is True
        assert mock_config.run.watch is True
        assert mock_config.ui.language == "en-US"
        assert mock_config.ui.confirm_new_chat is False

    def test_run_chainlit_called_with_app_path(self):
        """run_chainlit is called with the absolute path to app.py."""
        from optopsy.ui.cli import _cmd_run

        args = self._make_args()
        mock_config, mock_config_mod, mock_cli_mod, mock_compat = (
            self._mock_chainlit_modules()
        )

        with (
            patch.dict(
                sys.modules,
                {
                    "chainlit.config": mock_config_mod,
                    "chainlit.cli": mock_cli_mod,
                },
            ),
            patch(
                "optopsy.ui._compat.import_optional_dependency",
                mock_compat.import_optional_dependency,
            ),
            patch.dict(os.environ, {"CHAINLIT_AUTH_SECRET": "test"}, clear=False),
        ):
            _cmd_run(args)

        mock_cli_mod.run_chainlit.assert_called_once()
        target_path = mock_cli_mod.run_chainlit.call_args[0][0]
        assert target_path.endswith("app.py")
        assert os.path.isabs(target_path)


# ---------------------------------------------------------------------------
# _cmd_cache_size / _cmd_cache_clear tests
# ---------------------------------------------------------------------------


class TestCmdCache:
    def test_cache_size_shows_entries(self, capsys):
        """_cmd_cache_size prints per-symbol sizes and total."""
        from optopsy.ui.cli import _cmd_cache_size

        mock_cache = MagicMock()
        mock_cache.size.return_value = {
            "options/SPY": 1024 * 1024,
            "options/AAPL": 2048,
        }
        mock_cache.total_size_bytes.return_value = 1024 * 1024 + 2048

        args = argparse.Namespace()

        with (
            patch(
                "optopsy.ui._compat.import_optional_dependency",
            ),
            patch(
                "optopsy.ui.providers.cache.ParquetCache",
                return_value=mock_cache,
            ),
        ):
            _cmd_cache_size(args)

        output = capsys.readouterr().out
        assert "options/SPY" in output
        assert "1.0 MB" in output
        assert "options/AAPL" in output
        assert "2.0 KB" in output
        assert "Total" in output

    def test_cache_size_empty(self, capsys):
        """_cmd_cache_size prints 'empty' when no cache entries."""
        from optopsy.ui.cli import _cmd_cache_size

        mock_cache = MagicMock()
        mock_cache.size.return_value = {}

        args = argparse.Namespace()

        with (
            patch(
                "optopsy.ui._compat.import_optional_dependency",
            ),
            patch(
                "optopsy.ui.providers.cache.ParquetCache",
                return_value=mock_cache,
            ),
        ):
            _cmd_cache_size(args)

        output = capsys.readouterr().out
        assert "empty" in output.lower()

    def test_cache_clear_all(self, capsys):
        """_cmd_cache_clear clears all entries."""
        from optopsy.ui.cli import _cmd_cache_clear

        mock_cache = MagicMock()
        mock_cache.clear.return_value = 5

        args = argparse.Namespace(symbol=None)

        with (
            patch(
                "optopsy.ui._compat.import_optional_dependency",
            ),
            patch(
                "optopsy.ui.providers.cache.ParquetCache",
                return_value=mock_cache,
            ),
        ):
            _cmd_cache_clear(args)

        output = capsys.readouterr().out
        assert "5" in output
        mock_cache.clear.assert_called_once_with(symbol=None)

    def test_cache_clear_symbol(self, capsys):
        """_cmd_cache_clear with symbol clears only that symbol."""
        from optopsy.ui.cli import _cmd_cache_clear

        mock_cache = MagicMock()
        mock_cache.clear.return_value = 2

        args = argparse.Namespace(symbol="SPY")

        with (
            patch(
                "optopsy.ui._compat.import_optional_dependency",
            ),
            patch(
                "optopsy.ui.providers.cache.ParquetCache",
                return_value=mock_cache,
            ),
        ):
            _cmd_cache_clear(args)

        output = capsys.readouterr().out
        assert "2" in output
        assert "SPY" in output
        mock_cache.clear.assert_called_once_with(symbol="SPY")


# ---------------------------------------------------------------------------
# _cmd_download tests
# ---------------------------------------------------------------------------


class TestCmdDownload:
    def test_no_provider_prints_error(self, capsys):
        """_cmd_download prints error when no provider is configured."""
        from optopsy.ui.cli import _cmd_download

        args = argparse.Namespace(symbols=["SPY"], verbose=False)

        with (
            patch(
                "optopsy.ui._compat.import_optional_dependency",
            ),
            patch("optopsy.ui.cli._load_env"),
            patch(
                "optopsy.ui.providers.get_provider_for_tool",
                return_value=None,
            ),
        ):
            _cmd_download(args)

        output = capsys.readouterr().out
        assert "No data provider" in output
        assert "EODHD_API_KEY" in output
