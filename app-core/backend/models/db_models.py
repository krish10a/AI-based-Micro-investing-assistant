"""SQLAlchemy database models for goals and users."""

from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import enum


class PriorityEnum(str, enum.Enum):
    """Priority levels for goals."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GoalStatusEnum(str, enum.Enum):
    """Status of goal progress."""
    ON_TRACK = "on-track"
    BEHIND = "behind"
    AHEAD = "ahead"
    COMPLETED = "completed"


class User(Base):
    """User model for authentication and goal association."""

    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    goals = relationship("Goal", back_populates="user", cascade="all, delete-orphan")


class Goal(Base):
    """Financial goal model."""

    __tablename__ = "goals"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    # Goal details
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False, default="Wealth Building")
    description = Column(Text, nullable=True)

    # Financial details
    target_amount = Column(Float, nullable=False)
    current_amount = Column(Float, default=0.0)
    monthly_suggested_contribution = Column(Float, default=0.0)

    # Timeline
    target_date = Column(DateTime, nullable=True)
    timeline_months = Column(Integer, nullable=False)

    # Status and priority
    priority = Column(SQLEnum(PriorityEnum), default=PriorityEnum.MEDIUM)
    status = Column(SQLEnum(GoalStatusEnum), default=GoalStatusEnum.ON_TRACK)
    achieved = Column(Boolean, default=False)
    completion_percentage = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="goals")
    progress_history = relationship("GoalProgress", back_populates="goal", cascade="all, delete-orphan")


class GoalProgress(Base):
    """Progress history for goals."""

    __tablename__ = "goal_progress"

    id = Column(String, primary_key=True, index=True)
    goal_id = Column(String, ForeignKey("goals.id"), nullable=False, index=True)

    amount_added = Column(Float, nullable=False)
    previous_amount = Column(Float, nullable=False)
    new_amount = Column(Float, nullable=False)
    previous_completion = Column(Float, nullable=False)
    new_completion = Column(Float, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    goal = relationship("Goal", back_populates="progress_history")


class GoalTemplate(Base):
    """Pre-defined goal templates for users."""

    __tablename__ = "goal_templates"

    id = Column(String, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)

    # Template defaults
    default_target_amount = Column(Float, nullable=False)
    default_timeline_months = Column(Integer, nullable=False)
    default_priority = Column(SQLEnum(PriorityEnum), default=PriorityEnum.MEDIUM)
    suggested_monthly_contribution = Column(Float, nullable=False)

    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
