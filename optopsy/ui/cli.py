"""CLI entry point for optopsy-chat.

Handles argument parsing, cache management commands, and Chainlit server launch.
All non-UI commands are delegated to ``optopsy.data.cli``.
"""

import argparse
import os

from optopsy.data.cli import (
    _build_data_subparsers,
    _load_env,
)


def _cmd_run(args: argparse.Namespace) -> None:
    """Configure environment and launch the Chainlit server."""
    if args.host:
        os.environ["CHAINLIT_HOST"] = args.host
    if args.port:
        os.environ["CHAINLIT_PORT"] = str(args.port)

    # Point Chainlit's app root at the ui/ package directory so that
    # our public/ assets (custom JS) are served regardless of cwd.
    ui_dir = os.path.dirname(os.path.abspath(__file__))
    os.environ.setdefault("CHAINLIT_APP_ROOT", ui_dir)

    # Load .env before resolving paths so OPTOPSY_DATA_DIR is available.
    _load_env()

    # Chainlit requires a JWT secret when auth callbacks are registered.
    # Generate one on first run and persist it so sessions survive restarts.
    if not os.environ.get("CHAINLIT_AUTH_SECRET"):
        import secrets

        from optopsy.ui.paths import AUTH_SECRET_PATH

        secret_file = AUTH_SECRET_PATH
        secret_file.parent.mkdir(parents=True, exist_ok=True)
        if secret_file.exists():
            secret = secret_file.read_text().strip()
        else:
            secret = secrets.token_hex(32)
            secret_file.write_text(secret)
        os.environ["CHAINLIT_AUTH_SECRET"] = secret

    from optopsy.ui._compat import import_optional_dependency

    import_optional_dependency("chainlit")
    import_optional_dependency("litellm")

    from chainlit.config import config

    config.run.headless = args.headless
    config.run.debug = args.debug
    config.run.watch = args.watch
    config.ui.language = "en-US"
    config.ui.confirm_new_chat = False
    config.ui.custom_js = "/public/redirect_after_delete.js"
    config.ui.custom_css = "/public/hide_avatar.css"
    config.ui.default_avatar_file_url = "/public/logo-small.png"
    config.ui.name = "Optopsy AI"

    from chainlit.cli import run_chainlit

    target = os.path.join(os.path.dirname(__file__), "app.py")
    run_chainlit(os.path.abspath(target))


def main(argv: list[str] | None = None) -> None:
    """Parse CLI arguments and dispatch to the appropriate subcommand."""
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

    # --- data subcommands (download, symbols, cache) ---
    named = _build_data_subparsers(subparsers)

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
            named["cache"].print_help()
        else:
            parser.print_help()
    else:
        args.func(args)
