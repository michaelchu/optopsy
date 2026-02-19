import asyncio
import json
from typing import Any

import litellm
import pandas as pd

from .tools import ToolResult, execute_tool, get_tool_schemas

litellm.suppress_debug_info = True

SYSTEM_PROMPT = """\
You are an options strategy backtesting assistant powered by the optopsy library.

You help users:
1. Fetch or load option chain data
2. Run backtests on 28 different options strategies
3. Interpret results and explain strategy performance

## Workflow
- If a data provider is available (e.g. `fetch_eodhd_options`), use it to fetch data for a ticker. \
This loads the data directly into memory — no file step needed.
- When fetching data, ALWAYS provide both `start_date` and `end_date`. This enables chunked \
fetching which retrieves complete datasets for large date ranges. If the user doesn't specify \
dates, pick a reasonable 3-month window ending today.
- Alternatively, use `list_data_files` and `load_csv_data` to load from local CSV files.
- Use `preview_data` to show the user what their dataset looks like.
- Run strategy functions (e.g. `long_calls`, `iron_condor`) to backtest strategies on the loaded data.
- Only tools that appear in your tool list are available. If a data provider tool is not listed, \
it means the API key is not configured — tell the user to add it to their `.env` file.

## Available Strategies and Option Type Filtering

When fetching data with `fetch_eodhd_options`, ALWAYS pass the `option_type` parameter based on \
the strategy the user wants to run. This halves the data volume and speeds up fetching significantly.

**Calls only** (pass `option_type: "call"`):
long_calls, short_calls, long_call_spread, short_call_spread, \
long_call_butterfly, short_call_butterfly, long_call_calendar, short_call_calendar, \
long_call_diagonal, short_call_diagonal, covered_call

**Puts only** (pass `option_type: "put"`):
long_puts, short_puts, long_put_spread, short_put_spread, \
long_put_butterfly, short_put_butterfly, long_put_calendar, short_put_calendar, \
long_put_diagonal, short_put_diagonal

**Both calls and puts** (omit `option_type`):
long_straddles, short_straddles, long_strangles, short_strangles, \
iron_condor, reverse_iron_condor, iron_butterfly, reverse_iron_butterfly, protective_put

IMPORTANT: If the user mentions a specific strategy, always filter by option_type during fetch. \
If comparing multiple strategies that need different types, omit the filter. \
If the user hasn't specified a strategy yet, omit the filter.

## Key Parameters (all optional)
- max_entry_dte: Max days to expiration at entry (default 90)
- exit_dte: DTE at exit (default 0, i.e. hold to expiration)
- max_otm_pct: Max out-of-the-money percentage (default 0.5)
- min_bid_ask: Min bid/ask threshold (default 0.05)
- raw: Set true for individual trades, false for aggregated stats (default false)
- slippage: "mid", "spread", or "liquidity" (default "mid")

Calendar/diagonal strategies also accept: front_dte_min, front_dte_max, back_dte_min, back_dte_max.

## CSV Format
The CSV should have columns (in order): underlying_symbol, underlying_price, option_type, \
expiration, quote_date, strike, bid, ask. Optional: delta, gamma, theta, vega, volume.
Column order can be remapped but the defaults assume this order.

## Understanding Output

### Aggregated mode (default, raw=false)
Results are grouped by DTE range and OTM percentage range, then `pct_change` is summarized \
with descriptive statistics. Columns:
- **dte_range**: The DTE bucket at entry (e.g. "(7, 14]" means 8-14 DTE)
- **otm_pct_range** (or otm_pct_range_leg1/leg2/...): OTM % bucket for each leg
- **count**: Number of trades in this bucket
- **mean**: Average percentage return (positive = profitable on average)
- **std**: Standard deviation of returns (volatility of outcomes)
- **min**: Worst single trade return
- **25%/50%/75%**: Quartile returns (50% is the median)
- **max**: Best single trade return

For multi-leg strategies, there are separate otm_pct_range columns per leg. \
Calendar/diagonal strategies have dte_range_leg1 and dte_range_leg2 for the front and back legs.

Use `mean` to judge overall profitability, `count` for sample size, `std` for risk, and \
`min`/`max` for tail behavior. A positive mean with low std and high count is the strongest signal.

### Raw mode (raw=true)
Returns individual trades. Key columns:
- **underlying_symbol, expiration, dte_entry**: What was traded and when
- **strike** (or strike_leg1/leg2/...): Strike prices for each leg
- **total_entry_cost**: Net debit (negative) or credit (positive) to open
- **total_exit_proceeds**: Net amount received/paid at close
- **pct_change**: Return as a decimal (e.g. 0.25 = 25% gain, -0.5 = 50% loss)

For single-leg strategies: `entry` and `exit` are the fill prices. \
For multi-leg: individual leg prices are shown plus totals.

### How pct_change is calculated
pct_change = (total_exit_proceeds - total_entry_cost) / |total_entry_cost|

A debit strategy (you pay to enter) has negative total_entry_cost. \
A credit strategy (you receive premium) has positive total_entry_cost. \
Positive pct_change = profit, negative = loss.

## Guidelines
- Always load data before running strategies.
- If a strategy returns empty results, suggest relaxing filters (increase max_entry_dte or max_otm_pct).
- When interpreting aggregated results, focus on: which DTE/OTM buckets are most profitable (highest mean), \
which have enough trades to be statistically meaningful (count > 10), and risk-adjusted performance (mean/std).
- For comparisons, run both strategies and compare mean returns, win rates (% of buckets with positive mean), \
and consistency (lower std is better).
- Be concise but helpful. The tool results are already formatted as markdown tables.
"""


