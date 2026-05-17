# 03 — Costs & Free Tiers

A complete, honest breakdown of what is free, what costs money, and how to keep costs near zero while building.

---

## TL;DR

**Development cost: ~$0–5/month**
**Production cost (small scale): ~$10–35/month**
**The only unavoidable cost: Anthropic API usage**

---

## Free Forever (No Limits That Matter for a Student Project)

| Tool | License | Notes |
|---|---|---|
| LangGraph (library) | MIT | 100% free. Only their cloud *Platform* costs money |
| FastAPI | MIT | Free |
| Next.js | MIT | Free |
| Tailwind CSS | MIT | Free |
| shadcn/ui | MIT | Free |
| PostgreSQL | PostgreSQL License | Free |
| Redis | BSD 3-Clause | Free |
| Chroma | Apache 2.0 | Free vector DB, self-hosted |
| Mem0 (open-source) | Apache 2.0 | Free self-hosted. Requires you to run your own infra |
| Python | PSF License | Free |
| APScheduler | MIT | Free |
| Docker | Apache 2.0 (Community) | Free for personal use |
| Zustand | MIT | Free |
| React Query | MIT | Free |

---

## Free Tiers (Limited but Sufficient for Development)

| Tool | Free Tier | When You'll Hit the Limit |
|---|---|---|
| **Tavily Search** | 1,000 API credits/month | ~1,000 web searches. Plenty for dev. In prod, each Delegate Agent or Research Agent call uses 1 credit. |
| **Mem0 Cloud** | 10K memories, 1K retrievals/month | Sufficient for dev and early users. With self-hosted Mem0 + Chroma, this limit doesn't apply at all. |
| **Neon.tech (PostgreSQL)** | 0.5GB storage, 1 project, no cold starts | Enough for hundreds of users at launch |
| **Upstash (Redis)** | 10,000 commands/day | Sufficient for small scale |
| **Vercel (Frontend)** | Unlimited hobby deployments | Never a problem for a side project |
| **LangSmith** | 5,000 traces/month | For debugging agent runs. Plenty for dev. |
| **Railway (Backend)** | $5 credit/month | Covers ~500 hours of a small VM |

---

## Paid (No Free Tier — Budget Required)

### Anthropic Claude API ⚠️ Main Cost

This is the only real expense. Every agent call costs tokens.

| Model | Input tokens | Output tokens | Best for |
|---|---|---|---|
| `claude-haiku-4-5-20251001` | $0.80 / 1M | $4.00 / 1M | Dev, testing, simple agents |
| `claude-sonnet-4-20250514` | $3.00 / 1M | $15.00 / 1M | Production, complex reasoning |

**Cost estimation per user session:**

A typical morning check-in (user inputs 100 words → supervisor routes → 2 domain agents → synthesis → response of ~300 words):
- Rough token usage: ~2,000 input + ~500 output
- Cost at Haiku: `(2000 × $0.0000008) + (500 × $0.000004)` = **~$0.0036 per session** (~$0.004)
- Cost at Sonnet: ~$0.014 per session

**Monthly cost estimates:**

| Users | Sessions/day | Model | Monthly cost |
|---|---|---|---|
| 1 (you, dev) | 3 | Haiku | ~$0.36 |
| 1 (you, dev) | 3 | Sonnet | ~$1.26 |
| 10 beta users | 3 each | Mixed | ~$5–15 |
| 50 users | 3 each | Mixed | ~$25–75 |

**Cost control strategy:**
- Use `claude-haiku-4-5-20251001` for: routing, simple check-ins, pattern learning background jobs
- Use `claude-sonnet-4-20250514` for: execution agent (writing emails/docs), synthesis, complex coaching responses
- Cache common patterns — don't re-run the full agent graph for identical inputs

**How to get started free:**
- Anthropic gives $5 free credit on signup — enough for weeks of development

---

## Self-Hosted vs Cloud: Memory Layer Decision

This is the most important cost decision in the stack.

### Option A: Self-hosted Mem0 + Chroma (Recommended for Student)
- **Cost:** $0
- **Setup:** Run Chroma in Docker locally. `pip install mem0ai chromadb`. Point Mem0 at your local Chroma instance.
- **Downside:** You manage the infrastructure. In production, you need Chroma running on your server.
- **Production cost:** Included in your server cost (e.g., Railway or Fly.io VM)

### Option B: Mem0 Cloud (Free Hobby Tier)
- **Cost:** Free up to 10K memories, 1K retrievals/month
- **Setup:** Sign up at mem0.ai, get API key, use `MemoryClient` instead of `Memory`
- **Downside:** 1K retrieval calls/month is limiting if you have active users (each agent run retrieves memories)
- **Upgrade cost:** $19/month for 50K memories (graph memory still paywalled at $249/month)

**Recommendation:** Start with self-hosted Mem0 + Chroma. It's free, you learn the stack, and you're not dependent on their service.

---

## Production Infrastructure Budget

This is a realistic budget for running Life OS at small scale (~50 users):

```
Anthropic API (Haiku + Sonnet mix):    $15–30/month
Railway (FastAPI + Chroma + Redis):    $5–10/month
Neon.tech (PostgreSQL):                $0 (free tier)
Vercel (Next.js):                      $0 (free tier)
Tavily (1K free, then $20/month):      $0 (free tier sufficient early on)
Domain name:                           $10–15/year

TOTAL: ~$20–45/month
```

This is sustainable on a student budget. Once you have paying users, charge $9/month — you break even at 3 users.

---

## What NOT to Pay For

| Service | Why to avoid |
|---|---|
| **LangGraph Platform** | $39+/user/month. Use the free library and self-host. |
| **Mem0 Pro ($249/mo)** | Graph memory is the killer feature but it's paywalled. For v1, vector memory is sufficient. |
| **Pinecone** | Free tier is limited and Chroma is equivalent for our scale. |
| **OpenAI** | Claude is better for nuanced personal coaching. OpenAI has no advantage here. |
| **AWS/GCP/Azure** | Overkill. Railway and Fly.io are cheaper and simpler at small scale. |

---

## Environment Variables Required

```bash
# .env file

# Anthropic (required)
ANTHROPIC_API_KEY=sk-ant-...

# Database (required)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/lifeos

# Redis (required)
REDIS_URL=redis://localhost:6379

# Tavily (required for research/delegate agents)
TAVILY_API_KEY=tvly-...

# Mem0 (only if using cloud — skip for self-hosted)
MEM0_API_KEY=m0-...

# Auth
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# App
ENVIRONMENT=development
DEBUG=true
```
