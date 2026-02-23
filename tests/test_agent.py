"""Tests for optopsy.ui.agent — _compact_history and OptopsyAgent.chat()."""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("pyarrow", reason="UI extras not installed")

from optopsy.ui.agent import (
    _COMPACT_THRESHOLD,
    OptopsyAgent,
    _compact_history,
    _sanitize_tool_messages,
)

# ---------------------------------------------------------------------------
# _sanitize_tool_messages tests
# ---------------------------------------------------------------------------


class TestSanitizeToolMessages:
    def test_removes_orphaned_tool_messages(self):
        """Tool messages without matching tool_calls are removed."""
        messages = [
            {"role": "user", "content": "load data"},
            {"role": "assistant", "content": "Loading..."},  # no tool_calls
            {"role": "tool", "tool_call_id": "orphan1", "content": "result1"},
            {"role": "tool", "tool_call_id": "orphan2", "content": "result2"},
            {"role": "assistant", "content": "Done."},
        ]
        result = _sanitize_tool_messages(messages)
        assert len(result) == 3
        assert not any(m.get("role") == "tool" for m in result)

    def test_keeps_valid_tool_messages(self):
        """Tool messages with matching tool_calls are preserved."""
        messages = [
            {"role": "user", "content": "run strategy"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"id": "tc1", "function": {"name": "run_strategy"}},
                    {"id": "tc2", "function": {"name": "preview_data"}},
                ],
            },
            {"role": "tool", "tool_call_id": "tc1", "content": "result1"},
            {"role": "tool", "tool_call_id": "tc2", "content": "result2"},
            {"role": "assistant", "content": "Here are results."},
        ]
        result = _sanitize_tool_messages(messages)
        assert len(result) == 5  # nothing removed

    def test_mixed_orphaned_and_valid(self):
        """Only orphaned tool messages are removed; valid ones stay."""
        messages = [
            {"role": "user", "content": "load data"},
            {"role": "assistant", "content": "Fetching..."},  # no tool_calls
            {"role": "tool", "tool_call_id": "orphan", "content": "cached"},
            {"role": "assistant", "content": "Now running..."},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"id": "tc_valid", "function": {"name": "run"}}],
            },
            {"role": "tool", "tool_call_id": "tc_valid", "content": "stats"},
            {"role": "assistant", "content": "Results."},
        ]
        result = _sanitize_tool_messages(messages)
        tool_msgs = [m for m in result if m.get("role") == "tool"]
        assert len(tool_msgs) == 1
        assert tool_msgs[0]["tool_call_id"] == "tc_valid"

    def test_empty_messages(self):
        assert _sanitize_tool_messages([]) == []

    def test_no_tool_messages(self):
        messages = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        assert _sanitize_tool_messages(messages) == messages


# ---------------------------------------------------------------------------
# _compact_history tests
# ---------------------------------------------------------------------------


