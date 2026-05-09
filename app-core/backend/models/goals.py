"""Pydantic schemas for financial goals management."""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime


class GoalBase(BaseModel):
    """Base goal model with common fields."""

    name: str = Field(..., min_length=1, max_length=100, description="Goal name")
    target_amount: float = Field(..., gt=0, description="Target amount in rupees")
    timeline_months: int = Field(..., gt=0, le=600, description="Timeline in months (1-600)")
    priority: Literal["low", "medium", "high", "critical"] = Field(
        default="medium", description="Goal priority"
    )
    description: Optional[str] = Field(None, max_length=500, description="Goal description")


class GoalCreate(GoalBase):
    """Request model for creating a new goal."""

    pass


class GoalUpdate(BaseModel):
    """Request model for updating a goal."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    target_amount: Optional[float] = Field(None, gt=0)
    timeline_months: Optional[int] = Field(None, gt=0, le=600)
    priority: Optional[Literal["low", "medium", "high", "critical"]] = None
    description: Optional[str] = Field(None, max_length=500)
    achieved: Optional[bool] = None


class GoalResponse(GoalBase):
    """Response model for a goal."""

    id: str
    achieved: bool = Field(default=False, description="Whether goal is achieved")
    current_amount: float = Field(default=0, description="Current allocated amount")
    completion_percentage: float = Field(default=0, description="Completion percentage")
    monthly_suggested_contribution: float = Field(
        default=0, description="Suggested monthly contribution"
    )
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    class Config:
        from_attributes = True


class GoalsListResponse(BaseModel):
    """Response model for listing all goals."""

    goals: List[GoalResponse]
    total_count: int
    total_target_amount: float
    total_current_amount: float
    overall_completion: float


# In-memory storage for goals (replace with database in production)
goals_storage: dict[str, GoalResponse] = {}
goal_counter = 0
