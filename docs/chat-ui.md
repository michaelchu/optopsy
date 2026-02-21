# AI Chat UI

Optopsy includes an AI-powered chat interface that lets you fetch data, run backtests, and interpret results using natural language.

![AI Chat UI](images/chat-ui.png)

## What it does

- Fetches historical options data via the [EODHD US Stock Options Data API](https://eodhd.com/financial-apis/options-data-api) (API key required)
- Runs any of the 28 built-in strategies via conversational prompts
- Explains results and compares strategies side by side
- Works with any OpenAI-compatible LLM (GPT-4o, Claude, Llama, etc. via [LiteLLM](https://github.com/BerriAI/litellm))

## Installation

```bash
pip install optopsy[ui]
```

## Configuration

Create a `.env` file with your API keys (see `.env.example`):

```
ANTHROPIC_API_KEY=sk-...   # or OPENAI_API_KEY for OpenAI models
EODHD_API_KEY=...
```

### Environment Variables

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | LLM provider API key (default provider) |
| `OPENAI_API_KEY` | Alternative LLM provider |
| `OPTOPSY_MODEL` | Override model (LiteLLM format, default: `anthropic/claude-haiku-4-5-20251001`) |
| `EODHD_API_KEY` | Enable EODHD data provider for live options/stock data |

### Model Selection

Defaults to Claude Haiku 4.5 for its low cost and generous rate limits. To use a different model, set `OPTOPSY_MODEL` and the matching API key:

```
OPTOPSY_MODEL=gpt-4o
OPENAI_API_KEY=sk-...
```

## Launch

```bash
optopsy-chat
```

Your conversations are saved automatically and available in the sidebar. Fetched options data is cached locally so subsequent requests for the same symbol skip the API call.

### Launch Options

```bash
optopsy-chat run --port 9000 --headless --debug
```

## Cache Management

```bash
optopsy-chat cache size          # show disk usage
optopsy-chat cache clear         # clear all cached data
optopsy-chat cache clear SPY     # clear a specific symbol
```

## Example Prompts

- *"Fetch SPY options from 2024-01-01 to 2024-06-30 and run short puts with max 45 DTE, exit at 7 DTE"*
- *"Compare iron condors vs iron butterflies on SPY from 2023-06-01 to 2024-01-01 with 30 and 60 day max entry DTE"*
- *"Run short puts on SPY from 2024-01-01 to 2024-12-31 with RSI below 30 sustained for 3 days as the entry signal"*
