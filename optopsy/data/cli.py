"""CLI entry point for optopsy-data.

Handles argument parsing for data management commands: download, symbols,
and cache management. Does not require Chainlit/LiteLLM.
"""

import argparse


def _format_bytes(n: int | float) -> str:
    """Format a byte count as a human-readable string (e.g. ``"1.2 MB"``)."""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n = n / 1024
    return f"{n:.1f} TB"


def _cmd_cache_size(args: argparse.Namespace) -> None:
    """Print per-symbol cache sizes and a total to stdout."""
    from optopsy.data._compat import import_optional_dependency

    import_optional_dependency("pyarrow")

    from optopsy.data.providers.cache import get_store

    store = get_store()
    entries = store.size()
    if not entries:
        print("Cache is empty.")
        return
    for name, nbytes in entries.items():
        print(f"  {name:<30s} {_format_bytes(nbytes):>10s}")
    print(f"  {'Total':<30s} {_format_bytes(store.total_size_bytes()):>10s}")


def _cmd_cache_clear(args: argparse.Namespace) -> None:
    """Delete cached parquet files, optionally filtered by symbol or category."""
    from rich.console import Console
    from rich.prompt import Confirm

    from optopsy.data._compat import import_optional_dependency

    import_optional_dependency("pyarrow")

    from optopsy.data.providers.cache import get_store

    console = Console()
    store = get_store()
    symbol = args.symbol
    category = None
    if getattr(args, "stocks", False):
        category = "yf_stocks"
    elif getattr(args, "options", False):
        category = "options"

    # Build a human-readable description of what will be deleted
    parts = []
    if category:
        label = "stock" if category == "yf_stocks" else "options"
        parts.append(f"{label} data")
    else:
        parts.append("all cached data")
    if symbol:
        parts.append(f"for {symbol.upper()}")
    description = " ".join(parts)

    if not getattr(args, "yes", False):
        if not Confirm.ask(f"Clear {description}?", console=console, default=False):
            console.print("[dim]Aborted.[/dim]")
            return

    count = store.clear(symbol=symbol, category=category)
    console.print(f"Cleared {count} cached file(s) ({description}).")


def _load_env() -> None:
    """Load .env file from the project root."""
    from pathlib import Path

    from optopsy.data._compat import import_optional_dependency

    dotenv = import_optional_dependency("dotenv")

    env_path = dotenv.find_dotenv() or str(
        Path(__file__).resolve().parent.parent.parent / ".env"
    )
    dotenv.load_dotenv(env_path, override=True)


def _cmd_download(args: argparse.Namespace) -> None:
    import logging

    from optopsy.data._compat import import_optional_dependency

    import_optional_dependency("pyarrow")
    _load_env()

    if args.verbose:
        level = logging.DEBUG
    else:
        level = logging.ERROR  # suppress all logs in normal mode; status via Rich

    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
        level=level,
    )

    if getattr(args, "stocks", False):
        for symbol in args.symbols:
            _download_stocks_with_rich(symbol.upper())
        return

    import_optional_dependency("requests")

    from optopsy.data.providers import get_provider_for_tool
    from optopsy.data.providers.eodhd import EODHDProvider

    provider = get_provider_for_tool("download_options_data")
    if provider is None:
        print(
            "No data provider is configured for downloading options data.\n"
            "Set EODHD_API_KEY in your environment or .env file."
        )
        return

    for symbol in args.symbols:
        if isinstance(provider, EODHDProvider):
            _download_with_rich(provider, symbol.upper())
        else:
            print(f"\n{'=' * 60}")
            print(f"Downloading options data for {symbol.upper()}…")
            print(f"{'=' * 60}")
            summary, _ = provider.execute("download_options_data", {"symbol": symbol})
            print(f"\n{summary}")


