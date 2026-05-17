# Life OS — AI Life Coach & Executive Function System

An AI-powered personal life management system with multi-agent architecture. Life OS acts as your personal life coach — helping you plan your day, manage tasks, track goals, reflect on progress, and stay on track through intelligent AI agents that don't just advise you, they act for you.

**Live Demo**: [life-os-eta-hazel.vercel.app](https://life-os-eta-hazel.vercel.app)

---

## Architecture

```
Frontend (Next.js + Clerk Auth)
    ↓
Backend (FastAPI)
    ├── PostgreSQL (structured data)
    ├── Redis (caching, OAuth state)
    ├── ChromaDB (semantic memory)
    ├── Cloudflare R2 (file storage)
    └── User's own LLM API key (Groq/OpenRouter/OpenAI/etc)
```

**Zero server-side LLM keys** — users provide their own API keys through the Settings page. Keys are encrypted with Fernet and stored securely in the database.

---

## Features

- **AI Chat Coach** — conversational interface with full context of your tasks, goals, and habits
- **Multi-Agent System** — 12+ specialist agents dispatched automatically based on intent
- **Task Management** — smart task tracking with energy-level awareness and priority scoring
- **Goal Tracking** — long-term goal management with progress monitoring
- **Daily Check-ins** — mood and energy tracking with pattern analysis
- **Gmail Integration** — OAuth-based email drafting and management
- **File Generation** — create documents, spreadsheets, charts on demand
- **Weekly Reviews** — automated progress summaries and recommendations
- **Memory System** — ChromaDB-powered semantic memory for personalized coaching
- **Chaos Triage** — when everything is overwhelming, collapse your day into exactly 3 things

---

## Agent System

| Agent | Purpose |
|-------|---------|
| **Supervisor** | Classifies user intent, routes to specialist agents |
| **Focus** | Productivity coaching, time management, energy-based scheduling |
| **Health** | Wellness tracking, sleep patterns, stress management |
| **Goals** | Goal progress analysis, milestone tracking, recommendations |
| **Email** | Gmail integration — read, draft, and send emails via tools |
| **Research** | Web research with DuckDuckGo and Tavily |
| **Worker** | Generate documents (DOCX, XLSX, PDF, charts) |
| **Execution** | Task breakdown, step-by-step action plans |
| **Synthesis** | Combines multi-agent outputs into coherent responses |
| **Pattern Learning** | Learns behavioral patterns from check-in history |
| **Weekly Review** | Automated weekly progress summaries |
| **Chaos Triage** | Emergency mode — collapse overwhelm into 3 actions |

---

## Tech Stack

### Backend
| Technology | Purpose |
|-----------|---------|
| FastAPI | Async Python API framework |
| LangGraph | Multi-agent orchestration |
| SQLAlchemy | Async ORM with PostgreSQL |
| APScheduler | Background jobs (pattern learning, weekly reviews) |
| ChromaDB | Vector memory store |
| Redis | Caching, rate limiting, OAuth state |
| Cloudflare R2 | S3-compatible file storage |
| Clerk | JWT authentication |

### Frontend
| Technology | Purpose |
|-----------|---------|
| Next.js 14 | React framework (App Router) |
| Clerk | Authentication & user management |
| Tailwind CSS | Styling |
| Framer Motion | Animations |
| pnpm | Package manager |

### Infrastructure
| Service | Host |
|---------|------|
| Backend API | Railway |
| Frontend | Vercel |
| PostgreSQL | Railway |
| Redis | Railway |
| ChromaDB | Railway (Docker) |
| File Storage | Cloudflare R2 |
| Auth | Clerk |

---

## Supported LLM Providers

Users connect any OpenAI-compatible API provider in Settings:

| Provider | Default Model |
|----------|---------------|
| Groq | `llama-3.3-70b-versatile` |
| OpenRouter | `meta-llama/llama-3.3-70b-instruct` |
| OpenAI | `gpt-4o-mini` |
| Anthropic | `claude-sonnet-4-20250514` |
| Together | `Llama-3.3-70B-Instruct-Turbo` |
| Fireworks | `llama-v3p3-70b-instruct` |
| Mistral | `mistral-small-latest` |
| DeepSeek | `deepseek-chat` |
| Perplexity | `llama-3.1-sonar-small-128k-online` |

---

## Project Structure

```
├── backend/
│   ├── agents/          # AI agent implementations (12+ agents)
│   ├── core/            # Infrastructure (LLM, DB, auth, encryption, tools)
│   ├── routers/         # API route handlers
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic request/response schemas
│   ├── services/        # Business logic (email, notifications)
│   ├── alembic/         # Database migrations
│   ├── tests/           # Pytest test suite
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app/             # Next.js App Router pages
│   ├── components/      # React components (cyber UI theme)
│   ├── hooks/           # Custom React hooks
│   ├── lib/             # Utilities & API client
│   ├── types/           # TypeScript types
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml       # Local development
└── docker-compose.prod.yml  # Production (self-hosted)
```

---

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- pnpm

### Quick Start

1. **Start infrastructure:**
   ```bash
   docker-compose up -d
   ```
   This starts PostgreSQL, Redis, and ChromaDB.

2. **Backend:**
   ```bash
   cd backend
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env  # Edit with your Clerk keys
   alembic upgrade head
   uvicorn main:app --reload --port 8001
   ```

3. **Frontend:**
   ```bash
   cd frontend
   pnpm install
   # Create .env.local with:
   # NEXT_PUBLIC_API_URL=http://localhost:8001
   # NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
   # CLERK_SECRET_KEY=sk_test_...
   pnpm dev
   ```

4. **Add your LLM key** in the app's Settings page after signing up.

---

## Deployment

### Railway + Vercel (Recommended — ~$5/month)

**Backend (Railway):**
- Connect GitHub repo → root directory: `backend`
- Add PostgreSQL, Redis services
- Add ChromaDB as Docker image (`chromadb/chroma:latest`)
- Start command: `alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8001`
- Set environment variables (see `backend/.env.example`)

**Frontend (Vercel):**
- Connect GitHub repo → root directory: `frontend`
- Set `NEXT_PUBLIC_API_URL` to Railway backend URL
- Set Clerk keys

**Post-deploy:**
- Configure Clerk webhook → `https://backend-url/auth/webhook`
- Update `FRONTEND_URL` and `ALLOWED_ORIGINS` in Railway

### Self-Hosted (Docker Compose)

```bash
# Configure environment
cp backend/.env.example backend/.env
# Edit with production values

# Deploy
docker compose -f docker-compose.prod.yml up -d --build

# Run migrations
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

---

## Security

- Clerk JWT authentication on all protected endpoints
- Webhook signature verification (rejects unsigned payloads)
- OAuth state stored in Redis with 10-min TTL (prevents CSRF)
- Rate limiting on chat endpoint (15 req/min)
- Security headers (X-Frame-Options: DENY, HSTS, X-Content-Type-Options)
- CORS locked to frontend domain only
- File upload MIME type + extension whitelist
- User API keys encrypted with Fernet at rest
- No LLM API keys stored on server — users bring their own
- Production health endpoint returns minimal info

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat` | Send message to AI coach |
| GET | `/chat/history` | Get chat history by session |
| GET/POST | `/tasks` | Task CRUD |
| POST | `/checkin` | Daily check-in |
| GET/POST | `/goals` | Goal management |
| GET | `/dashboard/stats` | Dashboard statistics |
| POST | `/uploads` | File upload (PDF, DOCX, images) |
| GET | `/integrations/gmail/auth-url` | Start Gmail OAuth |
| GET | `/integrations/status` | Connected integrations |
| POST | `/agents/run` | Manual agent execution |
| GET | `/health` | Health check |

---

## License

Private project. All rights reserved.
