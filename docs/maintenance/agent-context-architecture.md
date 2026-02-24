# Agent Context Architecture Review

Last updated: 2026-02-24

Review of how the UI agent's tooling, prompts, and message history interact — focusing on context management, token efficiency, and gaps that cause poor multi-turn behavior.

---

## Current Architecture

### Data Flow

```
System Prompt (335 lines, cached on Anthropic)
    + Results Memo (top 5 runs, NOT cached — regenerated every call)
    + Message History (compacted after each tool iteration)
        ├── Old tool results: truncated to first line after 300 chars
        ├── Old assistant messages: truncated to first line after 300 chars
        └── Last tool batch: kept intact
    ↓
LLM decides: tool call OR final text response
    ↓
Tool execution → ToolResult
    ├── llm_summary   → appended to message history (role: tool)
    ├── user_display   → shown in Chainlit Step accordion
    ├── _result_df     → rendered as cl.Dataframe (interactive table)
    ├── chart_figure   → rendered as cl.Plotly
    └── state updates  → dataset, datasets, signals, results
```

### Dual Summary Pattern (ToolResult)

Every tool returns two text representations:

| Field | Recipient | Purpose |
|---|---|---|
| `llm_summary` | LLM (in message history) | Compact stats so LLM can reason without token bloat |
| `user_display` | User (in Chainlit Step) | Rich markdown tables, full data |

Default: `user_display = llm_summary` if not explicitly set.

### Message Compaction (`_COMPACT_THRESHOLD = 300`)

After each tool-calling iteration, `_compact_history()` truncates old messages:
- Keeps only the **first line** of old tool results and assistant reasoning
- Preserves the **last batch** of tool results intact

**Example after compaction:**
```
Turn 1 tool result: "long_calls — 37 aggregated stats [truncated]"
Turn 2 tool result: "long_calls — 602 raw trades [truncated]"
Turn 3 tool result: [full content preserved]
```

### Results Registry (`agent.results`)

Scalar summaries stored per strategy run:
```python
{
    "long_calls:dte=45,exit=0,otm=0.5,slip=mid": {
        "strategy": "long_calls",
        "count": 37, "mean_return": 0.0523,
        "std": 0.1234, "win_rate": 0.6486, "profit_factor": 1.45,
    }
}
```

Accessible to LLM via `list_results` and `compare_results` tools. Also surfaced as a top-5 memo in the system prompt.

---

## Problems

### 1. Post-Compaction Blindness

After compaction, the LLM cannot answer questions about previous results. It only sees:
```
"long_calls — 37 aggregated stats [truncated]"
```

**Impact:** User asks "show me the results of each bucket sorted by returns" and the LLM regurgitates from memory instead of referencing actual data.

**Root cause:** `llm_summary` for `run_strategy` is intentionally compact — just overall stats, no per-row data. After compaction, even that is truncated to one line.

**What the LLM gets for aggregated results:**
```
long_calls — 37 aggregated stats
pct_change: mean=-0.6000, std=0.3200, min=-1.0000, max=0.6760
DTE range: 7 to 90
Buckets with positive mean: 5/37
STOP — results are ready...
```

No per-bucket breakdown. The LLM literally cannot answer bucket-level questions.

### 2. Results Memo Not Cached

The top-5 results memo (appended to system prompt) changes after every strategy run, invalidating Anthropic's prompt cache for the entire system message on every call.

**Location:** `agent.py:481-512`

### 3. LLM Has No Tool to Query Result Data

The full result DataFrame is:
- Shown to the user as a `cl.Dataframe` element
- Stored transiently in `last_result_df` (session, for CSV download)
- **Never accessible to the LLM after the initial tool call**

There's no tool that lets the LLM say "give me the data from the last strategy run sorted by column X." The `list_results` tool only returns scalar summaries (mean, std, win_rate) — not per-bucket or per-trade data.

### 4. Redundant Information Paths

A single strategy run produces data in **four places**:
1. `llm_summary` — compact stats in message history (gets compacted)
2. `user_display` — full markdown table in Step accordion
3. `cl.Dataframe` — interactive table on the response message
4. Results memo — top-5 in system prompt (regenerated every call)

