import json
import logging
import os
from pathlib import Path

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

import optopsy as op
from optopsy.ui.agent import OptopsyAgent
from optopsy.ui.providers import get_provider_names

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


@cl.data_layer
def get_data_layer() -> SQLAlchemyDataLayer:
    return SQLAlchemyDataLayer(conninfo=f"sqlite+aiosqlite:///{DB_PATH}")


@cl.header_auth_callback
async def header_auth_callback(headers) -> cl.User:
    # Single-user local app — auto-authenticate without a login form.
    return cl.User(identifier="local", metadata={"role": "user"})


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

    await cl.Message(
        content=(
            "Welcome to **Optopsy Chat** — your options strategy backtesting assistant.\n\n"
            "**Getting started:**\n"
            "1. Fetch options data or drop a CSV file into the chat\n"
            "2. Preview the data\n"
            "3. Run any of 28 options strategies — just describe what you want\n\n"
            "**Example prompts:**\n"
            '- *"Fetch AAPL options data from the last 6 months"*\n'
            '- *"Run a long call spread with 60 DTE entry"*\n'
            '- *"Compare iron condors vs iron butterflies"*\n\n'
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
    def _parse_meta(step: dict) -> dict:
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

    messages.append({"role": "user", "content": message.content})

    # Show tool calls as expandable steps with a loading indicator.
    # tool_call_id is stored in step metadata so on_chat_resume can reconstruct
    # the tool message history with the correct ID.
    async def on_tool_call(tool_name, arguments, result, tool_call_id=""):
        async with cl.Step(name=tool_name, type="tool") as step:
            step.input = str(arguments)
            step.output = result
            if tool_call_id:
                step.metadata = {"tool_call_id": tool_call_id}

    # Delay creating the response message until after all tool steps finish,
    # so the final answer always appears below the tool step items.
    response_msg: cl.Message | None = None

    async def on_thinking_token(token: str):
        # Intermediate reasoning — silently discard; we only show the final answer.
        pass

    async def on_token(token: str):
        nonlocal response_msg
        if response_msg is None:
            response_msg = cl.Message(content="")
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
        # If on_token never fired (e.g. result came back all at once), send now.
        if response_msg is None:
            response_msg = cl.Message(content=result_text)
            await response_msg.send()
        else:
            response_msg.content = result_text
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
