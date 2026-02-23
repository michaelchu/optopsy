"""Tests for optopsy.ui.app — on_message, on_chat_start, on_chat_resume.

These tests exercise Chainlit handlers by importing app.py (which registers
Chainlit decorators) and calling the functions directly with mocked objects.
"""

import asyncio
import datetime
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

pytest.importorskip("pyarrow", reason="UI extras not installed")
pytest.importorskip("chainlit", reason="chainlit not installed")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def option_csv_data():
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
        ["SPX", 220.0, "call", exp_date, quote_dates[1], 212.5, 7.45, 7.55],
        ["SPX", 220.0, "call", exp_date, quote_dates[1], 215.0, 4.96, 5.05],
    ]
    return pd.DataFrame(data=d, columns=cols)


def _make_mock_element(name: str, path: str):
    el = MagicMock()
    el.name = name
    el.path = path
    return el


def _make_session_and_agent(agent=None, messages=None):
    """Build a mock cl.user_session and agent."""
    if agent is None:
        agent = MagicMock()
        agent.datasets = {}
        agent.dataset = None
        agent.chat = AsyncMock(
            return_value=("ok", [{"role": "assistant", "content": "ok"}])
        )
    if messages is None:
        messages = []

    store = {"agent": agent, "messages": messages}
    session = MagicMock()
    session.get = lambda key: store.get(key)
    session.set = lambda key, val: store.__setitem__(key, val)
    return session, store, agent


# ---------------------------------------------------------------------------
# on_message tests
# ---------------------------------------------------------------------------


