# 06 — Database Schema

Full PostgreSQL schema for Life OS. Every table, every column, every relationship.

---

## Setup

```bash
# Run PostgreSQL locally with Docker
docker run --name lifeos-db \
  -e POSTGRES_PASSWORD=lifeos \
  -e POSTGRES_DB=lifeos \
  -p 5432:5432 \
  -d postgres:16

# DATABASE_URL for .env
DATABASE_URL=postgresql+asyncpg://postgres:lifeos@localhost:5432/lifeos
```

---

## SQLAlchemy Models (Python)

### users

```python
class User(Base):
    __tablename__ = "users"

    id              = Column(UUID, primary_key=True, default=uuid4)
    email           = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    name            = Column(String, nullable=False)
    timezone        = Column(String, default="UTC")          # e.g. "America/Chicago"
    onboarding_done = Column(Boolean, default=False)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    profile         = relationship("UserProfile", back_populates="user", uselist=False)
    tasks           = relationship("Task", back_populates="user")
    checkins        = relationship("CheckIn", back_populates="user")
    goals           = relationship("Goal", back_populates="user")
```

### user_profiles

Structured profile data extracted from onboarding. Updated as the system learns more.

```python
class UserProfile(Base):
    __tablename__ = "user_profiles"

    id                   = Column(UUID, primary_key=True, default=uuid4)
    user_id              = Column(UUID, ForeignKey("users.id"), unique=True)

    # Identity
    occupation           = Column(String)
    life_focus_areas     = Column(ARRAY(String))    # ["focus", "health", "relationships"]

    # Energy patterns (updated by Pattern Learning Agent)
    typical_wake_time    = Column(Time)              # e.g. 07:30
    typical_sleep_time   = Column(Time)              # e.g. 23:00
    peak_energy_start    = Column(Time)              # learned: e.g. 10:00
    peak_energy_end      = Column(Time)              # learned: e.g. 12:00
    low_energy_windows   = Column(JSONB)             # [{"day": "monday", "time": "14:00-16:00"}]

    # Task patterns (updated by Pattern Learning Agent)
    time_estimation_bias = Column(Float, default=1.0)  # 1.35 = underestimates by 35%
    avg_tasks_completed  = Column(Float)               # rolling 14-day average
    avoidance_categories = Column(ARRAY(String))       # ["email", "admin", "phone calls"]

    # Preferences (from onboarding)
    communication_style  = Column(String)   # "direct" | "gentle" | "detailed" | "brief"
    coaching_tone        = Column(String)   # "encouraging" | "no-nonsense" | "reflective"

    # Meta
    updated_at           = Column(DateTime(timezone=True), onupdate=func.now())
```

### tasks

Every task the user has ever added, regardless of completion status.

```python
class Task(Base):
    __tablename__ = "tasks"

    id                  = Column(UUID, primary_key=True, default=uuid4)
    user_id             = Column(UUID, ForeignKey("users.id"), index=True)

    # Content
    title               = Column(String, nullable=False)
    description         = Column(Text)
    category            = Column(String)        # "email" | "admin" | "deep_work" | "personal" | "health"

    # Status
    status              = Column(String, default="pending")  # "pending" | "in_progress" | "done" | "deferred" | "deleted"
    priority            = Column(Integer, default=2)         # 1=urgent, 2=normal, 3=low

    # Scheduling
    due_date            = Column(Date)
    scheduled_for       = Column(DateTime(timezone=True))    # specific block on calendar

    # Time tracking (core for pattern learning)
    estimated_minutes   = Column(Integer)        # user's estimate
    actual_minutes      = Column(Integer)        # how long it actually took
    started_at          = Column(DateTime(timezone=True))
    completed_at        = Column(DateTime(timezone=True))

    # Avoidance tracking
    times_deferred      = Column(Integer, default=0)  # how many times pushed to "later"
    first_created_at    = Column(DateTime(timezone=True), server_default=func.now())

    # Execution agent output
    execution_output    = Column(Text)    # if agent drafted email/doc, stored here before approval

    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), onupdate=func.now())
```

### checkins

Daily morning and evening check-ins. Core data source for the Pattern Learning Agent.

```python
class CheckIn(Base):
    __tablename__ = "checkins"

    id              = Column(UUID, primary_key=True, default=uuid4)
    user_id         = Column(UUID, ForeignKey("users.id"), index=True)

    # Timing
    checkin_type    = Column(String)        # "morning" | "evening"
    checkin_date    = Column(Date, nullable=False)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    # Scores (1–5 scale)
    mood_score      = Column(Integer)       # 1=very low, 5=excellent
    energy_score    = Column(Integer)       # 1=exhausted, 5=peak
    stress_score    = Column(Integer)       # 1=none, 5=overwhelming
    focus_score     = Column(Integer)       # 1=scattered, 5=locked in

    # Physical
    sleep_hours     = Column(Float)         # hours slept last night
    sleep_quality   = Column(Integer)       # 1–5
    exercised       = Column(Boolean)

    # Context
    notes           = Column(Text)          # free text, what's on their mind
    wins            = Column(ARRAY(String)) # evening only: what went well
    struggles       = Column(ARRAY(String)) # evening only: what was hard

    # Tasks (evening only)
    tasks_planned   = Column(Integer)       # how many were planned this morning
    tasks_completed = Column(Integer)       # how many actually done
```

