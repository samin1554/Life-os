# Life OS — Tool-Using Agents with Multi-Agent Handoffs

## Context

This is a FastAPI + Next.js AI life coach app with 7 domain agents (focus, health, execution, chaos_triage, goals, relationships, delegate). Agents are simple LLM wrappers — they receive a user message, call `chat_completion()` via Groq (llama-3.3-70b-versatile), and return a text response. None of them have access to external tools (web search, file generation, etc.).

The chat endpoint (`POST /chat`) auto-dispatches to the right agent via `classify_intent()` from `agents/supervisor.py`, runs the agent via `execute_agent_run()` from `agents/runner.py`, and injects the agent's output into the coach's response.

**Goal:** Add two new agents (Research + Worker) that use real tools (web search, document generation), and enable multi-agent pipelines where agents hand off work to each other with accumulated context.

**Example flow:**
```
User: "Plan a trip to Japan with a $2000 budget"
  → Execution Agent: creates itinerary outline + budget breakdown
    → Research Agent: searches web for flights, hotels, current prices
      → Worker Agent: generates a formatted Word/PDF/Excel document
        → Coach presents the final document with download link
```

---

## Existing Codebase (Read These First)

Before making any changes, read these files to understand the patterns:

| File | Why |
|------|-----|
| `backend/agents/execution.py` | Example domain agent pattern — all agents follow this structure: system prompt + `run_X_agent(user_message, user_id, db) -> dict` |
| `backend/agents/orchestrator.py` | Contains `AGENT_RUNNERS` dict mapping agent names to functions. New agents must be registered here |
| `backend/agents/runner.py` | `execute_agent_run()` wraps all agent calls with `AgentInteraction` DB tracking + Redis pub/sub events. Contains `AGENT_DISPLAY_NAMES` and `ALL_AGENTS` |
| `backend/agents/supervisor.py` | `classify_intent()` routes user messages to agents. Has LLM prompt + keyword fallback. Currently supports "none" for casual chat |
| `backend/routers/chat.py` | Chat endpoint. Calls `classify_intent()`, runs single agent via `execute_agent_run()`, injects output into coach prompt. Needs to support multi-agent pipelines |
| `backend/core/llm.py` | `chat_completion(system_prompt, messages)` and `extract_structured(system_prompt, messages)` — Groq API via AsyncOpenAI. Models: llama-3.3-70b-versatile (chat), llama-3.1-8b-instant (extraction) |
| `backend/core/config.py` | Settings with `tavily_api_key` (already defined, needs value in .env) |
| `backend/models/models.py` | SQLAlchemy models. `AgentInteraction` tracks every agent run with status, input/output, timestamps |
| `backend/schemas/chat.py` | `ChatResponse` has `response`, `session_id`, `agent_used`, `agent_display_name` |

**Agent function signature (every agent follows this):**
```python
async def run_X_agent(user_message: str, user_id: str, db: AsyncSession) -> dict:
    return {"agent": "agent_name", "response": "...", ...}
```

**Key infrastructure:**
- Python 3.12, FastAPI 0.115, SQLAlchemy 2.0 async (asyncpg), PostgreSQL 5433, Redis 6381
- Groq LLM via OpenAI-compatible AsyncOpenAI client
- All async tests use `@pytest.mark.asyncio(loop_scope="session")`
- `tavily-python==0.5.0` already in requirements.txt (unused, needs API key)

---

## Phase 1: Tool Framework + Web Search Tools

### 1.1 Create `core/tools.py` — Tool Registry

A simple tool registry that agents use to declare and call tools.

```python
from dataclasses import dataclass
from typing import Callable, Any

@dataclass
class Tool:
    name: str
    description: str
    func: Callable
    parameters: dict  # JSON schema for LLM tool-calling

TOOLS_REGISTRY: dict[str, Tool] = {}

def register_tool(name: str, description: str, parameters: dict):
    def decorator(func):
        TOOLS_REGISTRY[name] = Tool(name=name, description=description, func=func, parameters=parameters)
        return func
    return decorator

def get_tools_for_agent(tool_names: list[str]) -> list[Tool]:
    return [TOOLS_REGISTRY[name] for name in tool_names if name in TOOLS_REGISTRY]

def format_tools_for_prompt(tools: list[Tool]) -> str:
    """Format tool descriptions for inclusion in an LLM system prompt."""
    lines = []
    for t in tools:
        params = ", ".join(f"{k}: {v}" for k, v in t.parameters.get("properties", {}).items())
        lines.append(f"- {t.name}({params}): {t.description}")
    return "\n".join(lines)
```

