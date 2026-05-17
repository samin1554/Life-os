# Life OS — Session 4: Tool-Using Agents with Multi-Agent Handoffs (2026-05-11)

## Overview

This session added **two new agents** (Research + Worker) that use **real external tools** (web search, document generation) and enabled **multi-agent pipelines** where agents hand off accumulated context to each other. The chat now auto-detects complex multi-step requests and routes them through sequential agent pipelines — e.g., Execution → Research → Worker — producing downloadable documents.

**Example flow:**
```
User: "Plan a trip to Japan with a $2000 budget"
  → Supervisor detects pipeline: ["execution", "research", "worker"]
    → Execution Agent: creates itinerary + budget breakdown
      → Research Agent: searches web for flights, hotels, prices
        → Worker Agent: generates formatted Word/PDF/Excel document
          → Coach presents final response with download link
```

---

## Architecture Changes

### Before: Single-Agent Dispatch
- Chat detected intent → ran ONE agent → injected its output into coach prompt
- Agents were text-only LLM wrappers with no external tool access
- No way for agents to collaborate or pass context

### After: Multi-Agent Pipelines with Tool Use
- **Supervisor** now returns pipelines of agents (`["execution", "research", "worker"]`)
- **Chat endpoint** runs agents sequentially, passing accumulated context forward
- **Research Agent** uses ReAct loop with `web_search` and `scrape_page` tools
- **Worker Agent** uses ReAct loop with `generate_docx`, `generate_xlsx`, `generate_pdf` tools
- **Tool framework** provides a registry + ReAct execution loop any agent can use
- Generated files are stored locally in `generated_files/` and served via `/files/{filename}`

---

## Backend Changes

### New Files

| File | Purpose |
|------|---------|
| `core/tools.py` | Tool registry: `@register_tool` decorator, `TOOLS_REGISTRY`, `get_tools_for_agent()`, `format_tools_for_prompt()` |
| `core/tool_runner.py` | ReAct execution loop: `run_agent_with_tools()` — LLM reasons, calls tool, observes result, repeats up to `max_iterations`. `_extract_tool_call()` parses JSON tool calls from LLM responses. |
| `core/tools_web.py` | `web_search(query, max_results)` — Tavily primary, DuckDuckGo fallback. `scrape_page(url)` — fetches page via httpx, extracts text via BeautifulSoup. |
| `core/tools_docs.py` | `generate_docx(title, sections)`, `generate_xlsx(title, headers, rows, chart_type)`, `generate_pdf(title, sections)` — saves to `generated_files/` |
| `agents/research.py` | Research Agent using ReAct loop with `web_search` + `scrape_page`. Compiles structured findings with URLs and data points. |
| `agents/worker.py` | Worker Agent using ReAct loop with document generation tools. Analyzes input, picks best format (docx/xlsx/pdf), calls exactly ONE generation tool. |
| `routers/files.py` | `GET /files/{filename}` — authenticated file download endpoint with correct MIME types for docx/xlsx/pdf/png |

### Modified Files

| File | Changes |
|------|---------|
| `agents/orchestrator.py` | Added `run_research_agent` and `run_worker_agent` to `AGENT_RUNNERS` |
| `agents/runner.py` | Added `"research": "Research Agent"` and `"worker": "Worker Agent"` to `AGENT_DISPLAY_NAMES` |
| `agents/supervisor.py` | Added pipeline routing rules to system prompt. Added "research" and "worker" to `valid_agents`. Enhanced keyword fallback with research/worker/pipeline detection. |
| `routers/chat.py` | Replaced single-agent dispatch with multi-agent pipeline support. Accumulates context across agents. Detects worker-generated filenames via regex, returns `download_url`. Added `re` import. |
| `schemas/chat.py` | Added `download_url: Optional[str]` and `agents_pipeline: Optional[list[str]]` to `ChatResponse` |
| `main.py` | Added `files` router import and `app.include_router(files.router)` |
| `requirements.txt` | Added: `duckduckgo-search`, `beautifulsoup4`, `python-docx`, `openpyxl`, `reportlab`, `matplotlib`, `pandas` |

---

## Frontend Changes

### Modified Files

