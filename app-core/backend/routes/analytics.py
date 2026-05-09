"""API routes for analytics and deep dive dashboard."""

import logging
from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import JSONResponse
from services.analytics_service import AnalyticsService
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter()
analytics_service = AnalyticsService()


@router.get("/analytics/portfolio-performance")
async def get_portfolio_performance(
    monthly_investment: float = Query(default=0, ge=0, description="Monthly SIP amount"),
    current_corpus: float = Query(default=0, ge=0, description="Current investment corpus"),
    user_segment: str = Query(default="Balanced Planner", description="User's financial segment"),
):
    """
    Return portfolio performance time-series data for charts.

    Provides historical and projected growth data for the analytics dashboard.
    """
    try:
        result = analytics_service.get_portfolio_performance(
            current_monthly_investment=monthly_investment,
            current_corpus=current_corpus,
            user_segment=user_segment,
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Portfolio performance calculation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not calculate portfolio performance",
        )


@router.get("/analytics/ai-reasoning")
async def get_ai_reasoning(
    cluster_id: int = Query(default=1, ge=0, le=2, description="Cluster ID from ML model"),
    segment: str = Query(default="Balanced Planner", description="Assigned segment"),
    income: float = Query(default=50000, gt=0, description="User income for feature computation"),
    rent: float = Query(default=15000, ge=0, description="Rent expense"),
    loan_repayment: float = Query(default=5000, ge=0, description="Loan repayment"),
    groceries: float = Query(default=8000, ge=0, description="Groceries expense"),
    transport: float = Query(default=3000, ge=0, description="Transport expense"),
    utilities: float = Query(default=2000, ge=0, description="Utilities expense"),
    healthcare: float = Query(default=1500, ge=0, description="Healthcare expense"),
    eating_out: float = Query(default=3000, ge=0, description="Eating out expense"),
    entertainment: float = Query(default=2000, ge=0, description="Entertainment expense"),
    insurance: float = Query(default=2000, ge=0, description="Insurance expense"),
    education: float = Query(default=2000, ge=0, description="Education expense"),
    miscellaneous: float = Query(default=2000, ge=0, description="Miscellaneous expense"),
):
    """
    Return AI reasoning and feature importance for the user's cluster.

    Explains why the user was assigned to their segment with feature contributions.
    """
    try:
        user_input = {
            "income": income,
            "rent": rent,
            "loan_repayment": loan_repayment,
            "groceries": groceries,
            "transport": transport,
            "utilities": utilities,
            "healthcare": healthcare,
            "eating_out": eating_out,
            "entertainment": entertainment,
            "insurance": insurance,
            "education": education,
            "miscellaneous": miscellaneous,
        }

        result = analytics_service.get_ai_reasoning(
            user_input=user_input,
            cluster_id=cluster_id,
            segment=segment,
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"AI reasoning calculation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate AI reasoning",
        )


@router.get("/analytics/system-stats")
async def get_system_stats():
    """
    Return global system statistics for the dashboard hero section.

    Shows platform-wide metrics like total assets managed, avg yield, etc.
    """
    try:
        result = analytics_service.get_global_stats()
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"System stats retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve system stats",
        )


@router.get("/analytics/notifications")
async def get_notifications(
    user_segment: str = Query(default="Balanced Planner", description="User's segment for personalized alerts"),
    limit: int = Query(default=10, ge=1, le=50, description="Maximum notifications to return"),
):
    """
    Return personalized AI alerts and insights for the user.

    Notifications are segment-specific and include market updates, tips, and alerts.
    """
    try:
        result = analytics_service.get_notifications(user_segment=user_segment)
        return JSONResponse(content={"notifications": result[:limit]})
    except Exception as e:
        logger.error(f"Notifications retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve notifications",
        )
