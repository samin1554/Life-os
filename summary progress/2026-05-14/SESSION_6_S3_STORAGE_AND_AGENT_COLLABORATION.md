# Life OS — Session 6: S3 Storage, Agent Collaboration, Insights & Weekly Review (2026-05-14)

## Overview

This session delivered five major features:
1. **S3-compatible cloud file storage** — files upload to Cloudflare R2 (or any S3-compatible bucket) in production, with local filesystem fallback for dev.
2. **Inter-agent collaboration** — agents are now aware of each other's capabilities and proactively suggest handoffs via clickable buttons in the chat UI.
3. **Insights dashboard** — full analytics page with interactive Nivo charts (vitals timeline, task velocity, category breakdown, goal progress, discovered patterns).
4. **Weekly Review page** — AI-generated weekly summary with stats grid and regenerate functionality.
5. **Demo data seeder** — script to populate 30 days of realistic checkins, tasks, and goals for testing.

---

## Feature 1: S3-Compatible Cloud Storage

### Problem

Generated files (xlsx, docx, pdf, chart PNGs) were stored on the local filesystem at `backend/generated_files/`. This fails in production (Railway) because container filesystems are ephemeral — files are lost on redeploy, and `FileResponse` can't serve them.

### Solution

Added a `FileStorage` class that uses boto3 for S3-compatible providers (Cloudflare R2, AWS S3, MinIO). Falls back to local filesystem when no S3 config is set.

### How It Works

- **Dev (no S3 config):** Everything works exactly as before — local filesystem, `FileResponse`
- **Production (with S3 env vars):** Files upload to S3 after generation -> downloads redirect to presigned URLs (1hr expiry) -> no bandwidth through backend

### Key Design Decisions

1. **Local fallback** — when `S3_BUCKET_NAME` is empty, storage falls back to local filesystem. Zero config for dev.
2. **Presigned URL redirects** — instead of proxying file content, redirect to time-limited S3 URLs. Frontend `downloadFile()` follows redirects automatically.
3. **S3 key = `{user_id}/{filename}`** — namespaced per user.
4. **boto3 sync + asyncio.to_thread** — prevents blocking the async event loop.

### Files Modified

| File | Change |
|------|--------|
| `backend/core/storage.py` | **NEW** — `FileStorage` class with upload, download URL, delete, exists methods |
| `backend/core/config.py` | Added 5 S3 env vars (bucket, endpoint, keys, region) |
| `backend/agents/worker.py` | Uploads to S3 after file generation, cleans up local temp files |
| `backend/routers/files.py` | Download endpoints redirect to presigned URLs; delete removes from S3 |
| `backend/requirements.txt` | Added `boto3>=1.34.0` |

### Setup (Cloudflare R2)

```
S3_BUCKET_NAME=lifeos-files
S3_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com
S3_ACCESS_KEY_ID=<from R2 API token>
S3_SECRET_ACCESS_KEY=<from R2 API token>
S3_REGION=auto
```

---

## Feature 2: Worker Agent — Charts Always Embedded

### Problem

The Worker Agent could return standalone chart PNGs as final output. Users expected charts to always be inside documents.

### Fix

- Updated system prompt with rules 6 and 7: "NEVER return a standalone chart image. Charts MUST always be embedded inside a document."
- Marked `generate_chart` as "INTERMEDIATE STEP ONLY" in the tool list
- File selection logic now only tracks documents (docx/xlsx/pdf), never standalone chart PNGs
- Intermediate chart PNGs are cleaned up from disk after being embedded in the document

---

## Feature 3: Inter-Agent Collaboration & Suggested Actions

### Problem

Agents worked in isolation — they didn't know about each other's capabilities and couldn't suggest handoffs. The user wanted a collaborative coaching system where agents chain together naturally.

### Solution

Agents now include a collaboration section in their system prompts (via `get_collaboration_prompt()`) listing what other agents can do. When an agent identifies a useful next step, it outputs `suggested_actions` — structured data that renders as clickable buttons in the chat UI.

### How It Works

1. Each agent's system prompt includes a section listing other agents' capabilities
2. The LLM decides when to suggest handoffs based on data maturity (e.g., 7+ check-ins)
3. Suggestions are appended as a JSON block at the end of the response
4. `extract_suggested_actions()` parses and strips the JSON from the displayed text
5. Actions flow through `runner.py` -> `chat.py` -> `ChatResponse` -> frontend
6. Frontend renders color-coded buttons below the message
7. Clicking a button calls `sendMessage()` — the supervisor routes it normally

### Example Flow