### 1.2 Create `core/tool_runner.py` — ReAct Execution Loop

An agent loop that lets the LLM reason, call tools, observe results, and decide next steps.

```python
import json
from core.llm import chat_completion
from core.tools import Tool, format_tools_for_prompt

TOOL_USE_PROMPT = """You have access to the following tools:
{tool_descriptions}

To use a tool, respond with EXACTLY this JSON format on its own line:
{{"tool": "tool_name", "args": {{"param1": "value1"}}}}

After receiving tool results, continue reasoning. When you have a final answer, respond normally without any tool calls.

IMPORTANT: Only call one tool at a time. Wait for results before calling another."""

async def run_agent_with_tools(
    system_prompt: str,
    user_message: str,
    tools: list[Tool],
    max_iterations: int = 5,
    model: str = "llama-3.3-70b-versatile",
) -> str:
    """ReAct loop: LLM reasons → calls tool → observes result → repeats until final answer."""
    tool_descriptions = format_tools_for_prompt(tools)
    full_system = f"{system_prompt}\n\n{TOOL_USE_PROMPT.format(tool_descriptions=tool_descriptions)}"

    messages = [{"role": "user", "content": user_message}]

    for _ in range(max_iterations):
        response = await chat_completion(full_system, messages, model=model, max_tokens=1500)

        # Check if response contains a tool call
        tool_call = _extract_tool_call(response)
        if tool_call is None:
            return response  # Final answer

        tool_name, args = tool_call
        tool = next((t for t in tools if t.name == tool_name), None)
        if tool is None:
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": f"Error: Unknown tool '{tool_name}'. Available: {[t.name for t in tools]}"})
            continue

        # Execute tool
        try:
            result = await tool.func(**args)
            result_str = json.dumps(result) if isinstance(result, (dict, list)) else str(result)
        except Exception as e:
            result_str = f"Tool error: {e}"

        messages.append({"role": "assistant", "content": response})
        messages.append({"role": "user", "content": f"Tool result ({tool_name}):\n{result_str}"})

    return response  # Return last response if max iterations reached

def _extract_tool_call(text: str):
    """Extract a tool call JSON from LLM response text."""
    for line in text.strip().split("\n"):
        line = line.strip()
        if line.startswith("{") and '"tool"' in line:
            try:
                parsed = json.loads(line)
                if "tool" in parsed and "args" in parsed:
                    return parsed["tool"], parsed["args"]
            except json.JSONDecodeError:
                continue
    # Also try parsing the entire response as JSON
    try:
        parsed = json.loads(text.strip())
        if "tool" in parsed and "args" in parsed:
            return parsed["tool"], parsed["args"]
    except json.JSONDecodeError:
        pass
    return None
```

### 1.3 Create `core/tools_web.py` — Web Search + Scraping Tools

