"""API routes for analytics and deep dive dashboard."""

import logging
import random
from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import JSONResponse
from services.analytics_service import AnalyticsService
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

router = APIRouter()
analytics_service = AnalyticsService()


@router.get("/analytics/portfolio-growth")
async def get_portfolio_growth(
    monthly_investment: float = Query(default=0, ge=0, description="Monthly SIP amount"),
    current_corpus: float = Query(default=0, ge=0, description="Current investment corpus"),
    user_segment: str = Query(default="Balanced Planner", description="User's financial segment"),
):
    """
    Return portfolio growth data for the analytics dashboard.

    Provides yearly growth data for chart rendering.
    """
    try:
        # Get portfolio performance from analytics service
        result = analytics_service.get_portfolio_performance(
            current_monthly_investment=monthly_investment,
            current_corpus=current_corpus,
            user_segment=user_segment,
        )

        # Extract yearly data for frontend
        yearly_data = []
        for i, data_point in enumerate(result["time_series"]):
            if data_point["month"] > 0 and data_point["month"] % 12 == 0:
                year = datetime.now().year + (data_point["month"] // 12)
                yearly_data.append({
                    "year": year,
                    "value": data_point["portfolio_value"],
                    "gains": data_point["growth"]
                })

        # If no yearly data, generate projection
        if not yearly_data:
            current_year = datetime.now().year
            base_value = current_corpus
            annual_return = 0.12  # 12% default return
            for i in range(7):
                yearly_data.append({
                    "year": current_year + i,
                    "value": base_value * (1 + annual_return) ** i,
                    "gains": base_value * ((1 + annual_return) ** i - 1)
                })

        return JSONResponse(content={
            "current_value": result["current_corpus"],
            "initial_value": current_corpus,
            "total_gains": result["summary"]["total_growth"],
            "returns_percent": result["summary"]["growth_percentage"],
            "yearly_data": yearly_data
        })
    except Exception as e:
        logger.error(f"Portfolio growth calculation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not calculate portfolio growth",
        )


@router.get("/analytics/risk-metrics")
async def get_risk_metrics(
    user_segment: str = Query(default="Balanced Planner", description="User's financial segment"),
):
    """
    Return risk metrics for the analytics dashboard.

    Provides Sharpe ratio, Sortino ratio, max drawdown, beta, alpha, standard deviation, and VaR.
    """
    try:
        # Generate risk metrics based on segment
        segment_risk_profiles = {
            "Financially Stressed": {
                "sharpe_ratio": 0.5,
                "sortino_ratio": 0.7,
                "max_drawdown": -8.5,
                "beta": 0.6,
                "alpha": -2.0,
                "standard_deviation": 10.0,
                "var_95": -5.0
            },
            "Cash-Flow Tight": {
                "sharpe_ratio": 0.8,
                "sortino_ratio": 1.0,
                "max_drawdown": -7.0,
                "beta": 0.8,
                "alpha": 0.5,
                "standard_deviation": 12.0,
                "var_95": -6.0
            },
            "Stable Builder": {
                "sharpe_ratio": 1.2,
                "sortino_ratio": 1.5,
                "max_drawdown": -12.0,
                "beta": 1.0,
                "alpha": 2.5,
                "standard_deviation": 18.0,
                "var_95": -10.0
            },
            "High-Surplus Builder": {
                "sharpe_ratio": 1.5,
                "sortino_ratio": 1.8,
                "max_drawdown": -15.0,
                "beta": 1.2,
                "alpha": 4.0,
                "standard_deviation": 22.0,
                "var_95": -12.0
            },
            "Wealth Accelerator": {
                "sharpe_ratio": 1.8,
                "sortino_ratio": 2.2,
                "max_drawdown": -18.0,
                "beta": 1.4,
                "alpha": 5.5,
                "standard_deviation": 25.0,
                "var_95": -15.0
            }
        }

        risk_data = segment_risk_profiles.get(user_segment, segment_risk_profiles["Stable Builder"])

        return JSONResponse(content=risk_data)
    except Exception as e:
        logger.error(f"Risk metrics calculation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not calculate risk metrics",
        )


@router.get("/analytics/market-context")
async def get_market_context():
    """
    Return market context for the analytics dashboard.

    Provides Indian market data (Nifty 50, Sensex) and market sentiment.
    """
    try:
        # Simulated market data (in production, this would come from a real market data API)
        return JSONResponse(content={
            "nifty_50": 22450.75,
            "sensex": 73850.30,
            "sentiment": "bullish",
            "sp500_change": 1.2,
            "nasdaq_change": 1.8,
            "sector_performance": [
                {"sector": "IT", "change": 2.5},
                {"sector": "Banking", "change": 1.8},
                {"sector": "Pharma", "change": 0.9},
                {"sector": "Auto", "change": 1.2},
                {"sector": "FMCG", "change": 0.5}
            ],
            "volatility_index": 14.5
        })
    except Exception as e:
        logger.error(f"Market context retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve market context",
        )


@router.get("/analytics/asset-allocation")
async def get_asset_allocation(
    user_segment: str = Query(default="Balanced Planner", description="User's financial segment"),
):
    """
    Return asset allocation recommendations based on user segment.

    Provides percentage allocation across different asset classes.
    """
    try:
        # Asset allocation based on segment
        segment_allocations = {
            "Financially Stressed": [
                {"asset_class": "Liquid Funds", "percentage": 80, "value": 0},
                {"asset_class": "Debt Funds", "percentage": 20, "value": 0},
                {"asset_class": "Equity Funds", "percentage": 0, "value": 0},
                {"asset_class": "Gold", "percentage": 0, "value": 0}
            ],
            "Cash-Flow Tight": [
                {"asset_class": "Liquid Funds", "percentage": 50, "value": 0},
                {"asset_class": "Debt Funds", "percentage": 30, "value": 0},
                {"asset_class": "Equity Funds", "percentage": 20, "value": 0},
                {"asset_class": "Gold", "percentage": 0, "value": 0}
            ],
            "Stable Builder": [
                {"asset_class": "Liquid Funds", "percentage": 20, "value": 0},
                {"asset_class": "Debt Funds", "percentage": 30, "value": 0},
                {"asset_class": "Equity Funds", "percentage": 40, "value": 0},
                {"asset_class": "Gold", "percentage": 10, "value": 0}
            ],
            "High-Surplus Builder": [
                {"asset_class": "Liquid Funds", "percentage": 10, "value": 0},
                {"asset_class": "Debt Funds", "percentage": 20, "value": 0},
                {"asset_class": "Equity Funds", "percentage": 60, "value": 0},
                {"asset_class": "Gold", "percentage": 10, "value": 0}
            ],
            "Wealth Accelerator": [
                {"asset_class": "Liquid Funds", "percentage": 5, "value": 0},
                {"asset_class": "Debt Funds", "percentage": 15, "value": 0},
                {"asset_class": "Equity Funds", "percentage": 70, "value": 0},
                {"asset_class": "Gold", "percentage": 10, "value": 0}
            ]
        }

        allocation = segment_allocations.get(user_segment, segment_allocations["Stable Builder"])

        return JSONResponse(content=allocation)
    except Exception as e:
        logger.error(f"Asset allocation retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve asset allocation",
        )


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