```
User checks in for 8 days, then asks "How am I sleeping?"
-> Health agent analyzes 8 checkins, finds avg 5.8h sleep
-> Response: "Your sleep averages 5.8h..." + buttons:
   [Research sleep strategies] [Create sleep tracking report]
-> User clicks [Research sleep strategies]
-> Supervisor routes to Research agent -> web search -> findings
-> Research response shows findings + existing [Export as PDF] button
-> User clicks [Export as PDF]
-> Supervisor routes to Worker agent -> creates PDF
-> Download button appears. Three-agent chain complete.
```

### Key Design Decisions

1. **Suggestions are just new chat messages** — clicking a button calls `sendMessage()` with a pre-written message. The supervisor routes it normally. No new API endpoints, no agent-to-agent protocol.
2. **LLM decides when to suggest** — data maturity signals (checkin count, date range) help the LLM decide, but no hard-coded triggers.
3. **No DB migrations** — uses existing `extra_metadata` JSONB field on `AgentInteraction`.
4. **Frontend reuses existing pattern** — same approach as the "Export as Spreadsheet" / "Export as PDF" buttons that already exist for research results.

### Files Modified

| File | Change |
|------|--------|
| `backend/agents/registry.py` | **NEW** — Agent capabilities registry + `get_collaboration_prompt()` |
| `backend/agents/shared.py` | Added `extract_suggested_actions()` parser |
| `backend/schemas/chat.py` | Added `SuggestedAction` model, extended `ChatResponse` |
| `backend/agents/health.py` | Collaboration prompt, data maturity signal, suggested actions output |
| `backend/agents/focus.py` | Collaboration prompt + suggested actions output |
| `backend/agents/goals.py` | Collaboration prompt + suggested actions output |
| `backend/agents/relationships.py` | Collaboration prompt + suggested actions output |
| `backend/agents/runner.py` | Stores `suggested_actions` in `extra_metadata` |
| `backend/routers/chat.py` | Extracts + passes `suggested_actions` to response |
| `frontend/types/index.ts` | Added `SuggestedAction` interface + field on `ChatMessage` |
| `frontend/hooks/useChat.ts` | Passes `suggested_actions` from API response |
| `frontend/app/(app)/chat/page.tsx` | Renders suggestion buttons with agent-colored styling |

---

## Agents with Collaboration Awareness

| Agent | Can Suggest |
|-------|------------|
| **Health** | Research (find strategies for patterns), Worker (create tracking reports), Focus (energy-based planning) |
| **Focus** | Goals (align tasks to goals), Health (energy patterns), Worker (create daily plan documents) |
| **Goals** | Focus (break goals into tasks), Research (find resources), Worker (create goal tracking documents) |
| **Relationships** | Execution (draft messages), Research (find gift ideas, activity suggestions) |

Research and Worker are "terminal" agents — they produce output but don't typically suggest further handoffs.

---

## Build & Test Status

- **Backend:** 91/91 tests passing
- **Frontend:** Build passes, 0 errors
- **No database migrations required**
- **No breaking changes** — all features are additive

---

## How to Verify

```bash
# Backend tests
cd backend && python3 -m pytest tests/ -v

# Frontend build
cd frontend && npm run build
```

**Test S3 storage:**
1. Without S3 config: generate a file via chat -> downloads work as before (local FileResponse)
2. With S3 config: generate a file -> uploaded to R2 -> download redirects to presigned URL

**Test inter-agent collaboration:**
1. Check in 7+ times over several days
2. Ask "How am I sleeping?" or "How's my health?"
3. Health agent should show suggestion buttons below its response
4. Click a suggestion -> supervisor routes to the suggested agent
5. Chain continues naturally (research -> export -> download)

**Test chart embedding:**
1. Ask "Make a bar chart of sales data: East $500, West $300, North $200"
2. Worker should create a PDF/docx with the chart embedded, not return a standalone PNG

---

## Feature 4: Insights Dashboard

### What It Does

A full analytics page at `/insights` showing interactive charts and discovered patterns from the user's data.

### Backend — `GET /dashboard/insights`

New endpoint in `backend/routers/dashboard.py` that aggregates:
- **Vitals time-series** — daily mood, energy, sleep scores from all check-ins
- **Task velocity** — daily created vs. completed tasks
- **Category breakdown** — task distribution by category
- **Goal progress** — active goals with progress percentages
- **Pattern insights** — computed metrics from `user_patterns` table (time estimation bias, completion rate, mood-sleep correlation, check-in streak, avoidance categories)
- **Weekly averages** — 7-day mood, energy, sleep averages

### Frontend — `/insights` page

Built with **Nivo** charting library (4 chart types):

| Chart | Type | Data |
|-------|------|------|
| Vitals Timeline | `ResponsiveLine` | 30-day mood/energy/sleep trends |
| Task Velocity | `ResponsiveBar` | Daily completed vs. pending tasks |
| Task Categories | `ResponsivePie` | Category distribution (donut chart) |
| Goal Progress | `ResponsiveRadialBar` | Active goals with % completion |

