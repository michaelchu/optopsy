"""Chainlit web application for the Optopsy Chat UI.

This module is the Chainlit entry point.  It sets up:

- **Database** — SQLite-backed persistence for chat threads, steps, and feedback
  (``_init_db_sync()``).
- **Authentication** — Header-based auto-auth for single-user local use.
- **Session lifecycle** — ``on_chat_start`` creates a fresh ``OptopsyAgent``;
  ``on_chat_resume`` rebuilds message history from persisted steps.
- **Message handling** — ``on_message`` processes user input, handles CSV
  drag-and-drop uploads, and streams LLM responses with tool-call step UI.
- **Conversation starters** — Clickable quick-start prompts for new chats.
- **Chat settings** — Persistent parameter controls (DTE, OTM%, slippage).
- **Action buttons** — Quick follow-up actions on strategy results.
- **Rich elements** — Interactive DataFrames and CSV file exports.
"""

import base64
import json
import logging
import math
import mimetypes
import os
import struct
from pathlib import Path
from typing import Any

from dotenv import find_dotenv, load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)

# .env takes priority over shell env so there's no conflict with
# unrelated exports (e.g. work credentials in .zshrc).
_env_path = find_dotenv() or str(Path(__file__).resolve().parent.parent.parent / ".env")
load_dotenv(_env_path, override=True)

import chainlit as cl
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from chainlit.server import app as chainlit_app
from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.routing import APIRoute

import optopsy as op
from optopsy.ui.agent import OptopsyAgent, _sanitize_tool_messages
from optopsy.ui.providers import get_provider_names
from optopsy.ui.storage import STORAGE_DIR, STORAGE_ROUTE_PREFIX, LocalStorageClient

# ---------------------------------------------------------------------------
# Plotly binary-array patch
# ---------------------------------------------------------------------------
# Plotly's ``pio.to_json`` encodes large numeric arrays as base-64 blobs
# (``{dtype, bdata}``).  Plotly.js understands this when rendering live, but
# Chainlit's element persistence stores the raw JSON and on thread resume the
# frontend fails to decode the binary arrays, resulting in empty charts.
# We monkey-patch ``cl.Plotly.__post_init__`` to replace bdata with plain
# lists so the persisted JSON is universally readable.

_BDATA_DTYPE_MAP = {
    "f8": "d",
    "f4": "f",
    "i4": "i",
    "i2": "h",
    "i1": "b",
    "u4": "I",
    "u2": "H",
    "u1": "B",
}


def _sanitize_float(val):
    """Convert NaN/Infinity to None (JSON null) to produce valid JSON."""
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    return val


