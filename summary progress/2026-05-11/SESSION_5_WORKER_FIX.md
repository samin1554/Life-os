# Life OS — Session 5: Worker Agent Fix + Data Analysis & Visualization (2026-05-11)

## Overview

This session fixed the **Worker Agent not generating files** (it was outputting text instead of calling tools) and upgraded it into a full **data analysis + visualization engine** powered by pandas and matplotlib. The Worker Agent can now analyze data, generate charts, and export polished documents with embedded visualizations.

---

## Problem

After Session 4, the Worker Agent was dispatched correctly (supervisor routed to it, chat showed "Powered by Worker Agent") but it **never produced actual files**. Instead of calling `generate_xlsx` or `generate_docx`, the LLM output prose describing what a spreadsheet would look like. The frontend showed "No file was generated."

### Root Causes Identified

1. **Text-based tool calling is fundamentally unreliable** — the old approach told the LLM to output `{"tool": "...", "args": {...}}` in plain text, then parsed the response. LLMs (especially smaller fallback models) often output prose instead.
2. **`_extract_tool_call()` parser too strict** — only matched JSON on lines starting with `{`. Code blocks, embedded JSON, etc. were missed.
3. **Worker system prompt lacked concrete examples** — said "call exactly ONE tool" but never showed the exact JSON format expected.
4. **Tool parameter descriptions too vague** — e.g., `sheets: "list of sheet objects"` gave the LLM no idea what JSON structure to produce.
5. **Fallback models too weak** — when Groq rate-limited, fallback to 8b-instruct or gemini-flash-lite couldn't follow complex tool call instructions at all.

---

## Fixes Applied

### Fix 1: Native Function Calling (the critical fix)
**File:** `backend/core/tool_runner.py`, `backend/core/llm.py`

Replaced the entire text-based ReAct pattern with **native OpenAI-compatible function calling**:

- **Before:** LLM told to output `{"tool": "name", "args": {...}}` as text → parsed with regex → unreliable
- **After:** Tools passed via API `tools` parameter → API returns structured `tool_calls` → guaranteed structured output

New `chat_completion_with_tools()` in `llm.py`:
- Uses the `tools` parameter in the API call
- Parses `response.choices[0].message.tool_calls` for tool invocations
- Supports fallback providers (GitHub Models, Gemini) with the same `tools` API
- Returns `{content, tool_calls, raw_message}` dict

New `format_tools_for_api()` in `tools.py`:
- Converts `Tool` objects to OpenAI function calling format
- Builds proper JSON Schema `{type: "object", properties: {...}, required: [...]}`

Rewritten `run_agent_with_tools()`:
- Uses native tool calling as primary mechanism
- Falls back to text-based `_extract_tool_call()` parsing if API doesn't return tool_calls
- Uses `role: "tool"` messages with `tool_call_id` for proper conversation threading
- Temperature set to 0.3 for tool calling (more deterministic)

### Fix 2: Rewritten Worker System Prompt
**File:** `backend/agents/worker.py`

- Added "CRITICAL: You MUST call tools. Do NOT describe documents in text."
- Added 4 concrete few-shot examples showing exact tool call format
- Added multi-step workflow instructions (analyze → chart → export)

### Fix 3: Improved Tool Parameter Descriptions
**File:** `backend/core/tools_docs.py`

Changed parameter descriptions from vague prose to structured format:
```python
# Before:
"sheets": "list of sheet objects: {name, headers, rows, chart_type?}"

# After:
"sheets": {"type": "array", "description": "list of objects with keys: name (string), headers ([string]), rows ([[values]]), chart_type (optional: 'bar'|'pie'|'line'), summary (optional: 'totals'|'averages'|'both')"}
```

Updated `format_tools_for_prompt()` and added `format_tools_for_api()` in `core/tools.py`.

---

## New Feature: Data Analysis & Visualization

### New File: `backend/core/tools_data.py`

Two new tools powered by pandas + matplotlib:

#### `analyze_data` — Pandas Analysis Engine
Takes headers + rows + operations, returns structured results.

