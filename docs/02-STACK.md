# 02 — Technology Stack

Every tool chosen for this project. Free tier confirmed where applicable.

---

## Backend

### Python 3.12+
- **Role:** Primary backend language
- **Cost:** Free, open source
- **Why:** Best ecosystem for AI/ML, LangGraph is Python-native, async support is mature

### FastAPI 0.115+
- **Role:** HTTP API server, SSE streaming endpoint, auth
- **Cost:** Free, open source (MIT)
- **Install:** `pip install fastapi uvicorn`
- **Why:** Async-native, auto-generates OpenAPI docs, fastest Python web framework for API work

### LangGraph 0.3+ (open-source library)
- **Role:** Multi-agent orchestration, state management, graph execution
- **Cost:** 100% free — MIT licensed
- **Install:** `pip install langgraph`
- **Docs:** https://langchain.com/langgraph
- **Why:** Purpose-built for stateful multi-agent workflows. Supervisor and swarm patterns built in. Native checkpointing to PostgreSQL.
- **⚠️ Important:** LangGraph the *library* is free. LangGraph *Platform* (their cloud hosting) is paid. We self-host — never use the Platform.

### LangGraph Swarm (v2 only)
- **Role:** Peer-to-peer agent handoffs in phase 2
- **Cost:** Free — part of the LangGraph library
- **Install:** `pip install langgraph-swarm`

### Anthropic Claude API
- **Role:** The LLM powering all agents
- **Cost:** **Paid — this is the main cost of the project**
  - claude-sonnet-4-20250514: ~$3 per million input tokens, ~$15 per million output tokens
  - For development: use claude-haiku-4-5-20251001 ($0.80/$4 per M tokens) to save cost
  - Estimated dev cost: $5–20/month depending on usage
- **Install:** `pip install anthropic`
- **Model to use:** `claude-sonnet-4-20250514` for production, `claude-haiku-4-5-20251001` for dev/testing

### Mem0 (open-source, self-hosted)
- **Role:** Persistent semantic memory layer for all agents
- **Cost:** Free — Apache 2.0 open-source, self-hosted
  - Cloud Platform free tier: 10K memories, 1K retrievals/month (enough for dev + early users)
  - Self-hosted: fully free, you manage the vector DB
- **Install:** `pip install mem0ai`
- **Strategy:** Use the self-hosted open-source version in development. Vector backend: Chroma (also free). Upgrade to hosted tier if you hit limits.
- **Why not cloud Mem0?** The $249/month Pro tier for graph memory is too expensive for a student project. Self-hosted with Chroma gives you vector memory for free.

### Chroma (vector database for self-hosted Mem0)
- **Role:** Vector storage backend for Mem0's semantic memory
- **Cost:** Free, open source (Apache 2.0)
- **Install:** `pip install chromadb`
- **Why:** Simplest to self-host, zero config, works out of the box with Mem0

### PostgreSQL 16+
- **Role:** Structured data — users, tasks, goals, check-ins, logs, session state, LangGraph checkpoints
- **Cost:** Free, open source
- **Local dev:** Docker (`docker run -e POSTGRES_PASSWORD=password -p 5432:5432 postgres`)
- **Production:** Neon.tech — generous free tier (0.5GB, no sleeping), or Supabase free tier

### Redis 7+
- **Role:** Session state cache, rate limiting
- **Cost:** Free, open source
- **Local dev:** Docker (`docker run -p 6379:6379 redis`)
- **Production:** Upstash free tier (10K commands/day) or Railway

### APScheduler 3.10+
- **Role:** Nightly background jobs (pattern learning, weekly review generation)
- **Cost:** Free, open source (MIT)
- **Install:** `pip install apscheduler`
- **Why:** Simple, reliable, integrates cleanly with FastAPI. No separate Celery infrastructure needed for v1.

### Tavily Search API
- **Role:** Web search for the Research Agent and Delegate Agent
- **Cost:** Free tier — 1,000 API credits/month
- **Sign up:** https://tavily.com
- **Install:** `pip install tavily-python`
- **Why:** Built specifically for LLM agents. Returns clean parsed text, not raw HTML. Has a LangChain/LangGraph integration built in.