def _download_with_rich(provider: object, symbol: str) -> None:
    """Run download with Rich live progress display."""
    from rich.console import Console
    from rich.live import Live
    from rich.table import Table

    console = Console()
    console.rule(f"Downloading options data for {symbol}")

    # State shared with callbacks
    state: dict[str, object] = {
        "option_type": "",
        "rows": 0,
        "pct": 0.0,
        "status": "",
    }
    live_ctx: list[Live] = []  # mutable container for closure access

    def _make_display() -> Table:
        table = Table.grid(padding=(0, 1))
        otype = str(state["option_type"])
        rows = int(state.get("rows", 0))  # type: ignore[arg-type]
        pct = float(state.get("pct", 0))  # type: ignore[arg-type]
        status = str(state.get("status", ""))

        # Progress bar
        bar_width = 30
        filled = int(bar_width * pct / 100)
        bar = "━" * filled + "╺" + "─" * (bar_width - filled - 1)

        if otype:
            table.add_row(
                f"  [bold]{symbol}[/bold] {otype}",
                f"[green]{bar}[/green]",
                f"[cyan]{pct:5.1f}%[/cyan]",
                f"[yellow]{rows:,} rows[/yellow]",
            )
        if status:
            table.add_row(f"  [dim]{status}[/dim]")
        return table

    def _on_progress(sym: str, option_type: str, rows: int, pct: float) -> None:
        state["option_type"] = option_type
        state["rows"] = rows
        state["pct"] = pct
        if live_ctx:
            live_ctx[0].update(_make_display())

    def _on_status(msg: str) -> None:
        state["status"] = msg
        if live_ctx:
            live_ctx[0].update(_make_display())

    with Live(_make_display(), console=console, refresh_per_second=10) as live:
        live_ctx.append(live)
        summary, _ = provider.download_with_progress(  # type: ignore[attr-defined]
            symbol,
            on_progress=_on_progress,
            on_status=_on_status,
        )

    console.print(f"\n{summary}")


def _download_stocks_with_rich(symbol: str) -> None:
    """Download stock/index OHLCV data via yfinance with Rich progress display."""
    from datetime import date

    import pandas as pd
    from rich.console import Console

    from optopsy.data._compat import import_optional_dependency

    console = Console()
    console.rule(f"Downloading stock data for {symbol}")

    try:
        import_optional_dependency("yfinance")
    except ImportError:
        console.print(
            "  [red]The 'yfinance' package is required to download stock data. "
            "Install it with: pip install optopsy[data][/red]"
        )
        return

    from optopsy.data._yf_helpers import _YF_CACHE_CATEGORY, _yf_fetch_and_cache
    from optopsy.data.providers.cache import get_store

    store = get_store()
    cached = store.read(_YF_CACHE_CATEGORY, symbol)

    with console.status(f"[bold green]Fetching {symbol} from yfinance…"):
        try:
            result = _yf_fetch_and_cache(symbol, cached, date.today())
        except (OSError, ValueError) as exc:
            console.print(f"  [red]Error fetching {symbol}: {exc}[/red]")
            return

    if result is None or result.empty:
        console.print(f"  [yellow]No data returned for {symbol}.[/yellow]")
        return

    date_min = pd.to_datetime(result["date"]).dt.date.min()
    date_max = pd.to_datetime(result["date"]).dt.date.max()
    row_count = len(result)

    size_bytes = store.size().get(f"{_YF_CACHE_CATEGORY}/{symbol}", 0)
    size_str = _format_bytes(size_bytes)

    console.print(f"  [bold]{symbol}[/bold]  {date_min} → {date_max}")
    console.print(
        f"  [cyan]{row_count:,} rows[/cyan]  [dim]({size_str} on disk)[/dim]\n"
    )


def _cmd_symbols(args: argparse.Namespace) -> None:
    """List symbols that have options data available from configured providers."""
    from rich.columns import Columns
    from rich.console import Console

    _load_env()

    from optopsy.data.providers import get_available_providers

    console = Console()
    search = getattr(args, "search", None)
    use_pager = not search and console.is_terminal
    found = False

    def _render() -> None:
        nonlocal found
        for provider in get_available_providers():
            if not provider.is_available():
                continue
            symbols = provider.list_available_symbols()
            if symbols is None:
                continue
            found = True

            if search:
                term = search.upper()
                symbols = [s for s in symbols if term in s]

            if not symbols:
                console.print(
                    f"[yellow]No symbols matching '{search}' from {provider.name}.[/yellow]"
                )
                continue

            console.rule(f"{provider.name} — {len(symbols):,} symbols")
            console.print(Columns(symbols, padding=(0, 2), column_first=True))
            console.print()

    if use_pager:
        with console.pager(styles=True):
            _render()
    else:
        _render()

    if not found:
        console.print(
            "[yellow]No data provider supports listing symbols.\n"
            "Set EODHD_API_KEY in your environment or .env file.[/yellow]"
        )


