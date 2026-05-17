# 07 — API Routes

All FastAPI endpoints. Every route, method, request body, and response shape.

---

## Base URL
```
Development: http://localhost:8000
Production:  https://your-app.railway.app
```

## Authentication
All routes except `/auth/*` and `/health` require a JWT Bearer token:
```
Authorization: Bearer <token>
```

---

## Auth Routes

### POST /auth/register
```json
// Request
{
  "email": "sam@example.com",
  "password": "securepassword",
  "name": "Sam"
}

// Response 201
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user_id": "uuid",
  "onboarding_complete": false
}
```

### POST /auth/login
```json
// Request
{
  "email": "sam@example.com",
  "password": "securepassword"
}

// Response 200
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user_id": "uuid",
  "onboarding_complete": true
}
```

---

## Onboarding Routes

### GET /onboarding/status
```json
// Response 200
{
  "complete": false,
  "step": 3,
  "total_steps": 10
}
```

### POST /onboarding/start
Initialises onboarding session. Returns first question from onboarding agent.
```json
// Response 200
{
  "session_id": "uuid",
  "message": "Hi! I'm really glad you're here. Before I can help you properly, I'd love to get to know you a little. What's your name, and what made you decide to try Life OS today?"
}
```

### POST /onboarding/message
Send user's response, receive next question.
```json
// Request
{
  "session_id": "uuid",
  "message": "I'm Sam. I've been struggling to stay on top of everything — I have ADHD and I keep avoiding the simple stuff."
}

// Response 200 — streaming (SSE)
// Agent response streams token by token
// Final event: {"type": "done", "step": 4, "complete": false}
```

---

## Chat Routes (Core Agent Interaction)

### POST /chat
Main agent interaction endpoint. Streams response via SSE.

```json
// Request
{
  "message": "I have 12 things to do today and I don't know where to start",
  "session_id": "uuid"    // optional, creates new if omitted
}

// Response: SSE stream
// Each event:
data: {"type": "agent_start", "agent": "chaos_triage"}
data: {"type": "token", "content": "Okay"}
data: {"type": "token", "content": ". Let's"}
data: {"type": "token", "content": " cut this down."}
data: {"type": "agent_end", "agent": "chaos_triage"}
data: {"type": "agent_start", "agent": "synthesis"}
data: {"type": "token", "content": "Here are your 3 things for today:"}
// ...
data: {"type": "done", "session_id": "uuid"}
```

**Frontend SSE consumer pattern (Next.js):**
```typescript
const response = await fetch('/api/chat', {
  method: 'POST',
  body: JSON.stringify({ message }),
  headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }
});

const reader = response.body?.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const chunk = decoder.decode(value);
  // parse SSE events and update UI
}
```

---

## Check-in Routes

### POST /checkin/morning
```json
// Request
{
  "mood_score": 3,
  "energy_score": 2,
  "sleep_hours": 6.5,
  "sleep_quality": 3,
  "notes": "Feeling a bit foggy, big presentation today"
}

// Response: SSE stream
// Health agent + Focus agent run in parallel
// Synthesis produces morning briefing with daily plan
```

### POST /checkin/evening
```json
// Request
{
  "mood_score": 4,
  "energy_score": 3,
  "tasks_completed": 3,
  "tasks_planned": 5,
  "wins": ["Finished the presentation", "Called my sister"],
  "struggles": ["Didn't get to email"],
  "notes": "Ran out of energy around 3pm"
}

// Response 200
{
  "message": "Good job today. You completed 3 of 5 planned tasks...",
  "deferred_tasks": ["Email to Dr Johnson", "Update expense report"],
  "tomorrow_preview": "Tomorrow looks lighter — 4 tasks, first at 10am."
}
```

### GET /checkin/history
```json
// Query params: ?days=7
// Response 200
{
  "checkins": [
    {
      "date": "2026-01-15",
      "morning": { "mood_score": 3, "energy_score": 2, "sleep_hours": 6.5 },
      "evening": { "mood_score": 4, "tasks_completed": 3, "tasks_planned": 5 }
    }
  ],
  "averages": {
    "mood": 3.4,
    "energy": 3.1,
    "completion_rate": 0.68
  }
}
```