```python
from core.tools import register_tool
from core.config import get_settings

@register_tool(
    name="web_search",
    description="Search the web for current information. Returns titles, URLs, and snippets.",
    parameters={"properties": {"query": "search query string", "max_results": "number of results (default 5)"}},
)
async def web_search(query: str, max_results: int = 5) -> dict:
    """Search using Tavily (primary) or DuckDuckGo (fallback)."""
    settings = get_settings()

    if settings.tavily_api_key:
        from tavily import AsyncTavilyClient
        client = AsyncTavilyClient(api_key=settings.tavily_api_key)
        result = await client.search(query=query, max_results=max_results, include_answer=True)
        return {
            "answer": result.get("answer", ""),
            "results": [
                {"title": r["title"], "url": r["url"], "content": r["content"][:500]}
                for r in result.get("results", [])[:max_results]
            ],
        }
    else:
        # DuckDuckGo fallback (no API key needed)
        from duckduckgo_search import AsyncDDGS
        async with AsyncDDGS() as ddgs:
            results = []
            async for r in ddgs.atext(query, max_results=max_results):
                results.append({"title": r["title"], "url": r["href"], "content": r["body"][:500]})
            return {"answer": "", "results": results}


@register_tool(
    name="scrape_page",
    description="Fetch and extract the main text content from a URL.",
    parameters={"properties": {"url": "the URL to scrape"}},
)
async def scrape_page(url: str) -> dict:
    """Fetch a web page and extract text content."""
    import httpx
    from bs4 import BeautifulSoup

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": "LifeOS-Agent/1.0"})
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    return {"url": url, "content": text[:3000], "title": soup.title.string if soup.title else ""}
```

### 1.4 Create `agents/research.py` — Research Agent

```python
"""Research Agent — searches the web and compiles structured findings."""
from sqlalchemy.ext.asyncio import AsyncSession

from core.tools import get_tools_for_agent
from core.tool_runner import run_agent_with_tools
from agents.shared import get_user_context

RESEARCH_TOOLS = ["web_search", "scrape_page"]

SYSTEM_PROMPT = """You are the Research Agent for Life OS.

Your job is to research topics by searching the web and compiling findings into structured, actionable information.

Guidelines:
- Start by searching for the most relevant information using web_search
- If a search result looks promising, use scrape_page to get more detail
- Compile your findings into a clear, structured format
- Include specific data points: prices, dates, ratings, URLs
- Always cite your sources with URLs
- If you receive context from a previous agent (e.g., an execution plan), use it to guide your research
- Present findings as structured sections, not a wall of text
"""

async def run_research_agent(user_message: str, user_id: str, db: AsyncSession) -> dict:
    tools = get_tools_for_agent(RESEARCH_TOOLS)
    response = await run_agent_with_tools(
        system_prompt=SYSTEM_PROMPT,
        user_message=user_message,
        tools=tools,
        max_iterations=5,
    )
    return {"agent": "research", "response": response}
```

### 1.5 Register Research Agent

**In `agents/orchestrator.py`** — add to imports and `AGENT_RUNNERS`:
```python
from agents.research import run_research_agent

AGENT_RUNNERS = {
    ...existing entries...,
    "research": run_research_agent,
}
```

**In `agents/runner.py`** — add to `AGENT_DISPLAY_NAMES`:
```python
AGENT_DISPLAY_NAMES = {
    ...existing entries...,
    "research": "Research Agent",
    "worker": "Worker Agent",
}
```

**In `agents/supervisor.py`** — add "research" and "worker" to `valid_agents` set. Add routing rule:
```
- If the user asks to research, look up, compare, or find current information from the web → invoke research
```

Also add to the keyword fallback.

### 1.6 Add Dependencies

Add to `requirements.txt`:
```
duckduckgo-search>=6.0
beautifulsoup4>=4.12
python-docx>=1.1.0
openpyxl>=3.1.0
reportlab>=4.0.0
matplotlib>=3.8.0
pandas>=2.2.0
```

Then run: `pip3 install -r requirements.txt`

---

## Phase 2: Worker Agent + Document Generation

### 2.1 Create `core/tools_docs.py` — Document Generation Tools

