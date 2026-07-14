"""
SQLAlchemy ORM models: `users` and `videos` (PRD section 7.11 - Data / Storage).

`videos` also stores intermediate pipeline artifacts (script/scene plan/
timestamps) as JSON columns so a job can be resumed/debugged without
re-calling paid AI providers.
"""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Float, DateTime, Enum, Text, ForeignKey
from sqlalchemy.orm import relationship

from backend.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class VideoStatus(str, enum.Enum):
    QUEUED = "queued"
    SCRIPT = "script"
    PLANNING = "planning"
    AUDIO = "audio"
    ALIGNMENT = "alignment"
    ASSETS = "assets"
    COMPOSITION = "composition"
    ANIMATION = "animation"
    RENDERING = "rendering"
    AWAITING_REVIEW = "awaiting_review"
    COMPLETED = "completed"
    FAILED = "failed"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    videos = relationship("Video", back_populates="owner", cascade="all, delete-orphan")


class Video(Base):
    __tablename__ = "videos"

    id = Column(String, primary_key=True, default=_uuid)
    owner_id = Column(String, ForeignKey("users.id"), nullable=True)

    instruction = Column(Text, nullable=False)
    tone = Column(String, default="professional")
    audience = Column(String, default="general")
    length_minutes = Column(Float, default=1.0)

    status = Column(Enum(VideoStatus), default=VideoStatus.QUEUED, nullable=False)
    error_message = Column(Text, nullable=True)

    # Intermediate pipeline artifacts, stored as JSON text so a failed job
    # can be inspected/resumed without re-running earlier (paid) stages.
    script_json = Column(Text, nullable=True)
    scene_plan_json = Column(Text, nullable=True)
    timestamps_json = Column(Text, nullable=True)
    assets_json = Column(Text, nullable=True)
    composition_json = Column(Text, nullable=True)
    animation_json = Column(Text, nullable=True)

    audio_path = Column(String, nullable=True)
    captions_path = Column(String, nullable=True)
    output_path = Column(String, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    owner = relationship("User", back_populates="videos")
