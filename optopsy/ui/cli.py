"""CLI entry point for optopsy-chat.

Handles argument parsing, cache management commands, and Chainlit server launch.
"""

import argparse
import os


def _format_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _cmd_cache_size(args: argparse.Namespace) -> None:
    from optopsy.ui.providers.cache import ParquetCache

    cache = ParquetCache()
    entries = cache.size()
    if not entries:
        print("Cache is empty.")
        return
    for name, nbytes in entries.items():
        print(f"  {name:<30s} {_format_bytes(nbytes):>10s}")
    print(f"  {'Total':<30s} {_format_bytes(cache.total_size_bytes()):>10s}")


def _cmd_cache_clear(args: argparse.Namespace) -> None:
    from optopsy.ui.providers.cache import ParquetCache

    cache = ParquetCache()
    symbol = args.symbol
    count = cache.clear(symbol=symbol)
    if symbol:
        print(f"Cleared {count} cached file(s) for {symbol.upper()}.")
    else:
        print(f"Cleared {count} cached file(s).")


def _cmd_run(args: argparse.Namespace) -> None:
    if args.host:
        os.environ["CHAINLIT_HOST"] = args.host
    if args.port:
        os.environ["CHAINLIT_PORT"] = str(args.port)

    # Point Chainlit's app root at the ui/ package directory so that
    # our public/ assets (custom JS) are served regardless of cwd.
    ui_dir = os.path.dirname(os.path.abspath(__file__))
    os.environ.setdefault("CHAINLIT_APP_ROOT", ui_dir)

    # Chainlit requires a JWT secret when auth callbacks are registered.
    # Generate one on first run and persist it so sessions survive restarts.
    if not os.environ.get("CHAINLIT_AUTH_SECRET"):
        import secrets
        from pathlib import Path

        secret_file = Path("~/.optopsy/auth_secret").expanduser()
        secret_file.parent.mkdir(parents=True, exist_ok=True)
        if secret_file.exists():
            secret = secret_file.read_text().strip()
        else:
            secret = secrets.token_hex(32)
            secret_file.write_text(secret)
        os.environ["CHAINLIT_AUTH_SECRET"] = secret

    from chainlit.config import config

    config.run.headless = args.headless
    config.run.debug = args.debug
    config.run.watch = args.watch
    config.ui.language = "en-US"
    config.ui.confirm_new_chat = False
    config.ui.custom_js = "/public/redirect_after_delete.js"
    config.ui.custom_css = "/public/hide_avatar.css"

    from chainlit.cli import run_chainlit

    target = os.path.join(os.path.dirname(__file__), "app.py")
    run_chainlit(os.path.abspath(target))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="optopsy-chat",
        description="Optopsy Chat — options strategy backtesting assistant",
    )
    subparsers = parser.add_subparsers(dest="command")

    # --- run ---
    run_parser = subparsers.add_parser("run", help="Launch the chat UI (default)")
    run_parser.add_argument(
        "--host", default=None, help="Host to bind (default: 127.0.0.1)"
    )
    run_parser.add_argument(
        "--port", type=int, default=None, help="Port to bind (default: 8000)"
    )
    run_parser.add_argument(
        "--headless", action="store_true", help="Don't open browser on start"
    )
    run_parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    run_parser.add_argument(
        "-w", "--watch", action="store_true", help="Reload on file changes"
    )
    run_parser.set_defaults(func=_cmd_run)

    # --- cache ---
    cache_parser = subparsers.add_parser("cache", help="Manage the data cache")
    cache_sub = cache_parser.add_subparsers(dest="cache_command")

    size_parser = cache_sub.add_parser("size", help="Show cache size on disk")
    size_parser.set_defaults(func=_cmd_cache_size)

    clear_parser = cache_sub.add_parser("clear", help="Clear cached data")
    clear_parser.add_argument(
        "symbol",
        nargs="?",
        default=None,
        help="Symbol to clear (e.g. SPY). Omit to clear all.",
    )
    clear_parser.set_defaults(func=_cmd_cache_clear)

    args = parser.parse_args(argv)

    if args.command is None:
        # Default: no subcommand means launch Chainlit
        args.host = None
        args.port = None
        args.headless = False
        args.debug = False
        args.watch = False
        _cmd_run(args)
    elif not hasattr(args, "func"):
        # e.g. "optopsy-chat cache" with no sub-subcommand
        if args.command == "cache":
            cache_parser.print_help()
        else:
            parser.print_help()
    else:
        args.func(args)