---

## Task Routes

### GET /tasks
```json
// Query params: ?status=pending&date=today
// Response 200
{
  "tasks": [
    {
      "id": "uuid",
      "title": "Email Dr Johnson about appointment",
      "category": "email",
      "priority": 1,
      "status": "pending",
      "estimated_minutes": 15,
      "times_deferred": 3,
      "scheduled_for": "2026-01-15T10:00:00Z"
    }
  ],
  "total": 7,
  "today_plan": ["uuid1", "uuid2", "uuid3"]  // ordered list for today
}
```

### POST /tasks
```json
// Request
{
  "title": "Update Q1 budget spreadsheet",
  "category": "admin",
  "estimated_minutes": 45,
  "due_date": "2026-01-20"
}

// Response 201
{
  "id": "uuid",
  "title": "Update Q1 budget spreadsheet",
  "status": "pending",
  "agent_note": "This one keeps getting deferred — want me to handle it for you?"
}
```

### PATCH /tasks/{id}
```json
// Request (any subset of fields)
{
  "status": "done",
  "actual_minutes": 62
}

// Response 200
{
  "id": "uuid",
  "status": "done",
  "pattern_note": "You estimated 45 min, took 62 min (38% over). Noted for future planning."
}
```

### POST /tasks/{id}/execute
Ask the Execution Agent to draft the output for a task (email, document, etc.)
```json
// Request
{
  "context": "Email to Dr Johnson asking to reschedule next week's appointment to any time Thursday"
}

// Response: SSE stream from Execution Agent
// Final event includes: {"type": "execution_ready", "output": "Dear Dr Johnson..."}
```

---

## Goals Routes

### GET /goals
```json
// Response 200
{
  "goals": [
    {
      "id": "uuid",
      "title": "Learn guitar",
      "domain": "learning",
      "progress_pct": 15,
      "last_action_at": "2026-01-08T20:00:00Z",
      "drift_alert": true,    // no action in 7+ days
      "next_milestone": "Complete 10 beginner songs"
    }
  ]
}
```

### POST /goals
```json
// Request
{
  "title": "Run a 5K",
  "domain": "health",
  "why": "I want to feel more energetic and prove I can do it",
  "timeframe": "this_year"
}

// Response 201 — Goals agent creates milestones
{
  "id": "uuid",
  "milestones": [
    {"title": "Run 1K without stopping", "due": "2026-02-15"},
    {"title": "Run 3K", "due": "2026-03-15"},
    {"title": "Complete 5K", "due": "2026-04-30"}
  ]
}
```

---

## Memory Routes

### GET /memory
View your stored memories (privacy feature).
```json
// Response 200
{
  "memories": [
    {
      "id": "mem_abc",
      "content": "User's peak focus window is 10am to 12pm on weekdays",
      "source": "pattern_learned",
      "confidence": 0.84,
      "created_at": "2026-01-10"
    }
  ]
}
```

### DELETE /memory/{id}
User can delete any memory they don't want stored.
```json
// Response 200
{ "deleted": true }
```

### DELETE /memory/all
Nuclear option — delete everything.
```json
// Response 200
{ "deleted": true, "count": 127 }
```

---

## Dashboard Route

### GET /dashboard
Everything the frontend needs for the main dashboard in one call.
```json
// Response 200
{
  "today": {
    "date": "2026-01-15",
    "plan": [/* ordered task list for today */],
    "checkin_done": false,
    "energy_forecast": "medium",
    "peak_window": "10:00–12:00"
  },
  "streak": 7,
  "weekly_summary": { /* latest weekly review if available */ },
  "goals": [/* active goals with drift alerts */],
  "relationship_nudges": [/* people to reach out to */],
  "pattern_insights": [
    "You complete 40% more tasks when you sleep 7+ hours",
    "Your best work happens Tuesday mornings"
  ]
}
```

---

## Health Check

### GET /health
No auth required.
```json
// Response 200
{
  "status": "ok",
  "db": "connected",
  "memory": "connected",
  "version": "1.0.0"
}
```