Supported operations:
- `describe` — summary statistics for all columns
- `group_by` — aggregation with custom agg functions (sum, mean, count, etc.)
- `sort` — sort by any column
- `filter` — conditional filtering (>, <, ==, contains, etc.)
- `add_column` — computed columns via pandas eval expressions
- `pivot` — pivot tables
- `top_n` — top/bottom N rows by a column
- `value_counts` — frequency distribution

#### `generate_chart` — Matplotlib Visualization
Generates styled PNG chart images with cyberpunk dark theme.

Supported chart types: `bar`, `horizontal_bar`, `line`, `pie`, `scatter`, `histogram`, `stacked_bar`

Options: custom axis labels, figure size, value annotations, multi-series datasets.

Charts are saved to `generated_files/` and can be embedded in docx/pdf exports.

### Enhanced Existing Tools

| Tool | Enhancement |
|------|-------------|
| `generate_xlsx` | New `summary` option: `"totals"`, `"averages"`, or `"both"` — adds Excel formula rows (SUM/AVERAGE) at bottom of sheets |
| `generate_docx` | New `chart_image` field in sections — embeds chart PNGs inline in the document |
| `generate_pdf` | Same `chart_image` support — embeds charts in PDF reports |

### Multi-Step Workflow

The Worker Agent now supports chained tool calls (max_iterations increased from 3 to 6):

```
User: "Analyze my sales data and create a report with charts"
  → Step 1: analyze_data — pandas groups/aggregates the data
  → Step 2: generate_chart — matplotlib creates bar chart PNG
  → Step 3: generate_pdf — builds PDF report with embedded chart + data tables
```

---

## Files Modified

| File | Changes |
|------|---------|
| `backend/core/tool_runner.py` | **Rewritten** — native function calling via `tools` API, text-based fallback, `role: "tool"` message threading |
| `backend/core/llm.py` | Added `chat_completion_with_tools()` + `_fallback_chat_with_tools()` for native function calling with provider fallback |
| `backend/core/tools.py` | Added `format_tools_for_api()` for OpenAI function calling format; updated `format_tools_for_prompt()` for dict params |
| `backend/core/tools_docs.py` | Improved parameter descriptions; added `chart_image` support to docx/pdf; added `summary` rows to xlsx |
| `backend/agents/worker.py` | Rewrote system prompt with few-shot examples; added 2 new tools; `max_iterations=6`, `max_tokens=4000` |

### New Files

| File | Purpose |
|------|---------|
| `backend/core/tools_data.py` | `analyze_data` (pandas) + `generate_chart` (matplotlib) tools |

---

## Worker Agent Tool Inventory

| Tool | Purpose | Library |
|------|---------|---------|
| `analyze_data` | Data analysis — group, sort, filter, pivot, stats | pandas, numpy |
| `generate_chart` | Chart/graph generation — bar, pie, line, scatter, etc. | matplotlib |
| `generate_xlsx` | Excel spreadsheets with charts + summary rows | openpyxl |
| `generate_docx` | Word documents with embedded charts | python-docx |
| `generate_pdf` | PDF reports with embedded charts | reportlab |

---

## Build & Test Status

- **Backend:** 91/91 tests passing
- **Frontend:** Build passes, 0 errors
- **Live test (native function calling):** Worker Agent called 3 tools in sequence for "Python vs JavaScript comparison": `generate_xlsx` (7.2KB) → `generate_chart` (41KB PNG) → `generate_docx` (73KB with embedded chart). All files verified on disk.
- **New tools tested:** `analyze_data` correctly groups/aggregates pandas DataFrames; `generate_chart` produces styled PNG images; chart embedding works in both docx and pdf

---

## How to Verify

```bash
# Backend tests
cd backend && python3 -m pytest tests/ -v

# Frontend build
cd frontend && npm run build
```

**Test in browser chat:**
1. "Create a budget spreadsheet with rent $1200, food $400, utilities $150" → xlsx generated with download link
2. "Analyze this data and make a chart: Product A $500, Product B $300, Product C $200" → chart + export
3. "Write a travel guide for Tokyo as a PDF" → pdf generated with download link

**Test multi-step pipeline:**
1. "Research the best budget laptops and create a comparison spreadsheet" → research → worker pipeline, xlsx with real data
