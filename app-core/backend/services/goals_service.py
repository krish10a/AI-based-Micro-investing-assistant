"""Goals management service for financial goal tracking with database persistence."""

import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from models.db_models import Goal, GoalProgress, GoalTemplate, User, PriorityEnum, GoalStatusEnum
from models.goals import GoalCreate, GoalUpdate, GoalResponse
from cachetools import TTLCache

logger = logging.getLogger(__name__)

# Cache for goal summaries (5 minute TTL)
summary_cache = TTLCache(maxsize=100, ttl=300)


class GoalsService:
    """Service for managing financial goals with database persistence."""

    def __init__(self, db: Session):
        self.db = db

    def create_goal(self, user_id: str, goal_data: GoalCreate) -> GoalResponse:
        """Create a new financial goal for a user."""
        # Validate target date is in the future
        if goal_data.timeline_months <= 0:
            raise ValueError("Timeline must be positive")

        # Calculate target date from timeline
        target_date = datetime.utcnow() + timedelta(days=goal_data.timeline_months * 30)

        # Calculate suggested monthly contribution
        monthly_contribution = self._calculate_monthly_contribution(
            goal_data.target_amount, goal_data.timeline_months
        )

        # Check if total monthly contributions would exceed capacity
        self._validate_monthly_capacity(user_id, monthly_contribution)

        # Create goal
        goal = Goal(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=goal_data.name,
            category=goal_data.description or "Wealth Building",
            description=goal_data.description,
            target_amount=goal_data.target_amount,
            current_amount=0,
            monthly_suggested_contribution=monthly_contribution,
            target_date=target_date,
            timeline_months=goal_data.timeline_months,
            priority=goal_data.priority,
            status=GoalStatusEnum.ON_TRACK,
            achieved=False,
            completion_percentage=0,
        )

        self.db.add(goal)
        self.db.commit()
        self.db.refresh(goal)

        # Clear cache
        self._clear_user_cache(user_id)

        logger.info(f"Created goal: {goal.name} (ID: {goal.id}) for user: {user_id}")
        return self._to_response(goal)

    def get_goal(self, goal_id: str, user_id: str) -> Optional[GoalResponse]:
        """Get a specific goal by ID for a user."""
        goal = self.db.query(Goal).filter(
            and_(Goal.id == goal_id, Goal.user_id == user_id)
        ).first()
        return self._to_response(goal) if goal else None

    def get_all_goals(self, user_id: str) -> List[GoalResponse]:
        """Get all goals for a user."""
        goals = self.db.query(Goal).filter(Goal.user_id == user_id).all()
        return [self._to_response(g) for g in goals]

    def update_goal(self, goal_id: str, user_id: str, update_data: GoalUpdate) -> Optional[GoalResponse]:
        """Update an existing goal."""
        goal = self.db.query(Goal).filter(
            and_(Goal.id == goal_id, Goal.user_id == user_id)
        ).first()

        if not goal:
            return None

        # Update fields
        if update_data.name is not None:
            goal.name = update_data.name
        if update_data.target_amount is not None:
            goal.target_amount = update_data.target_amount
        if update_data.timeline_months is not None:
            goal.timeline_months = update_data.timeline_months
            goal.target_date = datetime.utcnow() + timedelta(days=update_data.timeline_months * 30)
        if update_data.priority is not None:
            goal.priority = update_data.priority
        if update_data.description is not None:
            goal.description = update_data.description
        if update_data.achieved is not None:
            goal.achieved = update_data.achieved

        # Recalculate monthly contribution if target or timeline changed
        if update_data.target_amount is not None or update_data.timeline_months is not None:
            goal.monthly_suggested_contribution = self._calculate_monthly_contribution(
                goal.target_amount, goal.timeline_months
            )

        # Update completion percentage
        goal.completion_percentage = min(
            round((goal.current_amount / goal.target_amount) * 100, 2), 100
        )

        # Update status based on progress
        goal.status = self._calculate_goal_status(goal)

        goal.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(goal)

        # Clear cache
        self._clear_user_cache(user_id)

        logger.info(f"Updated goal: {goal.name} (ID: {goal_id})")
        return self._to_response(goal)

    def delete_goal(self, goal_id: str, user_id: str) -> bool:
        """Delete a goal."""
        goal = self.db.query(Goal).filter(
            and_(Goal.id == goal_id, Goal.user_id == user_id)
        ).first()

        if not goal:
            return False

        goal_name = goal.name
        self.db.delete(goal)
        self.db.commit()

        # Clear cache
        self._clear_user_cache(user_id)

        logger.info(f"Deleted goal: {goal_name} (ID: {goal_id})")
        return True

    def update_goal_progress(self, goal_id: str, user_id: str, amount_added: float) -> Optional[GoalResponse]:
        """Update goal progress by adding to current amount."""
        if amount_added <= 0:
            raise ValueError("Amount must be positive")

        goal = self.db.query(Goal).filter(
            and_(Goal.id == goal_id, Goal.user_id == user_id)
        ).first()

        if not goal:
            return None

        # Record progress history
        progress = GoalProgress(
            id=str(uuid.uuid4()),
            goal_id=goal_id,
            amount_added=amount_added,
            previous_amount=goal.current_amount,
            new_amount=goal.current_amount + amount_added,
            previous_completion=goal.completion_percentage,
            new_completion=min(
                round(((goal.current_amount + amount_added) / goal.target_amount) * 100, 2), 100
            )
        )
        self.db.add(progress)

        # Update goal
        goal.current_amount += amount_added
        goal.completion_percentage = progress.new_completion
        goal.status = self._calculate_goal_status(goal)
        goal.updated_at = datetime.utcnow()

        # Check if goal is achieved
        if goal.completion_percentage >= 100:
            goal.achieved = True
            goal.status = GoalStatusEnum.COMPLETED

        self.db.commit()
        self.db.refresh(goal)

        # Clear cache
        self._clear_user_cache(user_id)

        logger.info(f"Updated progress for goal: {goal.name} - {goal.completion_percentage}%")
        return self._to_response(goal)

    def get_goals_summary(self, user_id: str) -> Dict[str, Any]:
        """Get summary of all goals for a user."""
        # Check cache
        cache_key = f"summary_{user_id}"
        if cache_key in summary_cache:
            return summary_cache[cache_key]

        goals = self.db.query(Goal).filter(Goal.user_id == user_id).all()

        total_target = sum(g.target_amount for g in goals)
        total_current = sum(g.current_amount for g in goals)
        overall_completion = (
            round((total_current / total_target) * 100, 2) if total_target > 0 else 0
        )

        # Count by priority
        priority_counts = {p.value: 0 for p in PriorityEnum}
        for goal in goals:
            priority_counts[goal.priority.value] += 1

        # Count by status
        status_counts = {s.value: 0 for s in GoalStatusEnum}
        for goal in goals:
            status_counts[goal.status.value] += 1

        # Count achieved
        achieved_count = sum(1 for g in goals if g.achieved)

        summary = {
            "total_goals": len(goals),
            "total_target_amount": total_target,
            "total_current_amount": total_current,
            "overall_completion": overall_completion,
            "achieved_count": achieved_count,
            "pending_count": len(goals) - achieved_count,
            "priority_breakdown": priority_counts,
            "status_breakdown": status_counts,
            "monthly_allocated": sum(g.monthly_suggested_contribution for g in goals),
        }

        # Cache the result
        summary_cache[cache_key] = summary

        return summary

    def get_goal_progress_history(self, goal_id: str, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get progress history for a goal."""
        goal = self.db.query(Goal).filter(
            and_(Goal.id == goal_id, Goal.user_id == user_id)
        ).first()

        if not goal:
            return []

        progress = self.db.query(GoalProgress).filter(
            GoalProgress.goal_id == goal_id
        ).order_by(GoalProgress.created_at.desc()).limit(limit).all()

        return [
            {
                "id": p.id,
                "amount_added": p.amount_added,
                "previous_amount": p.previous_amount,
                "new_amount": p.new_amount,
                "previous_completion": p.previous_completion,
                "new_completion": p.new_completion,
                "created_at": p.created_at.isoformat(),
            }
            for p in progress
        ]

    def get_goal_templates(self) -> List[Dict[str, Any]]:
        """Get available goal templates."""
        templates = self.db.query(GoalTemplate).filter(
            GoalTemplate.is_active == True
        ).all()

        return [
            {
                "id": t.id,
                "name": t.name,
                "category": t.category,
                "description": t.description,
                "default_target_amount": t.default_target_amount,
                "default_timeline_months": t.default_timeline_months,
                "default_priority": t.default_priority.value,
                "suggested_monthly_contribution": t.suggested_monthly_contribution,
            }
            for t in templates
        ]

    def create_goal_from_template(self, user_id: str, template_id: str, target_amount: Optional[float] = None) -> GoalResponse:
        """Create a goal from a template."""
        template = self.db.query(GoalTemplate).filter(
            and_(GoalTemplate.id == template_id, GoalTemplate.is_active == True)
        ).first()

        if not template:
            raise ValueError(f"Template {template_id} not found")

        goal_data = GoalCreate(
            name=template.name,
            target_amount=target_amount or template.default_target_amount,
            timeline_months=template.default_timeline_months,
            priority=template.default_priority,
            description=template.description,
        )

        return self.create_goal(user_id, goal_data)

    def get_goal_recommendations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get goal recommendations based on user's current goals."""
        summary = self.get_goals_summary(user_id)
        goals = self.get_all_goals(user_id)

        recommendations = []

        # Check for goals that are behind
        behind_goals = [g for g in goals if g.status == "behind"]
        if behind_goals:
            recommendations.append({
                "type": "catch_up",
                "message": f"You have {len(behind_goals)} goal(s) behind schedule. Consider increasing monthly contributions.",
                "goal_ids": [g.id for g in behind_goals],
                "priority": "high"
            })

        # Check for low priority goals that could be accelerated
        low_priority_goals = [g for g in goals if g.priority == "low" and not g.achieved]
        if low_priority_goals and summary["monthly_allocated"] < summary["total_target_amount"] * 0.01:
            recommendations.append({
                "type": "accelerate",
                "message": "You have capacity to accelerate your low-priority goals.",
                "goal_ids": [g.id for g in low_priority_goals],
                "priority": "medium"
            })

        # Check for completed goals
        completed_goals = [g for g in goals if g.achieved]
        if completed_goals:
            recommendations.append({
                "type": "celebrate",
                "message": f"Congratulations! You've achieved {len(completed_goals)} goal(s).",
                "goal_ids": [g.id for g in completed_goals],
                "priority": "low"
            })

        return recommendations

    def _calculate_monthly_contribution(
        self, target_amount: float, timeline_months: int, expected_return: float = 0.12
    ) -> float:
        """Calculate monthly contribution needed to achieve goal using SIP formula."""
        if timeline_months <= 0:
            return target_amount

        monthly_rate = expected_return / 12 / 100 if expected_return > 0 else 0

        if monthly_rate == 0:
            return target_amount / timeline_months

        # SIP formula: FV = P * (((1 + r)^n - 1) / r) * (1 + r)
        factor = (((1 + monthly_rate) ** timeline_months - 1) / monthly_rate) * (1 + monthly_rate)
        monthly_contribution = target_amount / factor

        return round(monthly_contribution, 2)

    def _calculate_goal_status(self, goal: Goal) -> GoalStatusEnum:
        """Calculate goal status based on progress and timeline."""
        if goal.achieved:
            return GoalStatusEnum.COMPLETED

        if goal.completion_percentage >= 100:
            return GoalStatusEnum.COMPLETED

        # Calculate expected progress based on timeline
        # Handle both datetime objects and ISO string formats
        created_at = goal.created_at
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        days_elapsed = (datetime.utcnow() - created_at).days
        total_days = goal.timeline_months * 30
        expected_progress = (days_elapsed / total_days) * 100 if total_days > 0 else 0

        # Compare actual vs expected progress
        if goal.completion_percentage >= expected_progress * 1.1:
            return GoalStatusEnum.AHEAD
        elif goal.completion_percentage >= expected_progress * 0.9:
            return GoalStatusEnum.ON_TRACK
        else:
            return GoalStatusEnum.BEHIND

    def _validate_monthly_capacity(self, user_id: str, new_contribution: float) -> None:
        """Validate that total monthly contributions don't exceed reasonable capacity."""
        # Get current total monthly contributions
        current_goals = self.db.query(Goal).filter(Goal.user_id == user_id).all()
        current_total = sum(g.monthly_suggested_contribution for g in current_goals)

        # Assume reasonable capacity is 50% of income (this should be calculated from user profile)
        # For now, use a reasonable default
        reasonable_capacity = 100000  # ₹1 lakh per month

        if current_total + new_contribution > reasonable_capacity:
            raise ValueError(
                f"Total monthly contributions (₹{current_total + new_contribution:,.0f}) "
                f"exceed reasonable capacity (₹{reasonable_capacity:,.0f}). "
                "Consider adjusting your goals or timeline."
            )

    def _clear_user_cache(self, user_id: str) -> None:
        """Clear cache entries for a user."""
        cache_key = f"summary_{user_id}"
        if cache_key in summary_cache:
            del summary_cache[cache_key]

    def _to_response(self, goal: Goal) -> GoalResponse:
        """Convert database model to response model."""
        return GoalResponse(
            id=goal.id,
            name=goal.name,
            target_amount=goal.target_amount,
            timeline_months=goal.timeline_months,
            priority=goal.priority.value,
            description=goal.description,
            achieved=goal.achieved,
            current_amount=goal.current_amount,
            completion_percentage=goal.completion_percentage,
            monthly_suggested_contribution=goal.monthly_suggested_contribution,
            status=goal.status.value,
            created_at=goal.created_at.isoformat(),
            updated_at=goal.updated_at.isoformat(),
        )