```python
import io
import os
import uuid
from datetime import datetime
from core.tools import register_tool

GENERATED_FILES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "generated_files")
os.makedirs(GENERATED_FILES_DIR, exist_ok=True)


@register_tool(
    name="generate_docx",
    description="Generate a Word document (.docx) with sections of text. Returns the file path.",
    parameters={"properties": {"title": "document title", "sections": "list of {heading, content} dicts"}},
)
async def generate_docx(title: str, sections: list[dict]) -> dict:
    from docx import Document
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph(f"Generated by Life OS — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    for section in sections:
        doc.add_heading(section.get("heading", ""), level=1)
        doc.add_paragraph(section.get("content", ""))
    filename = f"{uuid.uuid4().hex[:8]}_{title.replace(' ', '_')[:30]}.docx"
    filepath = os.path.join(GENERATED_FILES_DIR, filename)
    doc.save(filepath)
    return {"filename": filename, "filepath": filepath, "format": "docx"}


@register_tool(
    name="generate_xlsx",
    description="Generate an Excel spreadsheet (.xlsx) with data rows and optional charts. Returns the file path.",
    parameters={"properties": {"title": "spreadsheet title", "headers": "list of column headers", "rows": "list of lists (row data)", "chart_type": "optional: bar, pie, line"}},
)
async def generate_xlsx(title: str, headers: list[str], rows: list[list], chart_type: str = None) -> dict:
    from openpyxl import Workbook
    from openpyxl.chart import BarChart, PieChart, LineChart, Reference

    wb = Workbook()
    ws = wb.active
    ws.title = title[:31]
    ws.append(headers)
    for row in rows:
        ws.append(row)

    if chart_type and len(rows) > 0:
        chart_classes = {"bar": BarChart, "pie": PieChart, "line": LineChart}
        ChartClass = chart_classes.get(chart_type, BarChart)
        chart = ChartClass()
        chart.title = title
        data = Reference(ws, min_col=2, min_row=1, max_col=len(headers), max_row=len(rows) + 1)
        cats = Reference(ws, min_col=1, min_row=2, max_row=len(rows) + 1)
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(cats)
        ws.add_chart(chart, f"A{len(rows) + 4}")

    filename = f"{uuid.uuid4().hex[:8]}_{title.replace(' ', '_')[:30]}.xlsx"
    filepath = os.path.join(GENERATED_FILES_DIR, filename)
    wb.save(filepath)
    return {"filename": filename, "filepath": filepath, "format": "xlsx"}


@register_tool(
    name="generate_pdf",
    description="Generate a PDF document with title and text sections. Returns the file path.",
    parameters={"properties": {"title": "document title", "sections": "list of {heading, content} dicts"}},
)
async def generate_pdf(title: str, sections: list[dict]) -> dict:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

    filename = f"{uuid.uuid4().hex[:8]}_{title.replace(' ', '_')[:30]}.pdf"
    filepath = os.path.join(GENERATED_FILES_DIR, filename)

    doc = SimpleDocTemplate(filepath, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph(title, styles["Title"]))
    story.append(Spacer(1, 12))
    for section in sections:
        story.append(Paragraph(section.get("heading", ""), styles["Heading1"]))
        story.append(Spacer(1, 6))
        for para in section.get("content", "").split("\n"):
            if para.strip():
                story.append(Paragraph(para, styles["Normal"]))
                story.append(Spacer(1, 4))
    doc.build(story)
    return {"filename": filename, "filepath": filepath, "format": "pdf"}
```

### 2.2 Create `agents/worker.py` — Worker Agent

```python
"""Worker Agent — generates documents, spreadsheets, and visualizations."""
from sqlalchemy.ext.asyncio import AsyncSession

from core.tools import get_tools_for_agent
from core.tool_runner import run_agent_with_tools

WORKER_TOOLS = ["generate_docx", "generate_xlsx", "generate_pdf"]

SYSTEM_PROMPT = """You are the Worker Agent for Life OS.

Your job is to take structured plans and research findings and produce downloadable documents.

Guidelines:
- Analyze the input to determine the best output format:
  - Word (.docx): for reports, guides, essays, plans with narrative text
  - Excel (.xlsx): for budgets, trackers, comparison tables, data with numbers
  - PDF (.pdf): for formal reports, printable summaries
- Structure your data carefully before calling a tool. For docx/pdf, create clear sections with headings and content. For xlsx, create proper headers and data rows.
- If the input mentions charts, budget, or numbers → prefer Excel with a chart
- If the input mentions report, guide, or plan → prefer Word or PDF
- Always call exactly ONE generation tool to produce the final output
- Include all relevant data from the input — don't summarize away important details

IMPORTANT: When calling generate_xlsx, "rows" must be a list of lists where each inner list contains values matching the headers. Example:
headers: ["Item", "Cost", "Notes"]
rows: [["Flight", 850, "Round trip"], ["Hotel", 600, "7 nights"]]

When calling generate_docx or generate_pdf, "sections" must be a list of objects with "heading" and "content" keys. Example:
sections: [{"heading": "Day 1", "content": "Arrive in Tokyo..."}]
"""

async def run_worker_agent(user_message: str, user_id: str, db: AsyncSession) -> dict:
    tools = get_tools_for_agent(WORKER_TOOLS)
    response = await run_agent_with_tools(
        system_prompt=SYSTEM_PROMPT,
        user_message=user_message,
        tools=tools,
        max_iterations=3,
    )
    return {"agent": "worker", "response": response}
```

