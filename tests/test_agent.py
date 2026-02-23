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
)

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
            assert any(m["role"] == "assistant" for m in msgs)

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

            async def on_tool_call(name, args, result, tc_id):
                tool_calls_seen.append(name)

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