Plus a **Discovered Patterns** card showing computed insights: time estimation bias, completion rate, mood-sleep correlation strength, check-in streak, and avoidance categories.

All charts use the cyberpunk theme (dark background, neon colors, JetBrains Mono font).

### Files

| File | Change |
|------|--------|
| `backend/routers/dashboard.py` | Added `GET /dashboard/insights` endpoint |
| `frontend/app/(app)/insights/page.tsx` | **NEW** — Full insights page with 4 Nivo charts + pattern cards |

---

## Feature 5: Weekly Review Page

### What It Does

An AI-generated weekly review at `/weekly-review` summarizing the user's week with stats and coaching insights.

### Backend — `GET/POST /dashboard/weekly-review`

Two endpoints in `backend/routers/dashboard.py`:
- `GET` — fetches the current weekly review (calls `run_weekly_review()`)
- `POST` — force regenerates the review

Returns: `{review: string, stats: WeeklyStats, generated_at: string}`

### Frontend — `/weekly-review` page

- **Stats grid** — 6 metric cards (check-ins, completed tasks, pending tasks, avg mood, avg energy, exercise days)
- **Review text** — AI-generated weekly summary displayed in a CyberCard
- **Regenerate button** — force regenerate the review with loading state
- Empty state with "Generate Review" CTA when no review exists yet

### Files

| File | Change |
|------|--------|
| `backend/routers/dashboard.py` | Added `GET/POST /dashboard/weekly-review` endpoints |
| `frontend/app/(app)/weekly-review/page.tsx` | **NEW** — Weekly review page with stats grid + AI review text |

---

## Feature 6: Demo Data Seeder

### What It Does

Script at `backend/seed_demo_data.py` that generates 30 days of realistic, correlated demo data for testing the Insights and Weekly Review pages.

### Data Generated

- **~25 check-ins** (30 days with some skipped) — mood, energy, sleep, stress, exercise with realistic correlations (good sleep → better mood/energy)
- **25 tasks** — across 5 categories (work, health, personal, finance, learning) with varied statuses, priorities, time estimates, and deferral counts
- **4 goals** — Get fit (35%), Learn Spanish (15%), Save $10K (60%), Launch side project (10%)
- **Pattern learning** — runs `run_pattern_learning()` to compute user patterns from seeded data

### Usage

```bash
cd backend && python seed_demo_data.py
```

### Files

| File | Change |
|------|--------|
| `backend/seed_demo_data.py` | **NEW** — Demo data seeder script |

---

## Feature 7: Navigation Updates

### Sidebar

Added two new nav items to `frontend/components/layout/sidebar.tsx`:
- **Insights** (`/insights`) with `BarChart3` icon
- **Weekly Review** (`/weekly-review`) with `CalendarDays` icon

### Other Fixes

- `backend/core/storage.py` — Made `boto3` import optional with try/except fallback, so the app doesn't crash if boto3 isn't installed (graceful degradation to local storage)

---

## Complete File Inventory (Session 6)

### New Files

| File | Purpose |
|------|---------|
| `backend/core/storage.py` | S3-compatible file storage with local fallback |
| `backend/agents/registry.py` | Agent capabilities registry for inter-agent collaboration |
| `backend/seed_demo_data.py` | Demo data seeder (30 days of checkins, tasks, goals) |
| `frontend/app/(app)/insights/page.tsx` | Insights analytics dashboard with Nivo charts |
| `frontend/app/(app)/weekly-review/page.tsx` | AI-generated weekly review page |

### Modified Files

| File | Change |
|------|--------|
| `backend/core/config.py` | S3 env vars |
| `backend/agents/worker.py` | S3 upload, chart embedding rules, temp file cleanup |
| `backend/agents/health.py` | Collaboration prompt + suggested actions |
| `backend/agents/focus.py` | Collaboration prompt + suggested actions |
| `backend/agents/goals.py` | Collaboration prompt + suggested actions |
| `backend/agents/relationships.py` | Collaboration prompt + suggested actions |
| `backend/agents/shared.py` | `extract_suggested_actions()` parser |
| `backend/agents/runner.py` | Store suggested_actions in extra_metadata |
| `backend/routers/files.py` | Presigned URL redirects, S3 delete |
| `backend/routers/chat.py` | Pass suggested_actions to response |
| `backend/routers/dashboard.py` | Insights + weekly review endpoints |
| `backend/schemas/chat.py` | SuggestedAction model |
| `backend/requirements.txt` | Added boto3 |
| `frontend/types/index.ts` | SuggestedAction + ChatMessage update |
| `frontend/hooks/useChat.ts` | Pass suggested_actions |
| `frontend/app/(app)/chat/page.tsx` | Suggestion buttons UI |
| `frontend/components/layout/sidebar.tsx` | Insights + Weekly Review nav links |