Register in `orchestrator.py`:
```python
from agents.worker import run_worker_agent
AGENT_RUNNERS["worker"] = run_worker_agent
```

### 2.3 Create File Download Endpoint

**New file: `routers/files.py`**

```python
"""File download endpoint for generated documents."""
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from core.security import get_current_user
from models import User

router = APIRouter(prefix="/files", tags=["files"])

GENERATED_FILES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "generated_files")

MIME_TYPES = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pdf": "application/pdf",
    ".png": "image/png",
}

@router.get("/{filename}")
async def download_file(
    filename: str,
    current_user: User = Depends(get_current_user),
):
    filepath = os.path.join(GENERATED_FILES_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    ext = os.path.splitext(filename)[1]
    return FileResponse(filepath, media_type=MIME_TYPES.get(ext, "application/octet-stream"), filename=filename)
```

Register in `main.py`:
```python
from routers import files
app.include_router(files.router)
```

---

## Phase 3: Multi-Agent Pipeline Handoffs

### 3.1 Update Chat Endpoint for Pipelines

**File: `routers/chat.py`**

Currently the chat endpoint runs a single agent. Change it to support sequential pipelines where each agent receives accumulated context from previous agents.

Replace the single-agent dispatch block with:

```python
agent_used = None
agent_display_name = None
download_url = None

try:
    recent_context = None
    if history:
        last_messages = history[-4:]
        recent_context = "\n".join(f"{m['role']}: {m['content'][:200]}" for m in last_messages)
    intent = await classify_intent(req.message, context=recent_context)
    agents = intent.get("agents", ["none"])

    # Filter out "none" and invalid agents
    pipeline = [a for a in agents if a != "none" and a in ALL_AGENTS]

    if pipeline:
        accumulated_context = ""
        last_interaction = None

        for agent_name in pipeline:
            input_text = req.message
            if accumulated_context:
                input_text = f"{req.message}\n\nContext from previous analysis:\n{accumulated_context}"

            interaction = await execute_agent_run(
                agent_name=agent_name,
                input_text=input_text,
                user_id=str(current_user.id),
                db=db,
                trigger_type="chat",
            )

            if interaction.status == "completed" and interaction.full_response:
                accumulated_context += f"\n\n[{agent_name} output]:\n{interaction.full_response}"
                last_interaction = interaction

        if last_interaction and last_interaction.full_response:
            system_prompt += AGENT_AUGMENTED_PROMPT.format(agent_output=accumulated_context)
            agent_used = pipeline[-1]  # Report the last agent in pipeline
            agent_display_name = AGENT_DISPLAY_NAMES.get(agent_used, agent_used)

            # Check if worker produced a file (look for filename in response)
            if "worker" in pipeline:
                import re
                file_match = re.search(r'"filename":\s*"([^"]+)"', last_interaction.full_response)
                if file_match:
                    download_url = f"/files/{file_match.group(1)}"

except Exception as e:
    logger.warning(f"Agent dispatch failed, falling back to direct coach: {e}")
```

### 3.2 Update ChatResponse Schema

**File: `schemas/chat.py`**

```python
class ChatResponse(BaseModel):
    response: str
    session_id: str
    agent_used: Optional[str] = None
    agent_display_name: Optional[str] = None
    download_url: Optional[str] = None  # NEW — file download link from Worker Agent
    agents_pipeline: Optional[list[str]] = None  # NEW — all agents used in pipeline
```