class TestCompactHistory:
    def test_empty_list(self):
        msgs: list[dict[str, Any]] = []
        _compact_history(msgs)
        assert msgs == []

    def test_single_user_message(self):
        msgs = [{"role": "user", "content": "hello"}]
        _compact_history(msgs)
        assert msgs == [{"role": "user", "content": "hello"}]

    def test_single_assistant_with_tool_calls(self):
        """Only one assistant-with-tool_calls — nothing old to truncate."""
        msgs = [
            {"role": "user", "content": "run"},
            {"role": "assistant", "content": "thinking", "tool_calls": [{"id": "1"}]},
            {"role": "tool", "tool_call_id": "1", "content": "x" * 500},
        ]
        _compact_history(msgs)
        assert len(msgs[2]["content"]) == 500

    def test_old_tool_results_truncated(self):
        long_content = "first line\n" + "x" * 500
        msgs = [
            {"role": "user", "content": "go"},
            {"role": "assistant", "content": "ok", "tool_calls": [{"id": "t1"}]},
            {"role": "tool", "tool_call_id": "t1", "content": long_content},
            {"role": "assistant", "content": "next", "tool_calls": [{"id": "t2"}]},
            {"role": "tool", "tool_call_id": "t2", "content": "recent result"},
        ]
        _compact_history(msgs)
        assert msgs[2]["content"] == "first line [truncated]"
        assert msgs[4]["content"] == "recent result"

    def test_old_assistant_reasoning_truncated(self):
        long_reasoning = "A" * 500
        msgs = [
            {"role": "user", "content": "go"},
            {
                "role": "assistant",
                "content": long_reasoning,
                "tool_calls": [{"id": "t1"}],
            },
            {"role": "tool", "tool_call_id": "t1", "content": "short"},
            {
                "role": "assistant",
                "content": "final reasoning",
                "tool_calls": [{"id": "t2"}],
            },
            {"role": "tool", "tool_call_id": "t2", "content": "result"},
        ]
        _compact_history(msgs)
        assert msgs[1]["content"].endswith("… [truncated]")
        assert len(msgs[1]["content"]) <= _COMPACT_THRESHOLD + 20
        assert msgs[3]["content"] == "final reasoning"

    def test_short_content_not_truncated(self):
        msgs = [
            {"role": "user", "content": "go"},
            {"role": "assistant", "content": "ok", "tool_calls": [{"id": "t1"}]},
            {"role": "tool", "tool_call_id": "t1", "content": "short"},
            {"role": "assistant", "content": "done", "tool_calls": [{"id": "t2"}]},
            {"role": "tool", "tool_call_id": "t2", "content": "also short"},
        ]
        _compact_history(msgs)
        assert msgs[2]["content"] == "short"

    def test_last_batch_kept_intact(self):
        msgs = [
            {"role": "user", "content": "go"},
            {"role": "assistant", "content": "a", "tool_calls": [{"id": "t1"}]},
            {"role": "tool", "tool_call_id": "t1", "content": "y" * 500},
            {
                "role": "assistant",
                "content": "b",
                "tool_calls": [{"id": "t2"}, {"id": "t3"}],
            },
            {"role": "tool", "tool_call_id": "t2", "content": "z" * 500},
            {"role": "tool", "tool_call_id": "t3", "content": "w" * 500},
        ]
        _compact_history(msgs)
        assert msgs[2]["content"].endswith("[truncated]")
        assert len(msgs[4]["content"]) == 500
        assert len(msgs[5]["content"]) == 500


# ---------------------------------------------------------------------------
# OptopsyAgent.chat() tests
# ---------------------------------------------------------------------------


def _make_delta(content=None, tool_calls=None):
    delta = MagicMock()
    delta.content = content
    delta.tool_calls = tool_calls
    return delta


def _make_chunk(delta):
    chunk = MagicMock()
    choice = MagicMock()
    choice.delta = delta
    chunk.choices = [choice]
    return chunk


async def _async_iter(items):
    for item in items:
        yield item


