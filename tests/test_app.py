"""Tests for optopsy.ui.app — on_message CSV upload handling.

These tests exercise on_message by importing app.py (which registers Chainlit
handlers) and calling the function directly with mocked Chainlit objects.
"""

import asyncio
import datetime
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
# Tests
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

            with (
                patch.object(cl, "user_session", session),
                patch.object(cl, "Message", return_value=mock_cl_msg),
                patch.object(cl, "Step", return_value=mock_step),
                patch.object(op, "csv_data", return_value=option_csv_data),
            ):
                await on_message(mock_msg)

            assert "SPX_2018.csv" in agent.datasets
            assert agent.dataset is option_csv_data

        asyncio.run(_run())

    def test_csv_upload_error_displayed(self):
        """CSV upload failure sends error message to user."""

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

            assert any("Failed to load" in c for c in sent_contents)
            assert any("bad.csv" in c for c in sent_contents)

        asyncio.run(_run())

    def test_no_csv_calls_chat(self):
        """No CSV elements — goes straight to agent.chat."""

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
        """Exception from agent.chat is shown to user."""

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

            assert any("LLM exploded" in c for c in sent_contents)

        asyncio.run(_run())