### 3.3 Update Supervisor for Pipeline Detection

**File: `agents/supervisor.py`**

Add pipeline routing rules to the system prompt:

```
PIPELINE ROUTING — when a request requires multiple steps:
- "Plan a trip and create a document/guide" → ["execution", "research", "worker"]
- "Research X and make a spreadsheet/report" → ["research", "worker"]  
- "Create a budget/tracker for X" → ["execution", "worker"]
- "Research X" (no document needed) → ["research"]
- "Make me a document about X" → ["execution", "worker"]

When returning a pipeline, list agents in execution order. Each agent's output feeds into the next.
```

Add "research" and "worker" to the `valid_agents` set and to the keyword fallback.

---

## Phase 4: Frontend Updates

### 4.1 Update Types

**File: `frontend/types/index.ts`**

```typescript
// Add to ChatMessage:
export interface ChatMessage {
  ...existing fields...
  download_url?: string;
  agents_pipeline?: string[];
}
```

### 4.2 Update Chat Hook

**File: `frontend/hooks/useChat.ts`**

Pass through `download_url` and `agents_pipeline` from API response to message objects.

### 4.3 Update Chat Page

**File: `frontend/app/(app)/chat/page.tsx`**

Add download button on messages that have `download_url`:

```tsx
{msg.download_url && (
  <a
    href={`${API_BASE}${msg.download_url}`}
    target="_blank"
    className="mt-3 inline-flex items-center gap-2 px-4 py-2 bg-[#00ff88]/10 
      border border-[#00ff88]/30 text-[#00ff88] text-xs font-mono uppercase 
      tracking-wider hover:bg-[#00ff88]/20 transition-all cyber-chamfer-sm"
  >
    <Download className="w-3.5 h-3.5" />
    Download Document
  </a>
)}
```

Show pipeline progress when multiple agents are used:
```tsx
{msg.agents_pipeline && msg.agents_pipeline.length > 1 && (
  <div className="flex items-center gap-1.5 mb-2 text-[10px] font-mono text-[#6b7280]">
    {msg.agents_pipeline.map((agent, i) => (
      <span key={agent} className="flex items-center gap-1">
        {i > 0 && <span>→</span>}
        <span style={{ color: AGENT_COLORS[agent] || "#6b7280" }}>{agent}</span>
      </span>
    ))}
  </div>
)}
```

---

## Build Order

1. `core/tools.py` — tool registry (no dependencies)
2. `core/tool_runner.py` — ReAct loop (depends on tools.py + llm.py)
3. `core/tools_web.py` — web search tools (depends on tools.py)
4. `agents/research.py` — Research Agent (depends on tool_runner + tools_web)
5. Register research agent in `orchestrator.py`, `runner.py`, `supervisor.py`
6. **Test**: Send "Research best standing desks under $500" in chat → should get web search results
7. `core/tools_docs.py` — document generation tools
8. `agents/worker.py` — Worker Agent (depends on tool_runner + tools_docs)
9. `routers/files.py` — file download endpoint
10. Register worker agent in `orchestrator.py`, `runner.py`, `supervisor.py`
11. Update `routers/chat.py` for multi-agent pipeline support
12. Update `schemas/chat.py` with download_url and agents_pipeline
13. Register files router in `main.py`
14. **Test**: Send "Plan a trip to Japan and create a travel guide" → should produce a downloadable document
15. Frontend: update types, hook, and chat page for download links + pipeline display
16. **Test**: Full flow in browser

## Verification

```bash
# Install new dependencies
cd backend && pip3 install -r requirements.txt

# Run tests
cd backend && python3 -m pytest tests/ -v

# Build frontend
cd frontend && npm run build

# Test in browser
# 1. "Research best laptops under $1000" → Research Agent runs, web results in response
# 2. "Create a budget spreadsheet for a $2000 Japan trip" → Worker generates .xlsx, download link appears
# 3. "Plan a trip to Japan and create a travel guide PDF" → Pipeline: execution → research → worker → download link
```
