from unittest.mock import patch

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

    def test_zero(self):
        from optopsy.ui.cli import _format_bytes

        assert _format_bytes(0) == "0.0 B"