class TestOnMessageCSVUpload:
    def test_valid_csv_stores_dataset(self, option_csv_data):
        """CSV upload stores dataset on agent and sets active dataset."""

        async def _run():
            from optopsy.ui.app import on_message

            session, store, agent = _make_session_and_agent()

            mock_msg = MagicMock()
            mock_msg.content = "check this data"
            mock_msg.elements = [_make_mock_element("SPX_2018.csv", "/tmp/test.csv")]

            mock_cl_msg = MagicMock()
            mock_cl_msg.send = AsyncMock()
            mock_cl_msg.update = AsyncMock()
            mock_cl_msg.stream_token = AsyncMock()

            # Mock cl.Step as async context manager
            mock_step = MagicMock()
            mock_step.__aenter__ = AsyncMock(return_value=mock_step)
            mock_step.__aexit__ = AsyncMock(return_value=False)

            import chainlit as cl

            import optopsy as op

            sent_contents = []

            def capture_message(**kwargs):
                content = kwargs.get("content", "")
                sent_contents.append(content)
                return mock_cl_msg

            with (
                patch.object(cl, "user_session", session),
                patch.object(cl, "Message", side_effect=capture_message),
                patch.object(cl, "Step", return_value=mock_step),
                patch.object(op, "csv_data", return_value=option_csv_data),
            ):
                await on_message(mock_msg)

            assert "SPX_2018.csv" in agent.datasets
            assert agent.dataset is option_csv_data
            # Verify the upload confirmation message includes row count
            upload_msg = next(c for c in sent_contents if "SPX_2018.csv" in c)
            assert "4" in upload_msg  # 4 rows
            assert "Loaded" in upload_msg

        asyncio.run(_run())

    def test_csv_upload_error_displayed(self):
        """CSV upload failure sends error message with filename and error text."""

        async def _run():
            from optopsy.ui.app import on_message

            session, store, agent = _make_session_and_agent()

            mock_msg = MagicMock()
            mock_msg.content = ""
            mock_msg.elements = [_make_mock_element("bad.csv", "/tmp/bad.csv")]

            sent_contents = []
            mock_cl_msg = MagicMock()
            mock_cl_msg.send = AsyncMock()
            mock_cl_msg.update = AsyncMock()
            mock_cl_msg.stream_token = AsyncMock()

            import chainlit as cl

            import optopsy as op

            def capture_message(**kwargs):
                content = kwargs.get("content", "")
                sent_contents.append(content)
                return mock_cl_msg

            with (
                patch.object(cl, "user_session", session),
                patch.object(cl, "Message", side_effect=capture_message),
                patch.object(op, "csv_data", side_effect=ValueError("bad CSV")),
            ):
                await on_message(mock_msg)

            error_msg = next(c for c in sent_contents if "Failed" in c)
            assert "bad.csv" in error_msg
            assert "bad CSV" in error_msg

        asyncio.run(_run())

    def test_no_csv_passes_correct_args_to_chat(self):
        """No CSV elements — agent.chat is called with the user message in history."""

        async def _run():
            from optopsy.ui.app import on_message

            session, store, agent = _make_session_and_agent()

            mock_msg = MagicMock()
            mock_msg.content = "run long_calls"
            mock_msg.elements = []

            mock_cl_msg = MagicMock()
            mock_cl_msg.send = AsyncMock()
            mock_cl_msg.update = AsyncMock()
            mock_cl_msg.stream_token = AsyncMock()

            import chainlit as cl

            with (
                patch.object(cl, "user_session", session),
                patch.object(cl, "Message", return_value=mock_cl_msg),
            ):
                await on_message(mock_msg)

            agent.chat.assert_called_once()
            # Verify the messages list passed to chat contains the user message
            call_args = agent.chat.call_args
            messages_arg = call_args[0][0]
            assert any(
                m["role"] == "user" and m["content"] == "run long_calls"
                for m in messages_arg
            )
            # Verify callbacks were passed
            assert "on_tool_call" in call_args[1]
            assert "on_token" in call_args[1]

        asyncio.run(_run())

    def test_missing_session_reinitialized(self):
        """When agent is None in session, it is re-initialized."""

        async def _run():
            from optopsy.ui.app import on_message

            store: dict = {"agent": None, "messages": None}
            session = MagicMock()
            session.get = lambda key: store.get(key)
            session.set = lambda key, val: store.__setitem__(key, val)

            mock_msg = MagicMock()
            mock_msg.content = "hello"
            mock_msg.elements = []

            mock_cl_msg = MagicMock()
            mock_cl_msg.send = AsyncMock()
            mock_cl_msg.update = AsyncMock()
            mock_cl_msg.stream_token = AsyncMock()

            import chainlit as cl

            mock_agent = MagicMock()
            mock_agent.chat = AsyncMock(
                return_value=(
                    "hi",
                    [{"role": "assistant", "content": "hi"}],
                )
            )

            with (
                patch.object(cl, "user_session", session),
                patch.object(cl, "Message", return_value=mock_cl_msg),
                patch(
                    "optopsy.ui.app.OptopsyAgent",
                    return_value=mock_agent,
                ),
            ):
                await on_message(mock_msg)

            assert store["agent"] is mock_agent
            assert isinstance(store["messages"], list)

        asyncio.run(_run())

    def test_chat_exception_displayed(self):
        """Exception from agent.chat is shown to user as Error: message."""

        async def _run():
            from optopsy.ui.app import on_message

            agent = MagicMock()
            agent.datasets = {}
            agent.chat = AsyncMock(side_effect=RuntimeError("LLM exploded"))

            session, store, _ = _make_session_and_agent(agent=agent)

            mock_msg = MagicMock()
            mock_msg.content = "do something"
            mock_msg.elements = []

            sent_contents = []
            mock_cl_msg = MagicMock()
            mock_cl_msg.send = AsyncMock()
            mock_cl_msg.update = AsyncMock()
            mock_cl_msg.stream_token = AsyncMock()

            import chainlit as cl

            def capture_message(**kwargs):
                c = kwargs.get("content", "")
                sent_contents.append(c)
                return mock_cl_msg

            with (
                patch.object(cl, "user_session", session),
                patch.object(cl, "Message", side_effect=capture_message),
            ):
                await on_message(mock_msg)

            error_msg = next(c for c in sent_contents if "LLM exploded" in c)
            assert error_msg.startswith("Error:")

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# on_chat_resume tests
# ---------------------------------------------------------------------------