The LLM's text response may also reproduce the data as a table (now addressed by prompt instruction). This creates confusion about which is the "source of truth."

### 5. Session Resume Loses All State

On reconnect, `agent.dataset`, `agent.datasets`, `agent.signals` are all reset. Message history is rebuilt from Chainlit steps but in-memory DataFrames are gone. User must reload data.

---

## Tool-by-Tool: What LLM Gets vs Needs

| Tool | LLM Gets | LLM Needs But Doesn't Get |
|---|---|---|
| `run_strategy` (aggregated) | Overall stats, bucket count | Per-bucket rows (DTE, OTM, mean, count) |
| `run_strategy` (raw) | Overall pct_change stats | Individual trade details |
| `scan_strategies` | Best combo + header | Full leaderboard (only top entries visible) |
| `compare_results` | Top 5 comparison rows | Already good — but truncated after compaction |
| `list_results` | Top 5 by mean_return | Full list if >5 runs |
| `build_signal` | Date count + description | Date distribution, overlap with other signals |
| `preview_data` | Shape + date range | Already good for its purpose |

---

## Proposed Solutions

### Option A: Queryable Result Store (Recommended)

Add a tool that lets the LLM query the last result DataFrame:

```python
@_register("query_last_result")
def _handle_query(arguments, ...):
    """Sort, filter, or slice the last strategy result."""
    df = get_last_result_df()  # from session
    sort_by = arguments.get("sort_by")  # column name
    ascending = arguments.get("ascending", False)
    head = arguments.get("head", 20)

    if sort_by and sort_by in df.columns:
        df = df.sort_values(sort_by, ascending=ascending)

    return _result(
        _df_to_compact_summary(df.head(head)),
        user_display=_df_to_markdown(df.head(head)),
        result_df=df.head(head),
    )
```

**Pros:** LLM can answer any data question without re-running strategies. General purpose — works for any result shape.

**Cons:** Requires storing DataFrames in agent state (memory), adds one more tool call per follow-up question.

### Option B: Richer LLM Summaries

Include per-row data in `llm_summary` for aggregated results (capped at N rows). No new tools needed, but increases token usage per call and hardcodes assumptions about what the LLM might need.

**Pros:** Zero latency — data is already in context.

**Cons:** Token bloat for large results. Still can't handle arbitrary queries. Hardcoded to specific column structures.

### Option C: Smarter Compaction

Instead of truncating to first line, preserve a structured summary:

```python
# Instead of: "long_calls — 37 aggregated stats [truncated]"
# Preserve:   "long_calls — 37 aggregated stats | mean=-0.60 | 5/37 positive | top bucket: (30,45] (-0.05,0.0] mean=0.37"
```

**Pros:** No new tools, better multi-turn reasoning.

**Cons:** Still limited — can't answer arbitrary questions. Increases compacted message size.

### Option D: Separate Context Window for Results

Move result summaries out of message history into a dedicated context block (like the memo, but more structured and cached):

```python
# In system prompt construction:
system_content = [
    {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}},
    {"type": "text", "text": results_context},  # All results, structured
]
```

**Pros:** Results survive compaction. Can be cached independently.

**Cons:** Grows with session length. Still limited to what we pre-format.

---

## Recommendation

**Option A (Queryable Result Store)** is the most general solution:

1. Store the last N result DataFrames in agent state (keyed by result_key)
2. Add a `query_results` tool that accepts sort/filter/slice params
3. LLM calls it when users ask data questions — no re-running strategies
4. Works for any result shape (aggregated, raw, scan leaderboard)

Combined with **Option C (Smarter Compaction)** for basic multi-turn context, this gives the LLM enough to reason about results while keeping tokens manageable.

### Migration Path

1. Add `query_results` tool with sort_by, filter, head params
2. Store last result DataFrame in `agent.results[key]["_df"]` (or separate dict)
3. Update compaction to preserve 2-line summaries instead of 1-line
4. Cache the results memo block separately so it doesn't invalidate prompt cache
5. Update system prompt to tell LLM to use `query_results` for data questions
