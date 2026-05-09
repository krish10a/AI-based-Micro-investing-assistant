"""Goals management service for financial goal tracking."""

import logging
import uuid
from typing import Dict, List, Optional, Any
from models.goals import GoalCreate, GoalUpdate, GoalResponse, goals_storage
from datetime import datetime

logger = logging.getLogger(__name__)

# Module-level counter (not used but declared to avoid NameError)
goal_counter: int = 0


class GoalsService:
    """Service for managing financial goals."""

    def __init__(self):
        self._initialize_demo_goals()

    def _initialize_demo_goals(self):
        """Initialize with some demo goals for testing."""
        demo_goals = [
            {
                "name": "Emergency Fund",
                "target_amount": 100000,
                "timeline_months": 12,
                "priority": "critical",
                "description": "Build a 6-month emergency fund for financial security",
            },
            {
                "name": "Vacation Savings",
                "target_amount": 50000,
                "timeline_months": 6,
                "priority": "low",
                "description": "Save for a dream vacation to Goa",
            },
        ]

        for goal_data in demo_goals:
            self.create_goal(GoalCreate(**goal_data))

    def create_goal(self, goal_data: GoalCreate) -> GoalResponse:
        """Create a new financial goal."""
        global goal_counter

        goal_id = str(uuid.uuid4())
        goal_counter += 1

        # Calculate suggested monthly contribution
        monthly_contribution = self._calculate_monthly_contribution(
            goal_data.target_amount, goal_data.timeline_months
        )

        goal = GoalResponse(
            id=goal_id,
            name=goal_data.name,
            target_amount=goal_data.target_amount,
            timeline_months=goal_data.timeline_months,
            priority=goal_data.priority,
            description=goal_data.description,
            achieved=False,
            current_amount=0,
            completion_percentage=0,
            monthly_suggested_contribution=monthly_contribution,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )

        goals_storage[goal_id] = goal
        logger.info(f"Created goal: {goal.name} (ID: {goal_id})")

        return goal

    def get_goal(self, goal_id: str) -> Optional[GoalResponse]:
        """Get a specific goal by ID."""
        return goals_storage.get(goal_id)

    def get_all_goals(self) -> List[GoalResponse]:
        """Get all goals."""
        return list(goals_storage.values())

    def update_goal(self, goal_id: str, update_data: GoalUpdate) -> Optional[GoalResponse]:
        """Update an existing goal."""
        goal = goals_storage.get(goal_id)
        if not goal:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        update_dict["updated_at"] = datetime.utcnow().isoformat()

        # Update fields
        for key, value in update_dict.items():
            if value is not None:
                setattr(goal, key, value)

        # Recalculate monthly contribution if target or timeline changed
        if "target_amount" in update_dict or "timeline_months" in update_dict:
            goal.monthly_suggested_contribution = self._calculate_monthly_contribution(
                goal.target_amount, goal.timeline_months
            )

        goals_storage[goal_id] = goal
        logger.info(f"Updated goal: {goal.name} (ID: {goal_id})")

        return goal

    def delete_goal(self, goal_id: str) -> bool:
        """Delete a goal."""
        if goal_id in goals_storage:
            goal_name = goals_storage[goal_id].name
            del goals_storage[goal_id]
            logger.info(f"Deleted goal: {goal_name} (ID: {goal_id})")
            return True
        return False

    def update_goal_progress(self, goal_id: str, amount_added: float) -> Optional[GoalResponse]:
        """Update goal progress by adding to current amount."""
        goal = goals_storage.get(goal_id)
        if not goal:
            return None

        goal.current_amount += amount_added
        goal.completion_percentage = min(
            round((goal.current_amount / goal.target_amount) * 100, 2), 100
        )

        # Check if goal is achieved
        if goal.completion_percentage >= 100:
            goal.achieved = True

        goal.updated_at = datetime.utcnow().isoformat()
        goals_storage[goal_id] = goal

        logger.info(f"Updated progress for goal: {goal.name} - {goal.completion_percentage}%")

        return goal

    def _calculate_monthly_contribution(
        self, target_amount: float, timeline_months: int, expected_return: float = 0.12
    ) -> float:
        """
        Calculate monthly contribution needed to achieve goal.

        Uses SIP formula: FV = P * (((1 + r)^n - 1) / r) * (1 + r)
        Where: FV = future value, P = monthly payment, r = monthly rate, n = months
        """
        if timeline_months <= 0:
            return target_amount

        monthly_rate = expected_return / 12 / 100 if expected_return > 0 else 0

        if monthly_rate == 0:
            return target_amount / timeline_months

        # SIP formula rearranged to solve for P
        # FV = P * (((1 + r)^n - 1) / r) * (1 + r)
        # P = FV / ((((1 + r)^n - 1) / r) * (1 + r))

        factor = (((1 + monthly_rate) ** timeline_months - 1) / monthly_rate) * (
            1 + monthly_rate
        )
        monthly_contribution = target_amount / factor

        return round(monthly_contribution, 2)

    def get_goals_summary(self) -> Dict[str, Any]:
        """Get summary of all goals."""
        goals = self.get_all_goals()

        total_target = sum(g.target_amount for g in goals)
        total_current = sum(g.current_amount for g in goals)
        overall_completion = (
            round((total_current / total_target) * 100, 2) if total_target > 0 else 0
        )

        # Count by priority
        priority_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for goal in goals:
            priority_counts[goal.priority] += 1

        # Count achieved
        achieved_count = sum(1 for g in goals if g.achieved)

        return {
            "total_goals": len(goals),
            "total_target_amount": total_target,
            "total_current_amount": total_current,
            "overall_completion": overall_completion,
            "achieved_count": achieved_count,
            "pending_count": len(goals) - achieved_count,
            "priority_breakdown": priority_counts,
        }