### goals

Long-term goals tracked by the Goals Agent.

```python
class Goal(Base):
    __tablename__ = "goals"

    id              = Column(UUID, primary_key=True, default=uuid4)
    user_id         = Column(UUID, ForeignKey("users.id"), index=True)

    # Content
    title           = Column(String, nullable=False)
    description     = Column(Text)
    why             = Column(Text)          # user's reason for this goal

    # Categorisation
    domain          = Column(String)        # "health" | "career" | "relationships" | "learning" | "personal"
    timeframe       = Column(String)        # "this_week" | "this_month" | "this_year" | "long_term"

    # Progress
    status          = Column(String, default="active")  # "active" | "completed" | "paused" | "abandoned"
    progress_pct    = Column(Integer, default=0)         # 0–100
    last_action_at  = Column(DateTime(timezone=True))    # when user last did something toward this goal

    # Milestones
    milestones      = Column(JSONB)         # [{"title": "...", "done": false, "due": "2026-02-01"}]

    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())
```

### relationships

Important people in the user's life, tracked by the Relationships Agent.

```python
class Relationship(Base):
    __tablename__ = "relationships"

    id                  = Column(UUID, primary_key=True, default=uuid4)
    user_id             = Column(UUID, ForeignKey("users.id"), index=True)

    # Identity
    name                = Column(String, nullable=False)
    relationship_type   = Column(String)    # "family" | "friend" | "partner" | "colleague" | "mentor"
    notes               = Column(Text)      # context from onboarding

    # Interaction tracking
    last_interacted_at  = Column(DateTime(timezone=True))
    interaction_frequency_days = Column(Integer)  # desired frequency, e.g. 14 = every 2 weeks
    times_nudged        = Column(Integer, default=0)  # how many times system has suggested reaching out

    created_at          = Column(DateTime(timezone=True), server_default=func.now())
```

### agent_interactions

Every agent response, what was suggested, and whether the user accepted it. Critical for learning what the user values.

```python
class AgentInteraction(Base):
    __tablename__ = "agent_interactions"

    id              = Column(UUID, primary_key=True, default=uuid4)
    user_id         = Column(UUID, ForeignKey("users.id"), index=True)

    # What happened
    agent_name      = Column(String)            # "focus" | "execution" | "chaos_triage" etc.
    input_summary   = Column(Text)              # brief summary of user input
    output_summary  = Column(Text)              # brief summary of agent output
    full_response   = Column(Text)              # complete agent response

    # User feedback
    accepted        = Column(Boolean)           # did user follow the suggestion?
    overridden      = Column(Boolean, default=False)  # did user explicitly reject it?
    override_note   = Column(Text)              # if overridden, what did they do instead?

    session_id      = Column(UUID)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
```

### user_patterns

Structured output from the Pattern Learning Agent. Updated nightly.

```python
class UserPattern(Base):
    __tablename__ = "user_patterns"

    id                          = Column(UUID, primary_key=True, default=uuid4)
    user_id                     = Column(UUID, ForeignKey("users.id"), unique=True)

    # Energy rhythms
    peak_days                   = Column(ARRAY(String))     # ["tuesday", "wednesday", "thursday"]
    low_days                    = Column(ARRAY(String))     # ["monday", "friday"]
    peak_hour_start             = Column(Integer)           # 10 (= 10:00)
    peak_hour_end               = Column(Integer)           # 12 (= 12:00)

    # Task patterns
    time_estimation_bias        = Column(Float)             # 1.35 = underestimates by 35%
    avg_completion_rate_7d      = Column(Float)             # 0.72 = completes 72% of planned tasks
    top_avoidance_categories    = Column(ARRAY(String))     # ["email", "forms"]
    avg_deferral_count          = Column(Float)             # average times a task is deferred before done

    # Mood correlations
    mood_sleep_correlation      = Column(Float)             # how strongly sleep predicts mood
    mood_exercise_correlation   = Column(Float)

    # Streak data
    checkin_streak              = Column(Integer, default=0)
    longest_checkin_streak      = Column(Integer, default=0)

    last_computed_at            = Column(DateTime(timezone=True))
    updated_at                  = Column(DateTime(timezone=True), onupdate=func.now())
```

---

## Alembic Migrations

```bash
# Initialise (once)
alembic init alembic

# Create migration after changing models
alembic revision --autogenerate -m "add user_patterns table"

# Apply migrations
alembic upgrade head
```

---

## Key Indexes

```sql
-- Fast user lookup
CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_checkins_user_date ON checkins(user_id, checkin_date);
CREATE INDEX idx_agent_interactions_user ON agent_interactions(user_id, created_at);

-- Avoidance pattern queries
CREATE INDEX idx_tasks_status_deferred ON tasks(user_id, status, times_deferred);

-- Goal drift detection
CREATE INDEX idx_goals_last_action ON goals(user_id, last_action_at);
```

---

## Docker Compose (Full Local Stack)

```yaml
version: "3.9"
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: lifeos
      POSTGRES_DB: lifeos
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  chroma:
    image: chromadb/chroma:latest
    ports:
      - "8000:8000"
    volumes:
      - chromadata:/chroma/chroma

volumes:
  pgdata:
  chromadata:
```

Run everything: `docker compose up -d`
