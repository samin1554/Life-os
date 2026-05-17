# Life OS — AI Life Coach & Executive Function System

> A multi-agent AI system that doesn't just advise you — it acts for you.
> Built for people who struggle with executive function, time blindness, task avoidance, and the chaos of modern life.

---

## What This Is

Life OS is a full-stack agentic application. A swarm of specialised AI agents learns your behavioural patterns across every life domain — sleep, focus, health, relationships, goals, admin — and then actively handles the tasks you keep avoiding: writing the email, structuring the spreadsheet, building a realistic daily plan based on your *actual* pace (not your optimistic one), and collapsing overwhelming days into exactly 3 things.

The core insight: every existing productivity tool tells you what to do. This one does it.

---

## The Problem It Solves

Most people struggle not with knowing *what* to do, but with *starting* it. This is executive dysfunction — the gap between intention and action. It affects:

- People with ADHD or attention difficulties
- Anyone under chronic stress or cognitive overload
- Students, founders, and anyone juggling too many open loops
- Normal humans on bad days (which is everyone, regularly)

Specifically for the builder of this project, the pain points are:
- Avoidance of low-reward tasks (emails, spreadsheets, forms)
- Unrealistic time planning — building plans for an ideal self
- Managing chaos when multiple things demand attention simultaneously
- Lacking a system that sees the whole picture at once

---

## What Makes This Different From Existing Apps

| Feature | Existing apps | Life OS |
|---|---|---|
| Task management | ✅ Most have it | ✅ |
| Reminders | ✅ Most have it | ✅ |
| Emotional support | Some (Pi.ai) | ✅ |
| Cross-domain synthesis | ❌ None | ✅ |
| Executes tasks for you | ❌ None | ✅ |
| Learns your real pace | ❌ None | ✅ |
| Persistent memory of who you are | ❌ None | ✅ |
| Chaos triage (everything → 3 things) | ❌ None | ✅ |

---

## Repository Structure

```
life-os/
├── README.md                    ← You are here
├── docs/
│   ├── 01-ARCHITECTURE.md       ← Full system architecture
│   ├── 02-STACK.md              ← Every tool, library, and why it was chosen
│   ├── 03-COSTS.md              ← Free tiers, what costs money, dev vs prod
│   ├── 04-AGENTS.md             ← Every agent: role, tools, memory access, prompts
│   ├── 05-MEMORY.md             ← Memory architecture, learning layers, schema
│   ├── 06-DATABASE.md           ← Full DB schema, all tables, relationships
│   ├── 07-API.md                ← All FastAPI routes, request/response shapes
│   ├── 08-FRONTEND.md           ← Next.js structure, pages, components, SSE
│   ├── 09-BUILD-PHASES.md       ← Phase 1/2/3 with exact tasks and order
│   └── 10-ONBOARDING-FLOW.md   ← Onboarding agent conversation design
├── backend/
│   ├── main.py
│   ├── agents/
│   ├── memory/
│   ├── routers/
│   ├── models/
│   ├── scheduler/
│   └── tools/
└── frontend/
    ├── app/
    ├── components/
    └── lib/
```

---

## Quick Start for Claude Code

When handing this to a coding agent, give it this README plus the specific doc for the component you want built. Suggested order:

1. Read `02-STACK.md` first — understand every tool
2. Read `03-COSTS.md` — confirm what is free vs paid
3. Read `01-ARCHITECTURE.md` — understand the whole system
4. Read `05-MEMORY.md` and `06-DATABASE.md` — build data layer first
5. Read `04-AGENTS.md` — build agents second
6. Read `07-API.md` and `08-FRONTEND.md` — build the interface last

---

## The One Rule for Claude Code

**Always build the memory layer before the agents. Always build the agents before the UI.**
The entire system depends on the memory schema being correct. Changing it later breaks everything.
