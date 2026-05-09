"""API routes for financial goals management with authentication and pagination."""

import logging
from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List

from database import get_db
from auth import get_current_active_user
from services.goals_service import GoalsService
from models.db_models import User
from models.goals import GoalCreate, GoalUpdate, GoalResponse

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class GoalsListResponse(BaseModel):
    """Response model for listing all goals."""
    goals: List[GoalResponse]
    total_count: int
    total_target_amount: float
    total_current_amount: float
    overall_completion: float
    page: int
    page_size: int
    total_pages: int


class BulkGoalCreate(BaseModel):
    """Request model for creating multiple goals."""
    goals: List[GoalCreate]


class BulkGoalResponse(BaseModel):
    """Response model for bulk goal creation."""
    created: List[GoalResponse]
    failed: List[dict]
    total_created: int
    total_failed: int


class GoalProgressUpdate(BaseModel):
    """Request model for updating goal progress."""
    amount: float = Field(..., gt=0, description="Amount to add to current progress")


class GoalProgressResponse(BaseModel):
    """Response model for goal progress update."""
    message: str
    goal: GoalResponse


class GoalDeleteResponse(BaseModel):
    """Response model for goal deletion."""
    message: str
    goal_id: str


# ============================================================================
# Helper Functions
# ============================================================================

def get_goals_service(db: Session) -> GoalsService:
    """Dependency for getting goals service."""
    return GoalsService(db)


# ============================================================================
# Routes
# ============================================================================