class TestOnChatResume:
    def test_rebuilds_message_history_from_steps(self):
        """on_chat_resume reconstructs messages from persisted thread steps."""

        async def _run():
            from optopsy.ui.app import on_chat_resume

            store: dict = {}
            session = MagicMock()
            session.get = lambda key: store.get(key)
            session.set = lambda key, val: store.__setitem__(key, val)

            thread = {
                "steps": [
                    {"type": "user_message", "output": "load data"},
                    {
                        "type": "assistant_message",
                        "output": "Loading...",
                        "metadata": json.dumps(
                            {
                                "tool_calls": [
                                    {
                                        "id": "tc1",
                                        "function": {"name": "load_csv_data"},
                                    }
                                ]
                            }
                        ),
                    },
                    {
                        "type": "tool",
                        "output": "Loaded 100 rows",
                        "id": "step_1",
                        "metadata": json.dumps({"tool_call_id": "tc1"}),
                    },
                    {"type": "user_message", "output": "run strategy"},
                    {"type": "assistant_message", "output": "Running..."},
                ],
            }

            import chainlit as cl

            with (
                patch.object(cl, "user_session", session),
                patch("optopsy.ui.app.OptopsyAgent") as mock_agent_cls,
            ):
                mock_agent_cls.return_value = MagicMock()
                await on_chat_resume(thread)

            messages = store["messages"]
            # Should have 5 step messages + 1 session-resumed notice
            assert len(messages) == 6

            # Check user messages
            assert messages[0] == {"role": "user", "content": "load data"}
            assert messages[3] == {"role": "user", "content": "run strategy"}

            # Check assistant with tool_calls restored
            assert messages[1]["role"] == "assistant"
            assert "tool_calls" in messages[1]
            assert messages[1]["tool_calls"][0]["id"] == "tc1"

            # Check tool message with tool_call_id from metadata
            assert messages[2]["role"] == "tool"
            assert messages[2]["tool_call_id"] == "tc1"
            assert messages[2]["content"] == "Loaded 100 rows"

            # Check session-resumed notice is appended (because tool messages exist)
            assert messages[5]["role"] == "user"
            assert "Session resumed" in messages[5]["content"]

        asyncio.run(_run())

    def test_no_session_resumed_notice_without_tools(self):
        """on_chat_resume does NOT append session-resumed notice when no tool messages."""

        async def _run():
            from optopsy.ui.app import on_chat_resume

            store: dict = {}
            session = MagicMock()
            session.get = lambda key: store.get(key)
            session.set = lambda key, val: store.__setitem__(key, val)

            thread = {
                "steps": [
                    {"type": "user_message", "output": "hello"},
                    {"type": "assistant_message", "output": "hi there"},
                ],
            }

            import chainlit as cl

            with (
                patch.object(cl, "user_session", session),
                patch("optopsy.ui.app.OptopsyAgent") as mock_agent_cls,
            ):
                mock_agent_cls.return_value = MagicMock()
                await on_chat_resume(thread)

            messages = store["messages"]
            assert len(messages) == 2
            assert not any("Session resumed" in m.get("content", "") for m in messages)

        asyncio.run(_run())

    def test_malformed_metadata_handled_gracefully(self):
        """Steps with non-JSON metadata strings are handled without crashing."""

        async def _run():
            from optopsy.ui.app import on_chat_resume

            store: dict = {}
            session = MagicMock()
            session.get = lambda key: store.get(key)
            session.set = lambda key, val: store.__setitem__(key, val)

            thread = {
                "steps": [
                    {"type": "user_message", "output": "test"},
                    {
                        "type": "assistant_message",
                        "output": "response",
                        "metadata": "not valid json {{{",
                    },
                ],
            }

            import chainlit as cl

            with (
                patch.object(cl, "user_session", session),
                patch("optopsy.ui.app.OptopsyAgent") as mock_agent_cls,
            ):
                mock_agent_cls.return_value = MagicMock()
                await on_chat_resume(thread)

            messages = store["messages"]
            assert len(messages) == 2
            # Should not have tool_calls since metadata was unparseable
            assert "tool_calls" not in messages[1]

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# on_chat_start tests
# ---------------------------------------------------------------------------


class TestOnChatStart:
    def test_welcome_message_with_providers(self):
        """on_chat_start sends welcome message that lists configured providers."""

        async def _run():
            from optopsy.ui.app import on_chat_start

            session = MagicMock()
            sent_contents = []
            mock_cl_msg = MagicMock()
            mock_cl_msg.send = AsyncMock()

            import chainlit as cl

            def capture_message(**kwargs):
                sent_contents.append(kwargs.get("content", ""))
                return mock_cl_msg

            with (
                patch.object(cl, "user_session", session),
                patch.object(cl, "Message", side_effect=capture_message),
                patch("optopsy.ui.app.get_provider_names", return_value=["EODHD"]),
            ):
                await on_chat_start()

            assert len(sent_contents) == 1
            welcome = sent_contents[0]
            assert "Welcome to **Optopsy Chat**" in welcome
            assert "EODHD" in welcome

        asyncio.run(_run())

    def test_welcome_message_without_providers(self):
        """on_chat_start warns when no providers are configured."""

        async def _run():
            from optopsy.ui.app import on_chat_start

            session = MagicMock()
            sent_contents = []
            mock_cl_msg = MagicMock()
            mock_cl_msg.send = AsyncMock()

            import chainlit as cl

            def capture_message(**kwargs):
                sent_contents.append(kwargs.get("content", ""))
                return mock_cl_msg

            with (
                patch.object(cl, "user_session", session),
                patch.object(cl, "Message", side_effect=capture_message),
                patch("optopsy.ui.app.get_provider_names", return_value=[]),
            ):
                await on_chat_start()

            welcome = sent_contents[0]
            assert "No data providers configured" in welcome

        asyncio.run(_run())