_MAX_TOOL_ITERATIONS = 15


class OptopsyAgent:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.tools = get_tool_schemas()
        self.dataset: pd.DataFrame | None = None

    async def chat(
        self,
        messages: list[dict[str, Any]],
        on_tool_call=None,
        on_token=None,
    ) -> tuple[str, list[dict[str, Any]]]:
        """
        Run the agent loop: send messages to LLM, execute any tool calls,
        and return (final_response_text, updated_messages).

        on_tool_call: async callback(tool_name, arguments, result) — UI step display.
        on_token: async callback(token_str) — called for each streamed token on
                  the *final* response (the one shown to the user).

        Note: The system prompt is prepended on every LLM call so context is
        maintained across tool-calling iterations.  This is intentional but
        means token usage grows with conversation length.  For very long
        sessions consider adding history summarization before calling chat().
        """
        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

        for _iteration in range(_MAX_TOOL_ITERATIONS):
            # -- tool-calling turns: non-streaming for simplicity --
            try:
                response = await litellm.acompletion(
                    model=self.model,
                    messages=full_messages,
                    tools=self.tools,
                    tool_choice="auto",
                )
            except litellm.AuthenticationError:
                raise RuntimeError(
                    "No API key configured. Add your LLM provider key "
                    "(e.g. `OPENAI_API_KEY`) to a `.env` file in this directory."
                )
            except litellm.RateLimitError:
                raise RuntimeError(
                    "LLM rate limit exceeded. Wait a moment and try again, "
                    "or switch to a model with higher rate limits."
                )
            except (litellm.ServiceUnavailableError, litellm.APIConnectionError):
                raise RuntimeError(
                    "LLM service is temporarily unavailable. Please try again shortly."
                )

            choice = response.choices[0]
            assistant_msg = choice.message

            # Append assistant message to history
            msg_dict: dict[str, Any] = {
                "role": "assistant",
                "content": assistant_msg.content or "",
            }
            if assistant_msg.tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in assistant_msg.tool_calls
                ]
            full_messages.append(msg_dict)

            # If no tool calls, this is the final answer.
            if not assistant_msg.tool_calls:
                # If we already got the full response above (non-streamed
                # intermediate turns that happened to be the last one), just
                # emit the content token-by-token for the UI.
                content = assistant_msg.content or ""
                if on_token and content:
                    # Emit in small chunks so the UI feels responsive
                    for i in range(0, len(content), 4):
                        await on_token(content[i : i + 4])
                return content, full_messages[1:]

            # Execute each tool call
            for tc in assistant_msg.tool_calls:
                func_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                # Run tool in a thread so the event loop stays alive
                # (keeps WebSocket heartbeats flowing during long fetches).
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda fn=func_name, a=args, ds=self.dataset: execute_tool(
                        fn, a, ds
                    ),
                )
                self.dataset = result.dataset

                # Show the rich version to the user in the UI
                if on_tool_call:
                    await on_tool_call(func_name, args, result.user_display)

                # Send only the concise summary to the LLM
                full_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result.llm_summary,
                    }
                )

        # If we exhausted the iteration limit, return what we have
        raise RuntimeError(
            f"Agent exceeded {_MAX_TOOL_ITERATIONS} tool-calling iterations. "
            "This likely indicates a loop — please simplify your request."
        )
