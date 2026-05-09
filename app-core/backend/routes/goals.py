"""API routes for financial goals management."""

import logging
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from services.goals_service import GoalsService
from models.goals import GoalCreate, GoalUpdate, GoalResponse, GoalsListResponse

logger = logging.getLogger(__name__)

router = APIRouter()
goals_service = GoalsService()


@router.post("/goals", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(goal_data: GoalCreate):
    """
    Create a new financial goal.

    Args:
        name: Goal name (e.g., "Emergency Fund", "New Car")
        target_amount: Target amount in rupees
        timeline_months: Timeline to achieve goal in months
        priority: Goal priority (low, medium, high, critical)
        description: Optional goal description

    Returns:
        Created goal with suggested monthly contribution
    """
    try:
        goal = goals_service.create_goal(goal_data)
        return JSONResponse(content=goal.model_dump(), status_code=201)
    except Exception as e:
        logger.error(f"Failed to create goal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create goal",
        )


@router.get("/goals", response_model=GoalsListResponse)
async def list_goals():
    """
    List all financial goals with completion status.

    Returns goals sorted by priority (critical first) with progress tracking.
    """
    try:
        goals = goals_service.get_all_goals()

        # Sort by priority (critical > high > medium > low)
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_goals = sorted(goals, key=lambda g: priority_order.get(g.priority, 4))

        summary = goals_service.get_goals_summary()

        return {
            "goals": [g.model_dump() for g in sorted_goals],
            "total_count": summary["total_goals"],
            "total_target_amount": summary["total_target_amount"],
            "total_current_amount": summary["total_current_amount"],
            "overall_completion": summary["overall_completion"],
        }
    except Exception as e:
        logger.error(f"Failed to list goals: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve goals",
        )


@router.get("/goals/summary")
async def get_goals_summary():
    """
    Get a summary of all goals with statistics.

    Returns aggregated metrics like total target, completion %, priority breakdown.
    """
    try:
        summary = goals_service.get_goals_summary()
        return JSONResponse(content=summary)
    except Exception as e:
        logger.error(f"Failed to get goals summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve goals summary",
        )


@router.get("/goals/{goal_id}", response_model=GoalResponse)
async def get_goal(goal_id: str):
    """
    Get a specific goal by ID.

    Returns full goal details including progress and suggested contribution.
    """
    try:
        goal = goals_service.get_goal(goal_id)
        if not goal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Goal with ID '{goal_id}' not found",
            )
        return goal
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get goal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve goal",
        )


@router.put("/goals/{goal_id}", response_model=GoalResponse)
async def update_goal(goal_id: str, update_data: GoalUpdate):
    """
    Update an existing goal.

    Args:
        goal_id: Goal ID to update
        update_data: Fields to update (name, target_amount, timeline_months, priority, description)

    Returns:
        Updated goal with new suggested monthly contribution
    """
    try:
        goal = goals_service.update_goal(goal_id, update_data)
        if not goal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Goal with ID '{goal_id}' not found",
            )
        return goal
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update goal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update goal",
        )


@router.post("/goals/{goal_id}/progress")
async def update_goal_progress(goal_id: str, amount: float):
    """
    Update goal progress by adding to current amount.

    Args:
        goal_id: Goal ID to update
        amount: Amount to add to current progress

    Returns:
        Updated goal with new completion percentage
    """
    try:
        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Amount must be positive",
            )

        goal = goals_service.update_goal_progress(goal_id, amount)
        if not goal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Goal with ID '{goal_id}' not found",
            )

        return {
            "message": "Goal progress updated successfully",
            "goal": goal.model_dump(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update goal progress: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update goal progress",
        )


@router.delete("/goals/{goal_id}")
async def delete_goal(goal_id: str):
    """
    Delete a financial goal.

    Args:
        goal_id: Goal ID to delete

    Returns:
        Success message
    """
    try:
        deleted = goals_service.delete_goal(goal_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Goal with ID '{goal_id}' not found",
            )

        return {
            "message": "Goal deleted successfully",
            "goal_id": goal_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete goal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete goal",
        )