class TestAgentChat:
    def test_single_turn_no_tools(self):
        """LLM responds with text only — no tool calls."""

        async def _run():
            chunks = [
                _make_chunk(_make_delta(content="Hello ")),
                _make_chunk(_make_delta(content="world")),
            ]
            agent = OptopsyAgent(model="test/model")
            agent.tools = []

            tokens_received = []

            async def on_token(t):
                tokens_received.append(t)

            with patch("litellm.acompletion", new_callable=AsyncMock) as mock_llm:
                mock_llm.return_value = _async_iter(chunks)
                content, msgs = await agent.chat(
                    [{"role": "user", "content": "hi"}],
                    on_token=on_token,
                )

            assert content == "Hello world"
            assert tokens_received == ["Hello ", "world"]
            # Returned messages should not include the system message
            assert msgs[0]["role"] == "user"
            assert any(
                m["role"] == "assistant" and m["content"] == "Hello world" for m in msgs
            )

        asyncio.run(_run())

    def test_tool_call_loop(self):
        """LLM calls a tool, then responds with text."""

        async def _run():
            tc_chunk_1 = MagicMock()
            tc_chunk_1.index = 0
            tc_chunk_1.id = "call_1"
            tc_chunk_1.function = MagicMock()
            tc_chunk_1.function.name = "preview_data"
            tc_chunk_1.function.arguments = '{"rows": 5}'

            tool_call_delta = _make_delta(tool_calls=[tc_chunk_1])
            tool_call_chunk = _make_chunk(tool_call_delta)

            text_chunks = [
                _make_chunk(_make_delta(content="Here are the results.")),
            ]

            call_count = 0

            async def mock_acompletion(**kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return _async_iter([tool_call_chunk])
                return _async_iter(text_chunks)

            agent = OptopsyAgent(model="test/model")
            agent.tools = [{"type": "function", "function": {"name": "preview_data"}}]

            tool_calls_seen = []
            tool_args_seen = []

            async def on_tool_call(name, args, result, tc_id):
                tool_calls_seen.append(name)
                tool_args_seen.append(args)

            with (
                patch("litellm.acompletion", side_effect=mock_acompletion),
                patch("optopsy.ui.agent.execute_tool") as mock_exec,
                patch("asyncio.sleep", new_callable=AsyncMock),
            ):
                mock_result = MagicMock()
                mock_result.dataset = None
                mock_result.signals = None
                mock_result.datasets = None
                mock_result.results = None
                mock_result.llm_summary = "preview ok"
                mock_exec.return_value = mock_result

                content, msgs = await agent.chat(
                    [{"role": "user", "content": "show data"}],
                    on_tool_call=on_tool_call,
                )

            assert content == "Here are the results."
            assert tool_calls_seen == ["preview_data"]
            # Verify execute_tool was called with parsed JSON args
            mock_exec.assert_called_once()
            actual_args = mock_exec.call_args[0][1]
            assert actual_args == {"rows": 5}
            # Verify tool result message was added to history
            assert any(m.get("role") == "tool" for m in msgs)

        asyncio.run(_run())

    def test_malformed_tool_arguments_fallback_to_empty(self):
        """When LLM sends invalid JSON arguments, they fall back to {}."""

        async def _run():
            tc_chunk = MagicMock()
            tc_chunk.index = 0
            tc_chunk.id = "call_bad"
            tc_chunk.function = MagicMock()
            tc_chunk.function.name = "preview_data"
            tc_chunk.function.arguments = "not valid json {"

            tool_call_delta = _make_delta(tool_calls=[tc_chunk])
            text_delta = _make_delta(content="Done")
            call_count = 0

            async def mock_acompletion(**kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return _async_iter([_make_chunk(tool_call_delta)])
                return _async_iter([_make_chunk(text_delta)])

            agent = OptopsyAgent(model="test/model")
            agent.tools = [{"type": "function", "function": {"name": "preview_data"}}]

            with (
                patch("litellm.acompletion", side_effect=mock_acompletion),
                patch("optopsy.ui.agent.execute_tool") as mock_exec,
                patch("asyncio.sleep", new_callable=AsyncMock),
            ):
                mock_result = MagicMock()
                mock_result.dataset = None
                mock_result.signals = None
                mock_result.datasets = None
                mock_result.results = None
                mock_result.llm_summary = "ok"
                mock_exec.return_value = mock_result

                await agent.chat([{"role": "user", "content": "go"}])

            # Should have been called with empty dict due to JSON parse failure
            actual_args = mock_exec.call_args[0][1]
            assert actual_args == {}

        asyncio.run(_run())

    def test_authentication_error(self):
        """AuthenticationError raises RuntimeError with API key message."""

        async def _run():
            import litellm

            agent = OptopsyAgent(model="test/model")
            agent.tools = []

            with patch("litellm.acompletion", new_callable=AsyncMock) as mock_llm:
                mock_llm.side_effect = litellm.AuthenticationError(
                    message="invalid key",
                    llm_provider="test",
                    model="test/model",
                )
                with pytest.raises(RuntimeError, match="No API key configured"):
                    await agent.chat([{"role": "user", "content": "hi"}])

        asyncio.run(_run())

    def test_rate_limit_retries_then_fails(self):
        """RateLimitError retries up to 3 times then raises RuntimeError."""

        async def _run():
            import litellm

            agent = OptopsyAgent(model="test/model")
            agent.tools = []

            with (
                patch("litellm.acompletion", new_callable=AsyncMock) as mock_llm,
                patch("asyncio.sleep", new_callable=AsyncMock),
            ):
                mock_llm.side_effect = litellm.RateLimitError(
                    message="rate limited",
                    llm_provider="test",
                    model="test/model",
                )
                with pytest.raises(RuntimeError, match="rate limit exceeded"):
                    await agent.chat([{"role": "user", "content": "hi"}])
                assert mock_llm.call_count == 3

        asyncio.run(_run())

    def test_service_unavailable_retries_then_fails(self):
        """ServiceUnavailableError retries up to 3 times then raises RuntimeError."""

        async def _run():
            import litellm

            agent = OptopsyAgent(model="test/model")
            agent.tools = []

            with (
                patch("litellm.acompletion", new_callable=AsyncMock) as mock_llm,
                patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            ):
                mock_llm.side_effect = litellm.ServiceUnavailableError(
                    message="service down",
                    llm_provider="test",
                    model="test/model",
                )
                with pytest.raises(RuntimeError, match="temporarily unavailable"):
                    await agent.chat([{"role": "user", "content": "hi"}])
                assert mock_llm.call_count == 3
                # Verify exponential backoff: sleep(1), sleep(2)
                assert mock_sleep.call_count == 2

        asyncio.run(_run())

    def test_iteration_cap(self):
        """Exceeding _MAX_TOOL_ITERATIONS raises RuntimeError."""

        async def _run():
            tc_chunk = MagicMock()
            tc_chunk.index = 0
            tc_chunk.id = "call_x"
            tc_chunk.function = MagicMock()
            tc_chunk.function.name = "preview_data"
            tc_chunk.function.arguments = "{}"

            tool_call_delta = _make_delta(tool_calls=[tc_chunk])
            tool_call_chunk = _make_chunk(tool_call_delta)

            agent = OptopsyAgent(model="test/model")
            agent.tools = [{"type": "function", "function": {"name": "preview_data"}}]

            async def mock_acompletion(**kwargs):
                return _async_iter([tool_call_chunk])

            with (
                patch("litellm.acompletion", side_effect=mock_acompletion),
                patch("optopsy.ui.agent.execute_tool") as mock_exec,
                patch("asyncio.sleep", new_callable=AsyncMock),
            ):
                mock_result = MagicMock()
                mock_result.dataset = None
                mock_result.signals = None
                mock_result.datasets = None
                mock_result.results = None
                mock_result.llm_summary = "ok"
                mock_exec.return_value = mock_result

                with pytest.raises(RuntimeError, match="exceeded"):
                    await agent.chat([{"role": "user", "content": "loop forever"}])

        asyncio.run(_run())

    def test_state_updates_from_tool_result(self):
        """Tool results update agent.dataset, signals, datasets, results."""

        async def _run():
            import pandas as pd

            tc_chunk = MagicMock()
            tc_chunk.index = 0
            tc_chunk.id = "call_1"
            tc_chunk.function = MagicMock()
            tc_chunk.function.name = "load_data"
            tc_chunk.function.arguments = "{}"

            tool_call_delta = _make_delta(tool_calls=[tc_chunk])
            text_delta = _make_delta(content="Done")
            call_count = 0

            async def mock_acompletion(**kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return _async_iter([_make_chunk(tool_call_delta)])
                return _async_iter([_make_chunk(text_delta)])

            agent = OptopsyAgent(model="test/model")
            agent.tools = [{"type": "function", "function": {"name": "load_data"}}]

            fake_df = pd.DataFrame({"a": [1]})
            fake_signals = {"entry": pd.DataFrame()}
            fake_datasets = {"SPY": fake_df}
            fake_results = {"run1": {"mean_return": 0.05}}

            with (
                patch("litellm.acompletion", side_effect=mock_acompletion),
                patch("optopsy.ui.agent.execute_tool") as mock_exec,
                patch("asyncio.sleep", new_callable=AsyncMock),
            ):
                mock_result = MagicMock()
                mock_result.dataset = fake_df
                mock_result.signals = fake_signals
                mock_result.datasets = fake_datasets
                mock_result.results = fake_results
                mock_result.llm_summary = "loaded"
                mock_exec.return_value = mock_result

                await agent.chat([{"role": "user", "content": "load"}])

            assert agent.dataset is fake_df
            assert agent.signals is fake_signals
            assert agent.datasets is fake_datasets
            assert agent.results is fake_results

        asyncio.run(_run())

    def test_rate_limit_retry_succeeds_on_second_attempt(self):
        """RateLimitError on first attempt, success on second."""

        async def _run():
            import litellm

            agent = OptopsyAgent(model="test/model")
            agent.tools = []

            text_chunks = [_make_chunk(_make_delta(content="ok"))]
            call_count = 0

            async def mock_acompletion(**kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise litellm.RateLimitError(
                        message="rate limited",
                        llm_provider="test",
                        model="test/model",
                    )
                return _async_iter(text_chunks)

            with (
                patch("litellm.acompletion", side_effect=mock_acompletion),
                patch("asyncio.sleep", new_callable=AsyncMock),
            ):
                content, msgs = await agent.chat(
                    [{"role": "user", "content": "hi"}],
                )

            assert content == "ok"
            assert call_count == 2

        asyncio.run(_run())

    def test_on_assistant_tool_calls_callback_fired(self):
        """on_assistant_tool_calls callback is called with tool_calls list."""

        async def _run():
            tc_chunk = MagicMock()
            tc_chunk.index = 0
            tc_chunk.id = "call_1"
            tc_chunk.function = MagicMock()
            tc_chunk.function.name = "preview_data"
            tc_chunk.function.arguments = "{}"

            tool_call_delta = _make_delta(tool_calls=[tc_chunk])
            text_delta = _make_delta(content="Done")
            call_count = 0

            async def mock_acompletion(**kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return _async_iter([_make_chunk(tool_call_delta)])
                return _async_iter([_make_chunk(text_delta)])

            agent = OptopsyAgent(model="test/model")
            agent.tools = [{"type": "function", "function": {"name": "preview_data"}}]

            assistant_tc_calls = []

            async def on_assistant_tool_calls(tool_calls):
                assistant_tc_calls.append(tool_calls)

            with (
                patch("litellm.acompletion", side_effect=mock_acompletion),
                patch("optopsy.ui.agent.execute_tool") as mock_exec,
                patch("asyncio.sleep", new_callable=AsyncMock),
            ):
                mock_result = MagicMock()
                mock_result.dataset = None
                mock_result.signals = None
                mock_result.datasets = None
                mock_result.results = None
                mock_result.llm_summary = "ok"
                mock_exec.return_value = mock_result

                await agent.chat(
                    [{"role": "user", "content": "go"}],
                    on_assistant_tool_calls=on_assistant_tool_calls,
                )

            assert len(assistant_tc_calls) == 1
            # The callback should receive a list of tool call dicts
            tc_list = assistant_tc_calls[0]
            assert len(tc_list) == 1
            assert tc_list[0]["id"] == "call_1"
            assert tc_list[0]["function"]["name"] == "preview_data"

        asyncio.run(_run())

    def test_system_prompt_includes_results_memo_for_anthropic(self):
        """Anthropic model gets results memo appended to system prompt."""

        async def _run():
            agent = OptopsyAgent(model="anthropic/claude-test")
            agent.tools = []
            agent.results = {
                "run1": {
                    "strategy": "long_calls",
                    "max_entry_dte": 30,
                    "exit_dte": 0,
                    "max_otm_pct": 0.05,
                    "mean_return": 0.10,
                    "win_rate": 0.65,
                },
            }

            chunks = [_make_chunk(_make_delta(content="ok"))]

            with patch("litellm.acompletion", new_callable=AsyncMock) as mock_llm:
                mock_llm.return_value = _async_iter(chunks)
                await agent.chat([{"role": "user", "content": "compare"}])

            # Inspect the system message passed to litellm
            call_kwargs = mock_llm.call_args[1]
            system_msg = call_kwargs["messages"][0]
            assert system_msg["role"] == "system"
            # Anthropic model uses content-block form with cache_control
            assert isinstance(system_msg["content"], list)
            # Should have 2 content blocks: prompt + results memo
            assert len(system_msg["content"]) == 2
            memo_text = system_msg["content"][1]["text"]
            assert "long_calls" in memo_text
            assert "mean=" in memo_text

        asyncio.run(_run())

    def test_multiple_tool_calls_in_single_turn(self):
        """LLM emits two tool calls in one turn; both are executed."""

        async def _run():
            tc1 = MagicMock()
            tc1.index = 0
            tc1.id = "call_a"
            tc1.function = MagicMock()
            tc1.function.name = "preview_data"
            tc1.function.arguments = "{}"

            tc2 = MagicMock()
            tc2.index = 1
            tc2.id = "call_b"
            tc2.function = MagicMock()
            tc2.function.name = "list_results"
            tc2.function.arguments = "{}"

            tool_call_delta = _make_delta(tool_calls=[tc1, tc2])
            text_delta = _make_delta(content="Done")
            call_count = 0

            async def mock_acompletion(**kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return _async_iter([_make_chunk(tool_call_delta)])
                return _async_iter([_make_chunk(text_delta)])

            agent = OptopsyAgent(model="test/model")
            agent.tools = [
                {"type": "function", "function": {"name": "preview_data"}},
                {"type": "function", "function": {"name": "list_results"}},
            ]

            with (
                patch("litellm.acompletion", side_effect=mock_acompletion),
                patch("optopsy.ui.agent.execute_tool") as mock_exec,
                patch("asyncio.sleep", new_callable=AsyncMock),
            ):
                mock_result = MagicMock()
                mock_result.dataset = None
                mock_result.signals = None
                mock_result.datasets = None
                mock_result.results = None
                mock_result.llm_summary = "ok"
                mock_exec.return_value = mock_result

                content, msgs = await agent.chat(
                    [{"role": "user", "content": "show everything"}],
                )

            assert content == "Done"
            assert mock_exec.call_count == 2
            called_names = [c[0][0] for c in mock_exec.call_args_list]
            assert "preview_data" in called_names
            assert "list_results" in called_names
            # Two tool messages in history
            tool_msgs = [m for m in msgs if m.get("role") == "tool"]
            assert len(tool_msgs) == 2

        asyncio.run(_run())

    def test_compact_history_none_content(self):
        """_compact_history handles content=None without crashing.

        LLMs sometimes send content=None on assistant messages that only have
        tool_calls. The compaction treats None as empty string.
        """
        msgs = [
            {"role": "user", "content": "go"},
            {"role": "assistant", "content": None, "tool_calls": [{"id": "t1"}]},
            {"role": "tool", "tool_call_id": "t1", "content": "x" * 500},
            {"role": "assistant", "content": "done", "tool_calls": [{"id": "t2"}]},
            {"role": "tool", "tool_call_id": "t2", "content": "result"},
        ]
        _compact_history(msgs)
        # None content on old assistant is left as-is (treated as empty, below threshold)
        assert msgs[1]["content"] is None
        # Old tool result is truncated
        assert msgs[2]["content"].endswith("[truncated]")
        # Last batch is intact
        assert msgs[4]["content"] == "result"

    def test_anthropic_cache_control_on_last_tool(self):
        """Anthropic model adds cache_control to the last tool schema."""
        agent = OptopsyAgent(model="anthropic/claude-test")
        assert len(agent.tools) > 0
        last_tool = agent.tools[-1]
        assert "cache_control" in last_tool
        assert last_tool["cache_control"] == {"type": "ephemeral"}
        # Non-last tools should NOT have cache_control
        if len(agent.tools) > 1:
            assert "cache_control" not in agent.tools[0]

    def test_non_anthropic_no_cache_control(self):
        """Non-Anthropic model does NOT add cache_control to tools."""
        agent = OptopsyAgent(model="openai/gpt-4")
        for tool in agent.tools:
            assert "cache_control" not in tool

    def test_results_memo_truncates_to_top_5(self):
        """Results memo shows only top 5 results by mean_return."""

        async def _run():
            agent = OptopsyAgent(model="anthropic/claude-test")
            agent.tools = []
            # Create 7 results with different mean_returns
            agent.results = {
                f"run{i}": {
                    "strategy": f"strategy_{i}",
                    "mean_return": 0.01 * i,
                    "win_rate": 0.5,
                }
                for i in range(7)
            }

            chunks = [_make_chunk(_make_delta(content="ok"))]

            with patch("litellm.acompletion", new_callable=AsyncMock) as mock_llm:
                mock_llm.return_value = _async_iter(chunks)
                await agent.chat([{"role": "user", "content": "compare"}])

            call_kwargs = mock_llm.call_args[1]
            system_msg = call_kwargs["messages"][0]
            memo_text = system_msg["content"][1]["text"]
            # Should mention 7 total runs
            assert "7 run(s)" in memo_text
            # Should mention 2 more not shown (7 - 5 = 2)
            assert "2 more not shown" in memo_text
            # Top strategy (strategy_6, mean=0.06) should be present
            assert "strategy_6" in memo_text
            # Bottom strategy (strategy_0, mean=0.0) should NOT be present
            assert "strategy_0" not in memo_text

        asyncio.run(_run())

    def test_non_anthropic_plain_system_prompt(self):
        """Non-Anthropic model gets plain string system prompt."""

        async def _run():
            agent = OptopsyAgent(model="openai/gpt-4")
            agent.tools = []

            chunks = [_make_chunk(_make_delta(content="ok"))]

            with patch("litellm.acompletion", new_callable=AsyncMock) as mock_llm:
                mock_llm.return_value = _async_iter(chunks)
                await agent.chat([{"role": "user", "content": "hi"}])

            call_kwargs = mock_llm.call_args[1]
            system_msg = call_kwargs["messages"][0]
            assert system_msg["role"] == "system"
            assert isinstance(system_msg["content"], str)

        asyncio.run(_run())

    def test_streaming_tool_call_chunk_accumulation(self):
        """Tool call arrives as multiple partial chunks — id, name, and args are accumulated."""

        async def _run():
            # First chunk: id and start of function name
            tc_part1 = MagicMock()
            tc_part1.index = 0
            tc_part1.id = "call_acc"
            tc_part1.function = MagicMock()
            tc_part1.function.name = "preview"
            tc_part1.function.arguments = '{"ro'

            # Second chunk: rest of function name and args (no id on continuation)
            tc_part2 = MagicMock()
            tc_part2.index = 0
            tc_part2.id = None
            tc_part2.function = MagicMock()
            tc_part2.function.name = "_data"
            tc_part2.function.arguments = 'ws": 5}'

            chunk1 = _make_chunk(_make_delta(tool_calls=[tc_part1]))
            chunk2 = _make_chunk(_make_delta(tool_calls=[tc_part2]))
            text_chunks = [_make_chunk(_make_delta(content="Done"))]
            call_count = 0

            async def mock_acompletion(**kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return _async_iter([chunk1, chunk2])
                return _async_iter(text_chunks)

            agent = OptopsyAgent(model="test/model")
            agent.tools = [{"type": "function", "function": {"name": "preview_data"}}]

            with (
                patch("litellm.acompletion", side_effect=mock_acompletion),
                patch("optopsy.ui.agent.execute_tool") as mock_exec,
                patch("asyncio.sleep", new_callable=AsyncMock),
            ):
                mock_result = MagicMock()
                mock_result.dataset = None
                mock_result.signals = None
                mock_result.datasets = None
                mock_result.results = None
                mock_result.llm_summary = "ok"
                mock_exec.return_value = mock_result

                content, msgs = await agent.chat(
                    [{"role": "user", "content": "show"}],
                )

            assert content == "Done"
            mock_exec.assert_called_once()
            # Verify accumulated name: "preview" + "_data" = "preview_data"
            actual_name = mock_exec.call_args[0][0]
            assert actual_name == "preview_data"
            # Verify accumulated args: '{"ro' + 'ws": 5}' = '{"rows": 5}'
            actual_args = mock_exec.call_args[0][1]
            assert actual_args == {"rows": 5}

        asyncio.run(_run())
