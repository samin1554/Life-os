import uuid
from datetime import datetime, time, date
from typing import Optional, List

from sqlalchemy import (
    String,
    Text,
    Boolean,
    Integer,
    Float,
    DateTime,
    Time,
    Date,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


def generate_uuid() -> uuid.UUID:
    return uuid.uuid4()


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid
    )
    clerk_id: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    hashed_password: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    timezone: Mapped[str] = mapped_column(String, default="UTC")
    onboarding_done: Mapped[bool] = mapped_column(Boolean, default=False)
    api_key_disclaimer_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    # Relationships
    profile: Mapped[Optional["UserProfile"]] = relationship(
        "UserProfile", back_populates="user", uselist=False
    )
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="user")
    checkins: Mapped[List["CheckIn"]] = relationship("CheckIn", back_populates="user")
    goals: Mapped[List["Goal"]] = relationship("Goal", back_populates="user")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True
    )

    # Identity
    occupation: Mapped[Optional[str]] = mapped_column(String)
    life_focus_areas: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))

    # Energy patterns
    typical_wake_time: Mapped[Optional[time]] = mapped_column(Time)
    typical_sleep_time: Mapped[Optional[time]] = mapped_column(Time)
    peak_energy_start: Mapped[Optional[time]] = mapped_column(Time)
    peak_energy_end: Mapped[Optional[time]] = mapped_column(Time)
    low_energy_windows: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Task patterns
    time_estimation_bias: Mapped[float] = mapped_column(Float, default=1.0)
    avg_tasks_completed: Mapped[Optional[float]] = mapped_column(Float)
    avoidance_categories: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))

    # Preferences
    communication_style: Mapped[Optional[str]] = mapped_column(String)
    coaching_tone: Mapped[Optional[str]] = mapped_column(String)

    # Meta
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="profile")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )

    # Content
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[Optional[str]] = mapped_column(String)

    # Status
    status: Mapped[str] = mapped_column(String, default="pending")
    priority: Mapped[int] = mapped_column(Integer, default=2)

    # Scheduling
    due_date: Mapped[Optional[date]] = mapped_column(Date)
    scheduled_for: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Time tracking
    estimated_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    actual_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Avoidance tracking
    times_deferred: Mapped[int] = mapped_column(Integer, default=0)
    first_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Agent integration
    assigned_agent: Mapped[Optional[str]] = mapped_column(String)
    execution_output: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="tasks")


class CheckIn(Base):
    __tablename__ = "checkins"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )

    # Timing
    checkin_type: Mapped[str] = mapped_column(String)
    checkin_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Scores (1-5 scale)
    mood_score: Mapped[Optional[int]] = mapped_column(Integer)
    energy_score: Mapped[Optional[int]] = mapped_column(Integer)
    stress_score: Mapped[Optional[int]] = mapped_column(Integer)
    focus_score: Mapped[Optional[int]] = mapped_column(Integer)

    # Physical
    sleep_hours: Mapped[Optional[float]] = mapped_column(Float)
    sleep_quality: Mapped[Optional[int]] = mapped_column(Integer)
    exercised: Mapped[Optional[bool]] = mapped_column(Boolean)

    # Context
    notes: Mapped[Optional[str]] = mapped_column(Text)
    wins: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))
    struggles: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))

    # Tasks (evening only)
    tasks_planned: Mapped[Optional[int]] = mapped_column(Integer)
    tasks_completed: Mapped[Optional[int]] = mapped_column(Integer)

    user: Mapped["User"] = relationship("User", back_populates="checkins")


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )

    # Content
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    why: Mapped[Optional[str]] = mapped_column(Text)

    # Categorisation
    domain: Mapped[Optional[str]] = mapped_column(String)
    timeframe: Mapped[Optional[str]] = mapped_column(String)

    # Progress
    status: Mapped[str] = mapped_column(String, default="active")
    progress_pct: Mapped[int] = mapped_column(Integer, default=0)
    last_action_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Milestones
    milestones: Mapped[Optional[dict]] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="goals")



class AgentInteraction(Base):
    __tablename__ = "agent_interactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )

    # What happened
    agent_name: Mapped[Optional[str]] = mapped_column(String, index=True)
    input_summary: Mapped[Optional[str]] = mapped_column(Text)
    output_summary: Mapped[Optional[str]] = mapped_column(Text)
    full_response: Mapped[Optional[str]] = mapped_column(Text)

    # Run tracking
    status: Mapped[str] = mapped_column(String, default="pending")
    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True
    )
    trigger_type: Mapped[Optional[str]] = mapped_column(String)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    # User feedback
    accepted: Mapped[Optional[bool]] = mapped_column(Boolean)
    overridden: Mapped[bool] = mapped_column(Boolean, default=False)
    override_note: Mapped[Optional[str]] = mapped_column(Text)

    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class GeneratedFile(Base):
    __tablename__ = "generated_files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )

    filename: Mapped[str] = mapped_column(String, nullable=False)
    original_name: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    file_format: Mapped[str] = mapped_column(String)
    file_size_bytes: Mapped[int] = mapped_column(Integer)

    template_used: Mapped[Optional[str]] = mapped_column(String)
    source_agent: Mapped[str] = mapped_column(String, default="worker")
    task_description: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class UserPattern(Base):
    __tablename__ = "user_patterns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True
    )

    # Energy rhythms
    peak_days: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))
    low_days: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))
    peak_hour_start: Mapped[Optional[int]] = mapped_column(Integer)
    peak_hour_end: Mapped[Optional[int]] = mapped_column(Integer)

    # Task patterns
    time_estimation_bias: Mapped[Optional[float]] = mapped_column(Float)
    avg_completion_rate_7d: Mapped[Optional[float]] = mapped_column(Float)
    top_avoidance_categories: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))
    avg_deferral_count: Mapped[Optional[float]] = mapped_column(Float)

    # Mood correlations
    mood_sleep_correlation: Mapped[Optional[float]] = mapped_column(Float)
    mood_exercise_correlation: Mapped[Optional[float]] = mapped_column(Float)

    # Streak data
    checkin_streak: Mapped[int] = mapped_column(Integer, default=0)
    longest_checkin_streak: Mapped[int] = mapped_column(Integer, default=0)

    last_computed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), index=True
    )
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )

    notification_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    link: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class UserApiKey(Base):
    __tablename__ = "user_api_keys"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", "label", name="uq_user_provider_label"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    provider: Mapped[str] = mapped_column(String, nullable=False)  # groq, openai, anthropic, tavily, custom
    label: Mapped[str] = mapped_column(String, nullable=False, default="default")
    base_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # for custom providers
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=False)
    key_suffix: Mapped[str] = mapped_column(String(4), nullable=False)  # last 4 chars
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )


class ConnectedAccount(Base):
    __tablename__ = "connected_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    provider: Mapped[str] = mapped_column(String, nullable=False)  # "gmail", "outlook"
    account_email: Mapped[str] = mapped_column(String, nullable=False)
    encrypted_access_token: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    scopes: Mapped[Optional[dict]] = mapped_column(JSONB)  # list of granted scopes
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    filename: Mapped[str] = mapped_column(String, nullable=False)  # stored name (uuid-based)
    original_name: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)  # S3 key or local path
    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    purpose: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # context, resume, etc.
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