def _decode_bdata(obj):
    """Recursively replace ``{dtype, bdata}`` dicts with plain lists."""
    if isinstance(obj, dict):
        if "bdata" in obj and "dtype" in obj:
            raw = base64.b64decode(obj["bdata"])
            fmt = _BDATA_DTYPE_MAP.get(obj["dtype"], "d")
            count = len(raw) // struct.calcsize(fmt)
            return [_sanitize_float(v) for v in struct.unpack(f"<{count}{fmt}", raw)]
        return {k: _decode_bdata(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decode_bdata(item) for item in obj]
    if isinstance(obj, float):
        return _sanitize_float(obj)
    return obj


_original_plotly_post_init = cl.Plotly.__post_init__


def _patched_plotly_post_init(self):
    _original_plotly_post_init(self)
    # Re-serialize with bdata decoded to plain arrays.
    # Indicator traces (RSI, MACD, Bollinger Bands, etc.) produce NaN for
    # the initial lookback window; standard JSON doesn't support NaN/Infinity
    # literals, so _decode_bdata converts them to null.
    try:
        decoded = _decode_bdata(json.loads(self.content))
        self.content = json.dumps(decoded, separators=(",", ":"))
    except Exception:
        # Fall back to the original content rather than breaking chart creation.
        logging.getLogger(__name__).debug(
            "bdata decode failed, using original", exc_info=True
        )


cl.Plotly.__post_init__ = _patched_plotly_post_init

DB_PATH = Path("~/.optopsy/chat.db").expanduser()

_DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    identifier TEXT NOT NULL UNIQUE,
    "createdAt" TEXT NOT NULL,
    metadata TEXT DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS threads (
    id TEXT PRIMARY KEY,
    "userId" TEXT,
    "userIdentifier" TEXT,
    "createdAt" TEXT,
    name TEXT,
    metadata TEXT,
    tags TEXT,
    FOREIGN KEY("userId") REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS steps (
    id TEXT PRIMARY KEY,
    name TEXT,
    type TEXT,
    "threadId" TEXT NOT NULL,
    "parentId" TEXT,
    streaming INTEGER DEFAULT 0,
    "waitForAnswer" INTEGER,
    "isError" INTEGER,
    metadata TEXT DEFAULT '{}',
    tags TEXT,
    input TEXT,
    output TEXT,
    "createdAt" TEXT,
    start TEXT,
    "end" TEXT,
    generation TEXT DEFAULT '{}',
    "defaultOpen" INTEGER DEFAULT 0,
    "showInput" TEXT,
    language TEXT,
    FOREIGN KEY("threadId") REFERENCES threads(id)
);
CREATE TABLE IF NOT EXISTS feedbacks (
    id TEXT PRIMARY KEY,
    "forId" TEXT NOT NULL,
    value REAL,
    comment TEXT,
    FOREIGN KEY("forId") REFERENCES steps(id)
);
CREATE TABLE IF NOT EXISTS elements (
    id TEXT PRIMARY KEY,
    "threadId" TEXT NOT NULL,
    type TEXT,
    "chainlitKey" TEXT,
    url TEXT,
    "objectKey" TEXT,
    name TEXT,
    display TEXT,
    size TEXT,
    language TEXT,
    page TEXT,
    "forId" TEXT,
    mime TEXT,
    props TEXT DEFAULT '{}',
    "autoPlay" TEXT,
    "playerConfig" TEXT,
    FOREIGN KEY("threadId") REFERENCES threads(id)
);
"""


# Initialize database synchronously at module import time, before Chainlit
# tries to use it via @cl.data_layer or authentication callbacks.
def _init_db_sync() -> None:
    import sqlite3

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(_DB_SCHEMA)
        # Add columns introduced in newer Chainlit versions (safe to run repeatedly).
        for col, definition in [
            ("defaultOpen", "INTEGER DEFAULT 0"),
            ("waitForAnswer", "INTEGER"),
        ]:
            try:
                conn.execute(f'ALTER TABLE steps ADD COLUMN "{col}" {definition}')
            except Exception:
                pass  # column already exists
        conn.commit()
    finally:
        conn.close()


_init_db_sync()

_storage_client = LocalStorageClient()


async def _lookup_element_mime(object_key: str) -> str | None:
    """Look up the stored mime type for an element by its object key."""
    import aiosqlite

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                'SELECT mime FROM elements WHERE "objectKey" = ? LIMIT 1',
                (object_key,),
            )
            row = await cursor.fetchone()
            if row and row[0] and row[0] != "application/octet-stream":
                return row[0]
    except Exception:
        pass
    return None


async def _serve_storage_file(file_path: str):
    """Serve persisted element files (e.g. Plotly chart JSON) from local storage."""
    full_path = (STORAGE_DIR / file_path).resolve()
    if not full_path.is_relative_to(STORAGE_DIR.resolve()):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    # Look up the element's stored mime type from the database first.
    # This is important because Chainlit's frontend ``useFetch`` hook parses
    # the response as JSON when Content-Type includes "application/json"
    # (via ``response.json()``), but returns raw text otherwise (via
    # ``response.text()``).  Plotly elements need ``application/json`` so the
    # frontend receives a parsed object, while Dataframe elements need
    # ``text/plain`` so the frontend receives a string that ``JSON.parse()``
    # can handle in ``Dataframe.tsx``.
    media_type = await _lookup_element_mime(file_path)
    if not media_type:
        media_type = mimetypes.guess_type(str(full_path))[0]
    if not media_type:
        # Sniff: if the file starts with '{' or '[' it's almost certainly JSON.
        with open(full_path, "rb") as _f:
            first_byte = _f.read(1).lstrip()
        if first_byte in (b"{", b"["):
            media_type = "application/json"
        else:
            media_type = "application/octet-stream"
    return FileResponse(full_path, media_type=media_type)


# Chainlit registers a catch-all ``/{full_path:path}`` route during import that
# serves the SPA index.html.  Routes added via ``@app.get(...)`` after that
# import land *after* the catch-all in FastAPI's route list, so the catch-all
# matches first and returns HTML instead of the actual file.  We work around
# this by inserting our storage route *before* the catch-all.
_storage_route = APIRoute(
    path=f"{STORAGE_ROUTE_PREFIX}/{{file_path:path}}",
    endpoint=_serve_storage_file,
    methods=["GET"],
)
# Find the catch-all and insert just before it.
_insert_idx = next(
    (
        i
        for i, r in enumerate(chainlit_app.routes)
        if hasattr(r, "path") and r.path == "/{full_path:path}"
    ),
    len(chainlit_app.routes),
)
chainlit_app.routes.insert(_insert_idx, _storage_route)


@cl.data_layer
def get_data_layer() -> SQLAlchemyDataLayer:
    return SQLAlchemyDataLayer(
        conninfo=f"sqlite+aiosqlite:///{DB_PATH}",
        storage_provider=_storage_client,
    )


@cl.header_auth_callback
async def header_auth_callback(headers) -> cl.User:
    # Single-user local app — auto-authenticate without a login form.
    return cl.User(identifier="local", metadata={"role": "user"})


@cl.set_starters
async def set_starters():
    """Clickable quick-start prompts shown at the beginning of each new chat."""
    return [
        cl.Starter(
            label="Backtest iron condors on SPY",
            message="Download SPY options data and run an iron condor backtest with 45 DTE entry",
        ),
        cl.Starter(
            label="Compare call vs put spreads",
            message="Load SPY data and compare long call spreads against long put spreads",
        ),
        cl.Starter(
            label="RSI-filtered covered calls",
            message="Run covered calls on SPY with an RSI below 30 entry signal",
        ),
        cl.Starter(
            label="List available strategies",
            message="List all available options strategies and briefly describe each one",
        ),
    ]


@cl.on_chat_start
async def on_chat_start():
    model = os.environ.get("OPTOPSY_MODEL", "anthropic/claude-haiku-4-5-20251001")
    agent = OptopsyAgent(model=model)
    cl.user_session.set("agent", agent)
    cl.user_session.set("messages", [])

    # Detect configured data providers
    providers = get_provider_names()

    provider_line = ""
    if providers:
        provider_line = f"Data providers: {', '.join(providers)}\n"
    else:
        provider_line = (
            "No data providers configured. "
            "Add API keys to your `.env` file to enable live data.\n"
        )

    # Initialize chat settings for persistent parameter controls
    settings = cl.ChatSettings(
        [
            cl.input_widget.Slider(
                id="max_entry_dte",
                label="Max Entry DTE",
                initial=90,
                min=7,
                max=365,
                step=7,
                description="Maximum days to expiration at entry",
            ),
            cl.input_widget.Slider(
                id="max_otm_pct",
                label="Max OTM %",
                initial=0.5,
                min=0.01,
                max=1.0,
                step=0.01,
                description="Maximum out-of-the-money percentage",
            ),
            cl.input_widget.Select(
                id="slippage",
                label="Slippage Model",
                values=["mid", "spread", "liquidity"],
                initial_value="mid",
                description="Price fill model for backtesting",
            ),
        ]
    )
    await settings.send()

    await cl.Message(
        content=(
            "Welcome to **Optopsy Chat** — your options strategy backtesting assistant.\n\n"
            "**Getting started:**\n"
            "1. Fetch options data or drop a CSV file into the chat\n"
            "2. Preview the data\n"
            "3. Run any of 28 options strategies — just describe what you want\n\n"
            "Use the **settings panel** (gear icon) to adjust default parameters, "
            "or click a **starter prompt** above to jump right in.\n\n"
            "CSV format: `underlying_symbol, underlying_price, option_type, "
            "expiration, quote_date, strike, bid, ask`\n\n"
            f"{provider_line}"
            f"Using model: `{model}` (set `OPTOPSY_MODEL` env var to change)"
        )
    ).send()


@cl.on_chat_resume
async def on_chat_resume(thread: cl.types.ThreadDict):
    """Restore agent state when a WebSocket reconnects to an existing thread.

    Without this handler Chainlit falls back to on_chat_start, which creates a
    fresh session and sends the welcome message again mid-conversation.

    Dataset and signal DataFrames are in-process state that cannot be persisted
    across sessions.  We inject a system-level note into the history so the LLM
    knows it must reload any data before running strategies.
    """
    model = os.environ.get("OPTOPSY_MODEL", "anthropic/claude-haiku-4-5-20251001")
    agent = OptopsyAgent(model=model)

    # Rebuild message history from the persisted thread, including tool calls.
    # Chainlit step types:
    #   "user_message"      -> role: user
    #   "assistant_message" -> role: assistant  (may embed tool_calls metadata)
    #   "tool"              -> role: tool        (tool result)
    def _parse_meta(step: Any) -> dict[str, Any]:
        """SQLite stores metadata as a JSON string; parse it to a dict."""
        raw = step.get("metadata") or {}
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except (ValueError, TypeError):
                return {}
        return raw

    messages: list[dict] = []
    for step in thread.get("steps", []):
        step_type = step.get("type")
        if step_type == "user_message":
            messages.append({"role": "user", "content": step.get("output", "")})
        elif step_type == "assistant_message":
            msg: dict = {"role": "assistant", "content": step.get("output", "")}
            # Restore tool_calls array if stored in step metadata
            tool_calls = _parse_meta(step).get("tool_calls")
            if tool_calls:
                msg["tool_calls"] = tool_calls
            messages.append(msg)
        elif step_type == "tool":
            meta = _parse_meta(step)
            tool_call_id = meta.get("tool_call_id", step.get("id", ""))
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": step.get("output", ""),
                }
            )

    # Drop orphaned tool messages whose tool_call_id has no matching
    # tool_calls entry — prevents Anthropic API "unexpected tool_use_id"
    # errors on resume.  Uses the same function applied in agent.chat().
    messages = _sanitize_tool_messages(messages)

    # Datasets and signals are lost on reconnect (they live only in memory).
    # Append a concise reminder so the LLM doesn't try to use stale state.
    if any(m.get("role") == "tool" for m in messages):
        messages.append(
            {
                "role": "user",
                "content": (
                    "[Session resumed] In-memory datasets and signals were cleared "
                    "during the reconnect. Please reload any data before running "
                    "strategies."
                ),
            }
        )

    cl.user_session.set("agent", agent)
    cl.user_session.set("messages", messages)


@cl.on_settings_update
async def on_settings_update(settings: dict):
    """Persist chat settings so they can be injected into strategy calls."""
    cl.user_session.set("chat_settings", settings)


# ---------------------------------------------------------------------------
# Helper functions for rich UI elements
# ---------------------------------------------------------------------------


def _build_settings_context(settings: dict) -> str:
    """Build a system-context note from chat settings for the LLM.

    Only includes settings that differ from defaults so the LLM knows the
    user has actively configured them.
    """
    parts = []
    defaults = {
        "max_entry_dte": 90,
        "max_otm_pct": 0.5,
        "slippage": "mid",
    }
    for key, default in defaults.items():
        val = settings.get(key)
        if val is not None and val != default:
            if key == "max_otm_pct":
                parts.append(f"max_otm_pct={val:.2f}")
            else:
                parts.append(f"{key}={val}")
    if parts:
        return f"[User settings: {', '.join(parts)}]"
    return ""


def _attach_result_elements(result: Any, tool_name: str, df_elements: list) -> None:
    """Attach interactive DataFrame and downloadable CSV to the element list.

    Called when a strategy tool produces a result DataFrame stored in
    ``result._result_df``.
    """
    import pandas as pd

    df: pd.DataFrame = result._result_df
    if df is None or df.empty:
        return

    # Stringify Interval columns (e.g. dte_range, otm_pct_range) so they
    # render as readable text instead of "[object Object]" in the browser.
    # pd.cut() produces CategoricalDtype with Interval categories, not IntervalDtype.
    for col in df.columns:
        dtype = df[col].dtype
        if isinstance(dtype, pd.IntervalDtype) or (
            isinstance(dtype, pd.CategoricalDtype)
            and isinstance(dtype.categories.dtype, pd.IntervalDtype)
        ):
            df[col] = df[col].astype(str)

    label = tool_name.replace("_", " ").title()

    # Interactive paginated table
    df_elements.append(
        cl.Dataframe(
            name=f"{label} Results",
            data=df,
            display="inline",
            size="large",
            mime="text/plain",
        )
    )

    # Downloadable CSV file
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    df_elements.append(
        cl.File(
            name=f"{tool_name}_results.csv",
            content=csv_bytes,
            display="inline",
            mime="text/csv",
        )
    )


def _build_strategy_actions(last_strategy_info: dict) -> list[cl.Action]:
    """Build quick follow-up action buttons after a strategy run."""
    if not last_strategy_info.get("strategy_name"):
        return []

    strategy = last_strategy_info["strategy_name"]
    args = last_strategy_info.get("arguments", {})

    actions = []

    # "Show raw trades" or "Show aggregated" toggle
    is_raw = args.get("raw", False)
    if is_raw:
        actions.append(
            cl.Action(
                name="rerun_strategy",
                payload={"strategy": strategy, "toggle": "aggregated", **args},
                label="Show Aggregated Stats",
                tooltip="Re-run with raw=false for summary statistics",
            )
        )
    else:
        actions.append(
            cl.Action(
                name="rerun_strategy",
                payload={"strategy": strategy, "toggle": "raw", **args},
                label="Show Raw Trades",
                tooltip="Re-run with raw=true to see individual trades",
            )
        )

    # "Try wider DTE" button
    current_dte = args.get("max_entry_dte", 90)
    wider_dte = min(current_dte + 30, 365)
    if wider_dte != current_dte:
        actions.append(
            cl.Action(
                name="rerun_strategy",
                payload={
                    "strategy": strategy,
                    "adjust": "wider_dte",
                    "dte": wider_dte,
                    **args,
                },
                label=f"Try DTE {wider_dte}",
                tooltip=f"Re-run {strategy} with max_entry_dte={wider_dte}",
            )
        )

    # "Create chart" button
    actions.append(
        cl.Action(
            name="create_chart_action",
            payload={"strategy": strategy},
            label="Chart Results",
            tooltip="Create a visualization of the strategy results",
        )
    )

    return actions


@cl.action_callback("rerun_strategy")
async def on_rerun_strategy(action: cl.Action):
    """Handle quick re-run action buttons on strategy results."""
    payload = action.payload
    strategy = payload.get("strategy", "")
    toggle = payload.get("toggle")
    adjust = payload.get("adjust")

    if toggle == "raw":
        prompt = f"Re-run {strategy} with raw=true to show individual trades"
    elif toggle == "aggregated":
        prompt = f"Re-run {strategy} with raw=false to show aggregated stats"
    elif adjust == "wider_dte":
        dte = payload.get("dte", 120)
        prompt = f"Re-run {strategy} with max_entry_dte={dte}"
    else:
        prompt = f"Re-run {strategy}"

    # Send as a user message to trigger the normal flow
    await cl.Message(content=prompt, author="user").send()
    # Process through the message handler
    msg = cl.Message(content=prompt)
    await on_message(msg)


@cl.action_callback("create_chart_action")
async def on_create_chart(action: cl.Action):
    """Handle chart creation action button."""
    strategy = action.payload.get("strategy", "")
    prompt = f"Create a bar chart comparing the results of {strategy} by DTE range"
    await cl.Message(content=prompt, author="user").send()
    msg = cl.Message(content=prompt)
    await on_message(msg)


@cl.on_message
async def on_message(message: cl.Message):
    agent: OptopsyAgent = cl.user_session.get("agent")
    messages: list = cl.user_session.get("messages")

    # Guard: session state is missing (e.g. user deleted the thread then typed).
    # Re-initialize in-place rather than redirecting so the message isn't lost.
    if agent is None or messages is None:
        model = os.environ.get("OPTOPSY_MODEL", "anthropic/claude-haiku-4-5-20251001")
        agent = OptopsyAgent(model=model)
        messages = []
        cl.user_session.set("agent", agent)
        cl.user_session.set("messages", messages)

    # Handle CSV file uploads via drag-and-drop
    csv_elements = [
        el
        for el in (message.elements or [])
        if el.name and el.name.lower().endswith(".csv") and el.path
    ]
    for el in csv_elements:
        try:
            assert el.path is not None
            df = op.csv_data(el.path)
            label = el.name
            agent.datasets[label] = df
            agent.dataset = df

            date_range = ""
            if "quote_date" in df.columns:
                d_min = df["quote_date"].min().date()
                d_max = df["quote_date"].max().date()
                date_range = f"Date range: {d_min} to {d_max}\n"

            await cl.Message(
                content=(
                    f"Loaded **{label}** — "
                    f"{len(df):,} rows, {len(df.columns)} columns\n"
                    f"{date_range}"
                    f"```\n{df.head().to_string()}\n```"
                )
            ).send()
        except Exception as e:
            await cl.Message(content=f"Failed to load **{el.name}**: {e}").send()

    # Inject chat settings defaults into user message context so the LLM
    # is aware of the user's preferred parameters.
    chat_settings = cl.user_session.get("chat_settings") or {}
    settings_context = _build_settings_context(chat_settings)
    user_content = message.content
    if settings_context:
        user_content = f"{message.content}\n\n{settings_context}"
    messages.append({"role": "user", "content": user_content})

    # Show tool calls as expandable steps with a loading indicator.
    # tool_call_id is stored in step metadata so on_chat_resume can reconstruct
    # the tool message history with the correct ID.
    # Chart figures are collected and attached to the final response message
    # so they appear in the main chat area, not inside the tool accordion.
    chart_elements: list[cl.ElementBased] = []
    # Collect DataFrame elements and downloadable CSV files from tool results.
    df_elements: list[cl.ElementBased] = []
    # Track the last strategy run for action buttons.
    last_strategy_info: dict[str, Any] = {}

    async def on_tool_call(tool_name, arguments, result, tool_call_id=""):
        async with cl.Step(name=tool_name, type="tool") as step:
            step.input = str(arguments)
            step.output = result.user_display
            if result.chart_figure is not None:
                chart_elements.append(
                    cl.Plotly(
                        name=f"chart_{len(chart_elements)}",
                        figure=result.chart_figure,
                        display="inline",
                    )
                )
            # Attach interactive DataFrame and downloadable CSV for strategy results.
            # Clear previous elements so only the last strategy call's results
            # are shown (prevents duplicate side-by-side tables when the LLM
            # re-runs a strategy in the same turn).
            if tool_name in ("run_strategy", "scan_strategies") and hasattr(
                result, "_result_df"
            ):
                df_elements.clear()
                _attach_result_elements(result, tool_name, df_elements)
            if tool_call_id:
                step.metadata = {"tool_call_id": tool_call_id}
            # Track last strategy call for action buttons
            if tool_name == "run_strategy":
                last_strategy_info["strategy_name"] = arguments.get("strategy_name", "")
                last_strategy_info["arguments"] = arguments

    # Delay creating the response message until after all tool steps finish,
    # so the final answer always appears below the tool step items.
    response_msg: cl.Message | None = None

    async def on_thinking_token(token: str):
        # Intermediate reasoning — silently discard; we only show the final answer.
        pass

    async def on_token(token: str):
        nonlocal response_msg
        if response_msg is None:
            # Attach chart + dataframe elements up front — tool calls finish
            # before streaming begins, so elements are already populated.
            all_elements = chart_elements + df_elements
            response_msg = cl.Message(content="", elements=all_elements)
            await response_msg.send()
        await response_msg.stream_token(token)

    async def on_assistant_tool_calls(tool_calls: list[dict]):
        # Store tool_calls metadata for session resume; no message to clear.
        nonlocal response_msg
        if response_msg is not None:
            response_msg.metadata = {"tool_calls": tool_calls}
            await response_msg.update()

    try:
        result_text, updated_messages = await agent.chat(
            messages,
            on_tool_call=on_tool_call,
            on_token=on_token,
            on_thinking_token=on_thinking_token,
            on_assistant_tool_calls=on_assistant_tool_calls,
        )
        # Build action buttons if a strategy was run
        actions = _build_strategy_actions(last_strategy_info)

        all_elements = chart_elements + df_elements
        # If on_token never fired (e.g. result came back all at once), send now.
        if response_msg is None:
            response_msg = cl.Message(
                content=result_text, elements=all_elements, actions=actions
            )
            await response_msg.send()
        else:
            response_msg.content = result_text
            if all_elements:
                response_msg.elements = all_elements
            if actions:
                response_msg.actions = actions
            await response_msg.update()
        cl.user_session.set("messages", updated_messages)
    except Exception as e:
        if response_msg is None:
            response_msg = cl.Message(content=f"Error: {e}")
            await response_msg.send()
        else:
            response_msg.content = f"Error: {e}"
            await response_msg.update()


def main():
    from optopsy.ui.cli import main as cli_main

    cli_main()