def _cmd_import(args: argparse.Namespace) -> None:
    """Import local parquet files into the PostgreSQL data store."""
    import os

    import pandas as pd
    from rich.console import Console

    _load_env()

    from optopsy.data.providers.cache import get_store

    console = Console()
    store = get_store()

    # Verify we're targeting PostgreSQL
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url.startswith(("postgres://", "postgresql://")):
        console.print(
            "[red]DATABASE_URL is not set or is not PostgreSQL. "
            "Import requires a PostgreSQL database.[/red]"
        )
        return

    for fpath in args.files:
        if not os.path.exists(fpath):
            console.print(f"[red]File not found: {fpath}[/red]")
            continue

        # Auto-detect category from path
        category = args.category
        if not category:
            if "/options/" in fpath or "\\options\\" in fpath:
                category = "options"
            elif "/yf_stocks/" in fpath or "\\yf_stocks\\" in fpath:
                category = "yf_stocks"
            else:
                console.print(
                    f"[yellow]Cannot detect category for {fpath}. Use -c flag.[/yellow]"
                )
                continue

        symbol = os.path.basename(fpath).replace(".parquet", "").upper()

        with console.status(f"Importing {symbol} ({category})..."):
            df = pd.read_parquet(fpath)
            store.write(category, symbol, df)

        console.print(
            f"  [green]Imported {symbol}: {len(df):,} rows into {category}[/green]"
        )


def _build_data_subparsers(
    subparsers: argparse._SubParsersAction,
) -> dict[str, argparse.ArgumentParser]:
    """Add download, symbols, and cache subparsers. Returns named parsers."""
    # --- download ---
    dl_parser = subparsers.add_parser(
        "download",
        help="Download historical market data for one or more symbols",
    )
    dl_parser.add_argument(
        "symbols",
        nargs="+",
        help="One or more US stock ticker symbols (e.g. SPY AAPL TSLA)",
    )
    dl_group = dl_parser.add_mutually_exclusive_group()
    dl_group.add_argument(
        "-o",
        "--options",
        action="store_true",
        default=True,
        help="Download options chain data via EODHD (default)",
    )
    dl_group.add_argument(
        "-s",
        "--stocks",
        action="store_true",
        help="Download stock/index OHLCV data via yfinance (no API key needed)",
    )
    dl_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging"
    )
    dl_parser.set_defaults(func=_cmd_download)

    # --- symbols ---
    sym_parser = subparsers.add_parser(
        "symbols", help="List symbols with options data available for download"
    )
    sym_parser.add_argument(
        "-q",
        "--search",
        default=None,
        help="Filter symbols containing TERM (case-insensitive)",
    )
    sym_parser.set_defaults(func=_cmd_symbols)

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
    clear_category = clear_parser.add_mutually_exclusive_group()
    clear_category.add_argument(
        "-o",
        "--options",
        action="store_true",
        help="Clear only options data",
    )
    clear_category.add_argument(
        "-s",
        "--stocks",
        action="store_true",
        help="Clear only stock data",
    )
    clear_parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip confirmation prompt",
    )
    clear_parser.set_defaults(func=_cmd_cache_clear)

    # --- import ---
    import_parser = subparsers.add_parser(
        "import",
        help="Import local parquet files into the PostgreSQL data store",
    )
    import_parser.add_argument(
        "files",
        nargs="+",
        help="Parquet file paths (e.g. ~/.optopsy/cache/options/SPY.parquet)",
    )
    import_parser.add_argument(
        "-c",
        "--category",
        choices=["options", "yf_stocks"],
        default=None,
        help="Data category (auto-detected from path if omitted)",
    )
    import_parser.set_defaults(func=_cmd_import)

    return {"cache": cache_parser}


def main(argv: list[str] | None = None) -> None:
    """Parse CLI arguments and dispatch to the appropriate subcommand."""
    parser = argparse.ArgumentParser(
        prog="optopsy-data",
        description="Optopsy Data — download and manage market data",
    )
    subparsers = parser.add_subparsers(dest="command")
    named = _build_data_subparsers(subparsers)

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
    elif not hasattr(args, "func"):
        # e.g. "optopsy-data cache" with no sub-subcommand
        if args.command == "cache":
            named["cache"].print_help()
        else:
            parser.print_help()
    else:
        args.func(args)