@router.post("/goals", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(
    goal_data: GoalCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
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
        goals_service = get_goals_service(db)
        goal = goals_service.create_goal(current_user.id, goal_data)
        return JSONResponse(content=goal.model_dump(), status_code=201)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create goal: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create goal. Please try again."
        )


@router.get("/goals", response_model=GoalsListResponse)
async def list_goals(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    sort_by: str = Query("priority", description="Sort field (priority, created_at, target_amount)"),
    sort_order: str = Query("desc", description="Sort order (asc, desc)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List all financial goals with completion status and pagination.

    Returns goals sorted by priority (critical first) with progress tracking.
    """
    try:
        goals_service = get_goals_service(db)
        goals = goals_service.get_all_goals(current_user.id)

        # Sort goals
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}

        if sort_by == "priority":
            goals.sort(key=lambda g: priority_order.get(g.priority, 4))
        elif sort_by == "created_at":
            goals.sort(key=lambda g: g.created_at, reverse=(sort_order == "desc"))
        elif sort_by == "target_amount":
            goals.sort(key=lambda g: g.target_amount, reverse=(sort_order == "desc"))

        # Apply sort order for priority
        if sort_by == "priority" and sort_order == "asc":
            goals.reverse()

        # Pagination
        total_count = len(goals)
        total_pages = (total_count + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_goals = goals[start_idx:end_idx]

        summary = goals_service.get_goals_summary(current_user.id)

        return {
            "goals": [g.model_dump() for g in paginated_goals],
            "total_count": total_count,
            "total_target_amount": summary["total_target_amount"],
            "total_current_amount": summary["total_current_amount"],
            "overall_completion": summary["overall_completion"],
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
    except Exception as e:
        logger.error(f"Failed to list goals: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve goals. Please try again."
        )


@router.get("/goals/summary")
async def get_goals_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a summary of all goals with statistics.

    Returns aggregated metrics like total target, completion %, priority breakdown.
    """
    try:
        goals_service = get_goals_service(db)
        summary = goals_service.get_goals_summary(current_user.id)
        return JSONResponse(content=summary)
    except Exception as e:
        logger.error(f"Failed to get goals summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve goals summary. Please try again."
        )


@router.get("/goals/{goal_id}", response_model=GoalResponse)
async def get_goal(
    goal_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific goal by ID.

    Returns full goal details including progress and suggested contribution.
    """
    try:
        goals_service = get_goals_service(db)
        goal = goals_service.get_goal(goal_id, current_user.id)
        if not goal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Goal with ID '{goal_id}' not found"
            )
        return goal
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get goal: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve goal. Please try again."
        )


@router.put("/goals/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: str,
    update_data: GoalUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing goal.

    Args:
        goal_id: Goal ID to update
        update_data: Fields to update (name, target_amount, timeline_months, priority, description)

    Returns:
        Updated goal with new suggested monthly contribution
    """
    try:
        goals_service = get_goals_service(db)
        goal = goals_service.update_goal(goal_id, current_user.id, update_data)
        if not goal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Goal with ID '{goal_id}' not found"
            )
        return goal
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update goal: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update goal. Please try again."
        )


@router.post("/goals/{goal_id}/progress", response_model=GoalProgressResponse)
async def update_goal_progress(
    goal_id: str,
    progress_data: GoalProgressUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update goal progress by adding to current amount.

    Args:
        goal_id: Goal ID to update
        amount: Amount to add to current progress

    Returns:
        Updated goal with new completion percentage
    """
    try:
        goals_service = get_goals_service(db)
        goal = goals_service.update_goal_progress(goal_id, current_user.id, progress_data.amount)
        if not goal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Goal with ID '{goal_id}' not found"
            )

        return {
            "message": "Goal progress updated successfully",
            "goal": goal.model_dump()
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update goal progress: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update goal progress. Please try again."
        )


@router.delete("/goals/{goal_id}", response_model=GoalDeleteResponse)
async def delete_goal(
    goal_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a financial goal.

    Args:
        goal_id: Goal ID to delete

    Returns:
        Success message
    """
    try:
        goals_service = get_goals_service(db)
        deleted = goals_service.delete_goal(goal_id, current_user.id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Goal with ID '{goal_id}' not found"
            )

        return {
            "message": "Goal deleted successfully",
            "goal_id": goal_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete goal: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete goal. Please try again."
        )


@router.post("/goals/bulk", response_model=BulkGoalResponse)
async def create_bulk_goals(
    bulk_data: BulkGoalCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create multiple goals in a single request.

    Args:
        goals: List of goal data to create

    Returns:
        Summary of created and failed goals
    """
    try:
        goals_service = get_goals_service(db)
        created = []
        failed = []

        for i, goal_data in enumerate(bulk_data.goals):
            try:
                goal = goals_service.create_goal(current_user.id, goal_data)
                created.append(goal)
            except Exception as e:
                failed.append({
                    "index": i,
                    "goal_name": goal_data.name,
                    "error": str(e)
                })

        return {
            "created": [g.model_dump() for g in created],
            "failed": failed,
            "total_created": len(created),
            "total_failed": len(failed)
        }
    except Exception as e:
        logger.error(f"Failed to create bulk goals: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create bulk goals. Please try again."
        )


@router.get("/goals/{goal_id}/progress/history")
async def get_goal_progress_history(
    goal_id: str,
    limit: int = Query(50, ge=1, le=100, description="Number of history entries to return"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get progress history for a specific goal.

    Returns a list of progress updates with timestamps.
    """
    try:
        goals_service = get_goals_service(db)
        history = goals_service.get_goal_progress_history(goal_id, current_user.id, limit)
        return {"history": history, "total": len(history)}
    except Exception as e:
        logger.error(f"Failed to get goal progress history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve goal progress history. Please try again."
        )


@router.get("/goals/templates")
async def get_goal_templates(db: Session = Depends(get_db)):
    """
    Get available goal templates.

    Returns a list of pre-configured goal templates that users can use as starting points.
    """
    try:
        goals_service = get_goals_service(db)
        templates = goals_service.get_goal_templates()
        return {"templates": templates}
    except Exception as e:
        logger.error(f"Failed to get goal templates: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve goal templates. Please try again."
        )


@router.post("/goals/templates/{template_id}", response_model=GoalResponse)
async def create_goal_from_template(
    template_id: str,
    target_amount: Optional[float] = Query(None, description="Override default target amount"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a goal from a template.

    Args:
        template_id: Template ID to use
        target_amount: Optional override for target amount

    Returns:
        Created goal
    """
    try:
        goals_service = get_goals_service(db)
        goal = goals_service.create_goal_from_template(current_user.id, template_id, target_amount)
        return goal
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_4022_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create goal from template: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create goal from template. Please try again."
        )


@router.get("/goals/recommendations")
async def get_goal_recommendations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get goal recommendations based on user's current goals.

    Returns personalized recommendations for improving goal progress.
    """
    try:
        goals_service = get_goals_service(db)
        recommendations = goals_service.get_goal_recommendations(current_user.id)
        return {"recommendations": recommendations}
    except Exception as e:
        logger.error(f"Failed to get goal recommendations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve goal recommendations. Please try again."
        )