| File | Changes |
|------|---------|
| `types/index.ts` | Added `download_url?: string` and `agents_pipeline?: string[]` to `ChatMessage` interface |
| `hooks/useChat.ts` | Passes `download_url` and `agents_pipeline` from API response into message objects |
| `app/(app)/chat/page.tsx` | Added `Download` icon import. Added `research` (#00aaff) and `worker` (#ff5500) to `AGENT_COLORS`. Added pipeline breadcrumb display (`execution → research → worker`). Added download button for messages with `download_url`. Updated quick prompts to showcase new capabilities. |

---

## Key Code Patterns

### Tool Registration

```python
from core.tools import register_tool

@register_tool(
    name="web_search",
    description="Search the web...",
    parameters={"properties": {"query": "...", "max_results": "..."}},
)
async def web_search(query: str, max_results: int = 5) -> dict:
    ...
```

### ReAct Loop

```python
from core.tool_runner import run_agent_with_tools
from core.tools import get_tools_for_agent

tools = get_tools_for_agent(["web_search", "scrape_page"])
response = await run_agent_with_tools(
    system_prompt=SYSTEM_PROMPT,
    user_message=user_message,
    tools=tools,
    max_iterations=5,
)
```

### Multi-Agent Pipeline in Chat

```python
pipeline = [a for a in agents if a != "none" and a in ALL_AGENTS]
accumulated_context = ""

for agent_name in pipeline:
    input_text = req.message
    if accumulated_context:
        input_text = f"{req.message}\n\nContext:\n{accumulated_context}"

    interaction = await execute_agent_run(agent_name, input_text, ...)
    accumulated_context += f"\n\n[{agent_name} output]:\n{interaction.full_response}"

# Inject all agent outputs into coach prompt
system_prompt += AGENT_AUGMENTED_PROMPT.format(agent_output=accumulated_context)
```

---

## Build & Test Status

### Backend
- **91/91 tests passing** — `cd backend && python3 -m pytest tests/ -v`
- All new imports verified: `docx`, `openpyxl`, `reportlab`, `matplotlib`, `pandas`, `bs4`, `duckduckgo_search`
- New dependencies installed successfully

### Frontend
- **Build passes** — 13 routes, 0 errors, 0 warnings
- Middleware deprecation warning remains (non-blocking)

### Infrastructure
- Generated files stored in `backend/generated_files/` (created automatically)
- Download endpoint protected by Clerk JWT auth

---

## File Inventory

### Backend (new)

```
backend/
├── core/
│   ├── tools.py              ← NEW — tool registry
│   ├── tool_runner.py        ← NEW — ReAct execution loop
│   ├── tools_web.py          ← NEW — web search + scraping
│   └── tools_docs.py         ← NEW — docx/xlsx/pdf generation
├── agents/
│   ├── research.py           ← NEW — Research Agent
│   └── worker.py             ← NEW — Worker Agent
├── routers/
│   └── files.py              ← NEW — file download endpoint
└── generated_files/          ← NEW — generated document storage
```

### Backend (modified)

```
backend/
├── agents/
│   ├── orchestrator.py       ← + research, + worker
│   ├── runner.py             ← + display names
│   └── supervisor.py         ← + pipeline routing, + valid agents
├── routers/
│   └── chat.py               ← multi-agent pipeline support
├── schemas/
│   └── chat.py               ← + download_url, + agents_pipeline
├── main.py                   ← + files router
└── requirements.txt          ← + 7 new packages
```

### Frontend (modified)

```
frontend/
├── types/
│   └── index.ts              ← + download_url, + agents_pipeline
├── hooks/
│   └── useChat.ts            ← pass through new fields
└── app/(app)/chat/
    └── page.tsx              ← pipeline display, download button, new colors
```

---

## Known Issues & Deferred Work

| Issue | Status | Notes |
|-------|--------|-------|
| File storage is local filesystem | **MVP** | Plan originally specified S3/R2. Switched to local `generated_files/` for simplicity. Can migrate to cloud storage later. |
| No file cleanup | **Deferred** | Generated files accumulate in `generated_files/`. No expiry or cleanup job yet. |
| Worker filename extraction is regex-based | **MVP** | Scans worker response text for `"filename": "..."`. Could be made more robust with structured output. |
| Tavily needs API key | **Configured** | `tavily_api_key` exists in config but needs value in `.env`. DuckDuckGo fallback works without key. |
| No file listing UI | **Deferred** | User can download from chat, but no dedicated `/downloads` page to browse all generated files. |
| Pipeline max iterations | **MVP** | Research: 5, Worker: 3. Could hit LLM token limits with long accumulated context. |

---

## Environment & Configuration

```
Backend:    FastAPI 0.115, Python 3.12.6, SQLAlchemy 2.0+ (asyncpg), Alembic
Frontend:   Next.js 16.2.6, TypeScript, Tailwind v4, @clerk/nextjs v7, shadcn/ui (base-nova)
LLM:        Groq via OpenAI-compatible client — llama-3.3-70b-versatile (chat), llama-3.1-8b-instant (extraction)
Auth:       Clerk JWT verification, auto-creates local User on first visit
Tests:      pytest 8.4.2 + pytest-asyncio 0.24.0, asyncio_mode=auto, loop_scope="session"
Infra:      Docker Compose (PostgreSQL 5433, Redis 6381, Chroma 8010)
Ports:      Frontend 3002, Backend 8001, Postgres 5433, Redis 6381, Chroma 8010
New Tools:  Tavily/DuckDuckGo (web search), BeautifulSoup (scraping), python-docx, openpyxl, reportlab, matplotlib, pandas
```

---

## How to Verify

```bash
# Backend tests
cd backend && python3 -m pytest tests/ -v

# Frontend build
cd frontend && npm run build

# Start infrastructure
cd backend && docker compose up -d

# Start backend
cd backend && uvicorn main:app --reload --port 8001

# Start frontend
cd frontend && npm run dev -- --port 3002
```

**Test flows in browser:**
1. "Research best laptops under $1000" → Research Agent runs, web results in response
2. "Create a budget spreadsheet for a $2000 Japan trip" → Worker generates .xlsx, download link appears
3. "Plan a trip to Japan and create a travel guide PDF" → Pipeline: execution → research → worker → download link

---

## Design Decisions

1. **ReAct loop over single-shot tool calling**: The LLM reasons, calls one tool, observes the result, then decides next steps. This lets Research Agent search → scrape → search again based on findings.

2. **Local file storage over S3/R2**: Simpler for MVP. No cloud credentials needed. Files are served via FastAPI's `FileResponse`. Easy to migrate to S3 later by swapping `tools_docs.py` upload logic.

3. **Context accumulation via string concatenation**: Each agent in the pipeline receives the original user message plus all previous agents' outputs as a text block. Simple and effective, though token-limited.

4. **Worker Agent decides output format**: Rather than the user specifying "make an Excel", the Worker analyzes the request context and picks docx/xlsx/pdf automatically. Can be overridden by explicit user instruction.

5. **Tool registry pattern**: Tools are registered via decorator and discovered at import time. This makes adding new tools trivial — just create the function with `@register_tool` and import the module.
