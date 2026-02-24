"""Tests for optopsy.ui.app — on_message, on_chat_start, on_chat_resume.

These tests exercise Chainlit handlers by importing app.py (which registers
Chainlit decorators) and calling the functions directly with mocked objects.
Also covers new Chainlit features: conversation starters, chat settings,
action buttons, rich elements (DataFrame + CSV export), and settings context.
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
            # Verify the message was actually sent to the user
            assert mock_cl_msg.send.called

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

    def test_orphaned_tool_messages_dropped(self):
        """Tool messages without a matching tool_calls entry are removed.

        This prevents Anthropic API errors like 'unexpected tool_use_id found
        in tool_result blocks' when intermediate assistant messages with
        tool_calls were not persisted.
        """

        async def _run():
            from optopsy.ui.app import on_chat_resume

            store: dict = {}
            session = MagicMock()
            session.get = lambda key: store.get(key)
            session.set = lambda key, val: store.__setitem__(key, val)

            thread = {
                "steps": [
                    {"type": "user_message", "output": "fetch SPY data"},
                    # Assistant message WITHOUT tool_calls metadata (not persisted)
                    {"type": "assistant_message", "output": "Fetching..."},
                    # Orphaned tool message — its tool_call_id has no match
                    {
                        "type": "tool",
                        "output": "Loaded 500 rows",
                        "id": "step_orphan",
                        "metadata": json.dumps({"tool_call_id": "toolu_ORPHANED_ID"}),
                    },
                    {"type": "user_message", "output": "run long_calls"},
                    # This assistant message HAS tool_calls
                    {
                        "type": "assistant_message",
                        "output": "Running...",
                        "metadata": json.dumps(
                            {
                                "tool_calls": [
                                    {
                                        "id": "tc_valid",
                                        "function": {"name": "run_strategy"},
                                    }
                                ]
                            }
                        ),
                    },
                    # Valid tool message — matches tc_valid
                    {
                        "type": "tool",
                        "output": "37 aggregated stats",
                        "id": "step_valid",
                        "metadata": json.dumps({"tool_call_id": "tc_valid"}),
                    },
                    {"type": "assistant_message", "output": "Here are the results."},
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
            # Orphaned tool message should be dropped
            tool_msgs = [m for m in messages if m.get("role") == "tool"]
            assert len(tool_msgs) == 1
            assert tool_msgs[0]["tool_call_id"] == "tc_valid"

            # The orphaned tool_call_id should not appear anywhere
            all_tc_ids = [
                m.get("tool_call_id") for m in messages if m.get("role") == "tool"
            ]
            assert "toolu_ORPHANED_ID" not in all_tc_ids

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

            mock_settings = MagicMock()
            mock_settings.send = AsyncMock()

            import chainlit as cl

            def capture_message(**kwargs):
                sent_contents.append(kwargs.get("content", ""))
                return mock_cl_msg

            with (
                patch.object(cl, "user_session", session),
                patch.object(cl, "Message", side_effect=capture_message),
                patch.object(cl, "ChatSettings", return_value=mock_settings),
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

            mock_settings = MagicMock()
            mock_settings.send = AsyncMock()

            import chainlit as cl

            def capture_message(**kwargs):
                sent_contents.append(kwargs.get("content", ""))
                return mock_cl_msg

            with (
                patch.object(cl, "user_session", session),
                patch.object(cl, "Message", side_effect=capture_message),
                patch.object(cl, "ChatSettings", return_value=mock_settings),
                patch("optopsy.ui.app.get_provider_names", return_value=[]),
            ):
                await on_chat_start()

            welcome = sent_contents[0]
            assert "No data providers configured" in welcome

        asyncio.run(_run())

    def test_on_chat_start_sets_session_state(self):
        """on_chat_start stores agent and messages in user_session."""

        async def _run():
            from optopsy.ui.app import on_chat_start

            store: dict = {}
            session = MagicMock()
            session.get = lambda key: store.get(key)
            session.set = lambda key, val: store.__setitem__(key, val)

            mock_cl_msg = MagicMock()
            mock_cl_msg.send = AsyncMock()

            mock_settings = MagicMock()
            mock_settings.send = AsyncMock()

            import chainlit as cl

            with (
                patch.object(cl, "user_session", session),
                patch.object(cl, "Message", return_value=mock_cl_msg),
                patch.object(cl, "ChatSettings", return_value=mock_settings),
                patch("optopsy.ui.app.get_provider_names", return_value=[]),
            ):
                await on_chat_start()

            assert "agent" in store
            assert "messages" in store
            assert isinstance(store["messages"], list)
            assert len(store["messages"]) == 0
            # Agent should be an OptopsyAgent instance
            from optopsy.ui.agent import OptopsyAgent

            assert isinstance(store["agent"], OptopsyAgent)

        asyncio.run(_run())

    def test_on_token_lazy_message_creation(self):
        """on_token creates response_msg lazily on first token."""

        async def _run():
            from optopsy.ui.app import on_message

            agent = MagicMock()
            agent.datasets = {}

            # Simulate chat that calls on_token with tokens
            async def fake_chat(messages, **kwargs):
                on_token = kwargs.get("on_token")
                if on_token:
                    await on_token("Hello ")
                    await on_token("world")
                return "Hello world", [
                    {"role": "user", "content": "hi"},
                    {"role": "assistant", "content": "Hello world"},
                ]

            agent.chat = fake_chat
            session, store, _ = _make_session_and_agent(agent=agent)

            mock_msg = MagicMock()
            mock_msg.content = "hi"
            mock_msg.elements = []

            sent_messages = []
            mock_cl_msg = MagicMock()
            mock_cl_msg.send = AsyncMock()
            mock_cl_msg.update = AsyncMock()
            mock_cl_msg.stream_token = AsyncMock()

            import chainlit as cl

            def capture_message(**kwargs):
                sent_messages.append(kwargs)
                return mock_cl_msg

            with (
                patch.object(cl, "user_session", session),
                patch.object(cl, "Message", side_effect=capture_message),
            ):
                await on_message(mock_msg)

            # First Message is created by on_token with empty content
            assert sent_messages[0]["content"] == ""
            # stream_token should have been called twice
            assert mock_cl_msg.stream_token.call_count == 2
            stream_calls = [c[0][0] for c in mock_cl_msg.stream_token.call_args_list]
            assert stream_calls == ["Hello ", "world"]

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# Conversation starters tests
# ---------------------------------------------------------------------------


class TestSetStarters:
    def test_returns_four_starters(self):
        """set_starters returns a list of Starter objects."""

        async def _run():
            from optopsy.ui.app import set_starters

            result = await set_starters()
            assert len(result) == 4

        asyncio.run(_run())

    def test_starters_have_required_fields(self):
        """Each starter has label and message fields."""

        async def _run():
            from optopsy.ui.app import set_starters

            result = await set_starters()
            for starter in result:
                assert starter.label
                assert starter.message

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# Chat settings tests
# ---------------------------------------------------------------------------


class TestOnSettingsUpdate:
    def test_stores_settings_in_session(self):
        """on_settings_update persists settings dict to user_session."""

        async def _run():
            from optopsy.ui.app import on_settings_update

            store: dict = {}
            session = MagicMock()
            session.get = lambda key: store.get(key)
            session.set = lambda key, val: store.__setitem__(key, val)

            import chainlit as cl

            with patch.object(cl, "user_session", session):
                await on_settings_update({"max_entry_dte": 60, "raw_mode": True})

            assert store["chat_settings"] == {
                "max_entry_dte": 60,
                "raw_mode": True,
            }

        asyncio.run(_run())


class TestBuildSettingsContext:
    def test_empty_settings_returns_empty(self):
        """Default settings produce no context string."""
        from optopsy.ui.app import _build_settings_context

        assert _build_settings_context({}) == ""

    def test_default_values_produce_empty(self):
        """Settings matching defaults produce no context string."""
        from optopsy.ui.app import _build_settings_context

        result = _build_settings_context(
            {
                "max_entry_dte": 90,
                "max_otm_pct": 0.5,
                "raw_mode": False,
                "slippage": "mid",
            }
        )
        assert result == ""

    def test_non_default_dte(self):
        """Changed DTE produces a settings context."""
        from optopsy.ui.app import _build_settings_context

        result = _build_settings_context({"max_entry_dte": 45})
        assert "[User settings:" in result
        assert "max_entry_dte=45" in result

    def test_non_default_raw_mode(self):
        """Toggled raw mode produces raw=true in context."""
        from optopsy.ui.app import _build_settings_context

        result = _build_settings_context({"raw_mode": True})
        assert "raw=true" in result

    def test_non_default_otm_pct(self):
        """Changed OTM % is formatted with 2 decimal places."""
        from optopsy.ui.app import _build_settings_context

        result = _build_settings_context({"max_otm_pct": 0.2})
        assert "max_otm_pct=0.20" in result

    def test_non_default_slippage(self):
        """Changed slippage model appears in context."""
        from optopsy.ui.app import _build_settings_context

        result = _build_settings_context({"slippage": "spread"})
        assert "slippage=spread" in result

    def test_multiple_non_defaults(self):
        """Multiple changed settings all appear."""
        from optopsy.ui.app import _build_settings_context

        result = _build_settings_context({"max_entry_dte": 30, "raw_mode": True})
        assert "max_entry_dte=30" in result
        assert "raw=true" in result


# ---------------------------------------------------------------------------
# Action buttons tests
# ---------------------------------------------------------------------------


class TestBuildStrategyActions:
    def test_empty_info_returns_no_actions(self):
        """No strategy info means no actions."""
        from optopsy.ui.app import _build_strategy_actions

        assert _build_strategy_actions({}) == []

    def test_non_raw_strategy_produces_raw_toggle(self):
        """Non-raw strategy produces 'Show Raw Trades' action."""
        from optopsy.ui.app import _build_strategy_actions

        actions = _build_strategy_actions(
            {
                "strategy_name": "long_calls",
                "arguments": {"strategy_name": "long_calls"},
            }
        )
        labels = [a.label for a in actions]
        assert "Show Raw Trades" in labels

    def test_raw_strategy_produces_aggregated_toggle(self):
        """Raw strategy produces 'Show Aggregated Stats' action."""
        from optopsy.ui.app import _build_strategy_actions

        actions = _build_strategy_actions(
            {
                "strategy_name": "long_calls",
                "arguments": {"strategy_name": "long_calls", "raw": True},
            }
        )
        labels = [a.label for a in actions]
        assert "Show Aggregated Stats" in labels

    def test_wider_dte_action(self):
        """Action to try wider DTE is created when DTE < 365."""
        from optopsy.ui.app import _build_strategy_actions

        actions = _build_strategy_actions(
            {
                "strategy_name": "short_puts",
                "arguments": {"strategy_name": "short_puts", "max_entry_dte": 60},
            }
        )
        labels = [a.label for a in actions]
        assert "Try DTE 90" in labels

    def test_no_wider_dte_at_max(self):
        """No wider DTE action when already at 365."""
        from optopsy.ui.app import _build_strategy_actions

        actions = _build_strategy_actions(
            {
                "strategy_name": "long_calls",
                "arguments": {"strategy_name": "long_calls", "max_entry_dte": 365},
            }
        )
        labels = [a.label for a in actions]
        assert not any("Try DTE" in lbl for lbl in labels)

    def test_chart_action_always_present(self):
        """Chart Results action is always present."""
        from optopsy.ui.app import _build_strategy_actions

        actions = _build_strategy_actions(
            {
                "strategy_name": "long_calls",
                "arguments": {"strategy_name": "long_calls"},
            }
        )
        labels = [a.label for a in actions]
        assert "Chart Results" in labels


# ---------------------------------------------------------------------------
# Attach result elements tests
# ---------------------------------------------------------------------------


class TestAttachResultElements:
    def test_attaches_dataframe_and_csv(self):
        """Attaching results adds Dataframe and File elements."""
        from optopsy.ui.app import _attach_result_elements

        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        result = MagicMock()
        result._result_df = df

        elements: list = []

        import chainlit as cl

        mock_df_element = MagicMock()
        mock_file_element = MagicMock()

        with (
            patch.object(cl, "Dataframe", return_value=mock_df_element) as mock_df_cls,
            patch.object(cl, "File", return_value=mock_file_element) as mock_file_cls,
        ):
            _attach_result_elements(result, "run_strategy", elements)

        assert len(elements) == 2
        assert elements[0] is mock_df_element
        assert elements[1] is mock_file_element
        # Verify Dataframe was created with correct args
        mock_df_cls.assert_called_once()
        call_kwargs = mock_df_cls.call_args[1]
        assert call_kwargs["name"] == "Run Strategy Results"
        assert call_kwargs["display"] == "inline"
        # Verify File was created with CSV content
        mock_file_cls.assert_called_once()
        file_kwargs = mock_file_cls.call_args[1]
        assert file_kwargs["name"] == "run_strategy_results.csv"
        assert file_kwargs["mime"] == "text/csv"

    def test_empty_df_skips(self):
        """Empty DataFrame produces no elements."""
        from optopsy.ui.app import _attach_result_elements

        result = MagicMock()
        result._result_df = pd.DataFrame()

        elements: list = []
        _attach_result_elements(result, "run_strategy", elements)
        assert len(elements) == 0

    def test_none_df_skips(self):
        """None DataFrame produces no elements."""
        from optopsy.ui.app import _attach_result_elements

        result = MagicMock()
        result._result_df = None

        elements: list = []
        _attach_result_elements(result, "run_strategy", elements)
        assert len(elements) == 0


# ---------------------------------------------------------------------------
# Action callback tests
# ---------------------------------------------------------------------------


class TestActionCallbacks:
    def test_rerun_strategy_raw_toggle(self):
        """rerun_strategy callback sends correct prompt for raw toggle."""

        async def _run():
            from optopsy.ui.app import on_rerun_strategy

            mock_action = MagicMock()
            mock_action.payload = {"strategy": "long_calls", "toggle": "raw"}

            import chainlit as cl

            sent_contents = []
            mock_cl_msg = MagicMock()
            mock_cl_msg.send = AsyncMock()
            mock_cl_msg.update = AsyncMock()
            mock_cl_msg.stream_token = AsyncMock()

            agent = MagicMock()
            agent.datasets = {}
            agent.chat = AsyncMock(return_value=("ok", []))

            store = {"agent": agent, "messages": [], "chat_settings": None}
            session = MagicMock()
            session.get = lambda key: store.get(key)
            session.set = lambda key, val: store.__setitem__(key, val)

            def capture_message(**kwargs):
                sent_contents.append(kwargs.get("content", ""))
                return mock_cl_msg

            with (
                patch.object(cl, "user_session", session),
                patch.object(cl, "Message", side_effect=capture_message),
            ):
                await on_rerun_strategy(mock_action)

            assert any("raw=true" in c for c in sent_contents)

        asyncio.run(_run())

    def test_rerun_strategy_aggregated_toggle(self):
        """rerun_strategy callback sends correct prompt for aggregated toggle."""

        async def _run():
            from optopsy.ui.app import on_rerun_strategy

            mock_action = MagicMock()
            mock_action.payload = {
                "strategy": "long_puts",
                "toggle": "aggregated",
            }

            import chainlit as cl

            sent_contents = []
            mock_cl_msg = MagicMock()
            mock_cl_msg.send = AsyncMock()
            mock_cl_msg.update = AsyncMock()
            mock_cl_msg.stream_token = AsyncMock()

            agent = MagicMock()
            agent.datasets = {}
            agent.chat = AsyncMock(return_value=("ok", []))

            store = {"agent": agent, "messages": [], "chat_settings": None}
            session = MagicMock()
            session.get = lambda key: store.get(key)
            session.set = lambda key, val: store.__setitem__(key, val)

            def capture_message(**kwargs):
                sent_contents.append(kwargs.get("content", ""))
                return mock_cl_msg

            with (
                patch.object(cl, "user_session", session),
                patch.object(cl, "Message", side_effect=capture_message),
            ):
                await on_rerun_strategy(mock_action)

            assert any("raw=false" in c for c in sent_contents)

        asyncio.run(_run())

    def test_rerun_strategy_wider_dte(self):
        """rerun_strategy callback sends correct prompt for wider DTE."""

        async def _run():
            from optopsy.ui.app import on_rerun_strategy

            mock_action = MagicMock()
            mock_action.payload = {
                "strategy": "iron_condor",
                "adjust": "wider_dte",
                "dte": 120,
            }

            import chainlit as cl

            sent_contents = []
            mock_cl_msg = MagicMock()
            mock_cl_msg.send = AsyncMock()
            mock_cl_msg.update = AsyncMock()
            mock_cl_msg.stream_token = AsyncMock()

            agent = MagicMock()
            agent.datasets = {}
            agent.chat = AsyncMock(return_value=("ok", []))

            store = {"agent": agent, "messages": [], "chat_settings": None}
            session = MagicMock()
            session.get = lambda key: store.get(key)
            session.set = lambda key, val: store.__setitem__(key, val)

            def capture_message(**kwargs):
                sent_contents.append(kwargs.get("content", ""))
                return mock_cl_msg

            with (
                patch.object(cl, "user_session", session),
                patch.object(cl, "Message", side_effect=capture_message),
            ):
                await on_rerun_strategy(mock_action)

            assert any("max_entry_dte=120" in c for c in sent_contents)

        asyncio.run(_run())

    def test_rerun_strategy_generic(self):
        """rerun_strategy with no toggle or adjust produces generic prompt."""

        async def _run():
            from optopsy.ui.app import on_rerun_strategy

            mock_action = MagicMock()
            mock_action.payload = {"strategy": "short_puts"}

            import chainlit as cl

            sent_contents = []
            mock_cl_msg = MagicMock()
            mock_cl_msg.send = AsyncMock()
            mock_cl_msg.update = AsyncMock()
            mock_cl_msg.stream_token = AsyncMock()

            agent = MagicMock()
            agent.datasets = {}
            agent.chat = AsyncMock(return_value=("ok", []))

            store = {"agent": agent, "messages": [], "chat_settings": None}
            session = MagicMock()
            session.get = lambda key: store.get(key)
            session.set = lambda key, val: store.__setitem__(key, val)

            def capture_message(**kwargs):
                sent_contents.append(kwargs.get("content", ""))
                return mock_cl_msg

            with (
                patch.object(cl, "user_session", session),
                patch.object(cl, "Message", side_effect=capture_message),
            ):
                await on_rerun_strategy(mock_action)

            assert any("Re-run short_puts" in c for c in sent_contents)

        asyncio.run(_run())

    def test_create_chart_action(self):
        """create_chart_action callback sends chart prompt."""

        async def _run():
            from optopsy.ui.app import on_create_chart

            mock_action = MagicMock()
            mock_action.payload = {"strategy": "iron_butterfly"}

            import chainlit as cl

            sent_contents = []
            mock_cl_msg = MagicMock()
            mock_cl_msg.send = AsyncMock()
            mock_cl_msg.update = AsyncMock()
            mock_cl_msg.stream_token = AsyncMock()

            agent = MagicMock()
            agent.datasets = {}
            agent.chat = AsyncMock(return_value=("ok", []))

            store = {"agent": agent, "messages": [], "chat_settings": None}
            session = MagicMock()
            session.get = lambda key: store.get(key)
            session.set = lambda key, val: store.__setitem__(key, val)

            def capture_message(**kwargs):
                sent_contents.append(kwargs.get("content", ""))
                return mock_cl_msg

            with (
                patch.object(cl, "user_session", session),
                patch.object(cl, "Message", side_effect=capture_message),
            ):
                await on_create_chart(mock_action)

            assert any("iron_butterfly" in c for c in sent_contents)
            assert any("chart" in c.lower() for c in sent_contents)

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# Settings context injection in on_message
# ---------------------------------------------------------------------------


class TestSettingsContextInjection:
    def test_settings_injected_into_message(self):
        """Non-default chat settings are appended to the user message."""

        async def _run():
            from optopsy.ui.app import on_message

            agent = MagicMock()
            agent.datasets = {}
            agent.chat = AsyncMock(
                return_value=("ok", [{"role": "assistant", "content": "ok"}])
            )

            store = {
                "agent": agent,
                "messages": [],
                "chat_settings": {"max_entry_dte": 30, "raw_mode": True},
            }
            session = MagicMock()
            session.get = lambda key: store.get(key)
            session.set = lambda key, val: store.__setitem__(key, val)

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

            # Check that agent.chat was called with messages containing settings
            call_args = agent.chat.call_args
            messages_arg = call_args[0][0]
            user_msg = next(m for m in messages_arg if m["role"] == "user")
            assert "[User settings:" in user_msg["content"]
            assert "max_entry_dte=30" in user_msg["content"]
            assert "raw=true" in user_msg["content"]

        asyncio.run(_run())

    def test_default_settings_not_injected(self):
        """Default settings produce no settings context injection."""

        async def _run():
            from optopsy.ui.app import on_message

            agent = MagicMock()
            agent.datasets = {}
            agent.chat = AsyncMock(
                return_value=("ok", [{"role": "assistant", "content": "ok"}])
            )

            store = {
                "agent": agent,
                "messages": [],
                "chat_settings": {
                    "max_entry_dte": 90,
                    "max_otm_pct": 0.5,
                    "raw_mode": False,
                    "slippage": "mid",
                },
            }
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

            with (
                patch.object(cl, "user_session", session),
                patch.object(cl, "Message", return_value=mock_cl_msg),
            ):
                await on_message(mock_msg)

            call_args = agent.chat.call_args
            messages_arg = call_args[0][0]
            user_msg = next(m for m in messages_arg if m["role"] == "user")
            assert "[User settings:" not in user_msg["content"]
            assert user_msg["content"] == "hello"

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# on_chat_start initializes settings
# ---------------------------------------------------------------------------


class TestOnChatStartSettings:
    def test_chat_settings_sent(self):
        """on_chat_start creates and sends ChatSettings."""

        async def _run():
            from optopsy.ui.app import on_chat_start

            store: dict = {}
            session = MagicMock()
            session.get = lambda key: store.get(key)
            session.set = lambda key, val: store.__setitem__(key, val)

            mock_cl_msg = MagicMock()
            mock_cl_msg.send = AsyncMock()

            mock_settings = MagicMock()
            mock_settings.send = AsyncMock()

            import chainlit as cl

            captured_settings_args = []

            def capture_settings(inputs):
                captured_settings_args.append(inputs)
                return mock_settings

            with (
                patch.object(cl, "user_session", session),
                patch.object(cl, "Message", return_value=mock_cl_msg),
                patch.object(cl, "ChatSettings", side_effect=capture_settings),
                patch("optopsy.ui.app.get_provider_names", return_value=[]),
            ):
                await on_chat_start()

            # ChatSettings was created with 4 input widgets
            assert len(captured_settings_args) == 1
            assert len(captured_settings_args[0]) == 4
            # settings.send() was called
            mock_settings.send.assert_called_once()

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# ToolResult._result_df tests
# ---------------------------------------------------------------------------


class TestToolResultResultDf:
    def test_result_df_default_none(self):
        """ToolResult._result_df defaults to None."""
        from optopsy.ui.tools._helpers import ToolResult

        tr = ToolResult("summary", None)
        assert tr._result_df is None

    def test_result_df_set_via_constructor(self):
        """ToolResult._result_df can be set via constructor."""
        from optopsy.ui.tools._helpers import ToolResult

        df = pd.DataFrame({"x": [1, 2, 3]})
        tr = ToolResult("summary", None, result_df=df)
        assert tr._result_df is df
        assert len(tr._result_df) == 3