### Python-dotenv
- **Role:** Environment variable management
- **Cost:** Free
- **Install:** `pip install python-dotenv`

---

## Frontend

### Next.js 15 (App Router)
- **Role:** Full frontend framework — pages, routing, API calls
- **Cost:** Free, open source (MIT)
- **Install:** `npx create-next-app@latest`
- **Why:** React server components, streaming support, excellent SSE handling, large community

### Tailwind CSS 4
- **Role:** Styling
- **Cost:** Free, open source (MIT)
- **Install:** bundled with Next.js setup

### shadcn/ui
- **Role:** Component library (cards, buttons, inputs, dialogs)
- **Cost:** Free, open source (MIT)
- **Install:** `npx shadcn@latest init`
- **Why:** Beautiful, accessible, copy-paste components. No runtime library — just code you own.

### Zustand
- **Role:** Client-side state management (current session, agent status, task queue)
- **Cost:** Free, open source (MIT)
- **Install:** `npm install zustand`

### React Query (TanStack Query)
- **Role:** Server state, data fetching, cache invalidation
- **Cost:** Free, open source (MIT)
- **Install:** `npm install @tanstack/react-query`

---

## Infrastructure (Local Development — all free)

### Docker + Docker Compose
- **Role:** Run PostgreSQL, Redis, and Chroma locally
- **Cost:** Free for local development
- **docker-compose.yml** provisions all infrastructure with one command

### Uvicorn
- **Role:** ASGI server for FastAPI
- **Cost:** Free
- **Install:** `pip install uvicorn[standard]`

---

## Infrastructure (Production — free tiers)

| Service | What for | Free tier |
|---|---|---|
| **Neon.tech** | PostgreSQL hosting | 0.5GB, no sleeping, 1 project |
| **Upstash** | Redis hosting | 10K commands/day |
| **Railway** | Backend (FastAPI) hosting | $5 credit/month (covers small usage) |
| **Vercel** | Frontend (Next.js) hosting | Unlimited hobby deployments |
| **Fly.io** | Alternative backend hosting | 3 shared VMs free |

**Realistic production cost estimate (small scale, <50 users):**
- Anthropic API: $10–30/month (main cost — use Haiku for non-critical agents)
- Neon: Free
- Upstash: Free
- Railway: ~$5/month or free if under limits
- Vercel: Free
- Mem0 self-hosted: Free
- **Total: ~$10–35/month** — affordable as a student project

---

## What Is NOT Used (and why)

| Tool | Why excluded |
|---|---|
| **LangGraph Platform (paid)** | $39+/user/month — use the free library + self-host instead |
| **Pinecone** | Paid vector DB — Chroma is free and sufficient |
| **OpenAI** | Claude is better for nuanced personal coaching responses |
| **Celery** | Heavy task queue — APScheduler is simpler for nightly jobs |
| **Django** | Too heavy for a pure API backend |
| **Prisma** | JavaScript ORM — we're Python backend, use SQLAlchemy |
| **Mem0 Cloud Pro ($249/mo)** | Graph memory is the premium feature — we work around it with manual relationship tracking in PostgreSQL |

---

## Full Dependency List

### Backend (`requirements.txt`)
```
fastapi==0.115.0
uvicorn[standard]==0.30.0
langgraph==0.3.0
langgraph-swarm==0.0.7
anthropic==0.40.0
mem0ai==0.1.0
chromadb==0.5.0
sqlalchemy==2.0.0
asyncpg==0.29.0
alembic==1.13.0
redis==5.0.0
apscheduler==3.10.0
tavily-python==0.5.0
python-dotenv==1.0.0
python-jose==3.3.0
passlib==1.7.4
httpx==0.27.0
pydantic==2.8.0
```

### Frontend (`package.json` key deps)
```json
{
  "dependencies": {
    "next": "15.0.0",
    "react": "19.0.0",
    "react-dom": "19.0.0",
    "@tanstack/react-query": "^5.0.0",
    "zustand": "^5.0.0",
    "tailwindcss": "^4.0.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.0.0",
    "lucide-react": "^0.400.0"
  }
}
```
