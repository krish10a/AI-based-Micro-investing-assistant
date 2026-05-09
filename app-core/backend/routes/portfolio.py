"""Portfolio management routes."""

import logging
import random
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status

from models.schemas import (
    PortfolioHoldingResponse,
    PortfolioPerformanceResponse,
    Holding,
    PerformanceMetrics,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory storage for portfolio holdings
# In production, this would be a database
portfolio_storage: Dict[str, List[Dict[str, Any]]] = {}

# Mock holdings data for demo purposes
MOCK_HOLDINGS = [
    {
        "symbol": "HDFCBANK.NS",
        "name": "HDFC Bank Limited",
        "quantity": 50,
        "average_cost": 1500.0,
        "current_price": 1650.0,
        "asset_type": "equity",
        "goal_allocation": "Wealth Building",
    },
    {
        "symbol": "RELIANCE.NS",
        "name": "Reliance Industries",
        "quantity": 25,
        "average_cost": 2400.0,
        "current_price": 2550.0,
        "asset_type": "equity",
        "goal_allocation": "Wealth Building",
    },
    {
        "symbol": "SBIETFGold.NS",
        "name": "SBI Gold ETF",
        "quantity": 100,
        "average_cost": 60.0,
        "current_price": 65.0,
        "asset_type": "gold",
        "goal_allocation": "Emergency Fund",
    },
    {
        "symbol": "ICICIPRU.NS",
        "name": "ICICI Prudential Bluechip Fund",
        "quantity": 200,
        "average_cost": 85.0,
        "current_price": 92.0,
        "asset_type": "mutual_fund",
        "goal_allocation": "Child Education",
    },
]


def _generate_mock_holdings(user_id: str) -> List[Dict[str, Any]]:
    """Generate mock holdings for a user."""
    holdings = []
    for holding_data in MOCK_HOLDINGS:
        # Add some variation based on user_id
        variation = hash(user_id + holding_data["symbol"]) % 20 - 10
        current_price = holding_data["current_price"] * (1 + variation / 100)

        holding = {
            "id": f"holding_{len(holdings) + 1}",
            "symbol": holding_data["symbol"],
            "name": holding_data["name"],
            "quantity": holding_data["quantity"],
            "average_cost": holding_data["average_cost"],
            "current_price": current_price,
            "current_value": holding_data["quantity"] * current_price,
            "gain_loss": (current_price - holding_data["average_cost"]) * holding_data["quantity"],
            "gain_loss_percentage": ((current_price - holding_data["average_cost"]) / holding_data["average_cost"]) * 100,
            "asset_type": holding_data["asset_type"],
            "goal_allocation": holding_data["goal_allocation"],
        }
        holdings.append(holding)
    return holdings


@router.get("/portfolio", response_model=PortfolioHoldingResponse)
async def get_portfolio_holdings(user_id: str):
    """
    Get user's portfolio holdings.

    Args:
        user_id: User ID

    Returns:
        Portfolio holdings with current values and gain/loss
    """
    try:
        # Get or generate holdings
        if user_id not in portfolio_storage:
            portfolio_storage[user_id] = _generate_mock_holdings(user_id)

        holdings_data = portfolio_storage[user_id]

        # Calculate totals
        total_value = sum(h["current_value"] for h in holdings_data)
        total_invested = sum(h["quantity"] * h["average_cost"] for h in holdings_data)
        total_gain_loss = total_value - total_invested
        total_gain_loss_percentage = (total_gain_loss / total_invested) * 100 if total_invested > 0 else 0

        # Asset allocation
        asset_allocation: Dict[str, float] = {}
        for holding in holdings_data:
            asset_type = holding["asset_type"]
            if asset_type not in asset_allocation:
                asset_allocation[asset_type] = 0
            asset_allocation[asset_type] += holding["current_value"]

        # Normalize to percentages
        if total_value > 0:
            asset_allocation = {
                k: round((v / total_value) * 100, 2)
                for k, v in asset_allocation.items()
            }

        # Convert to Holding objects
        holdings = [
            Holding(
                symbol=h["symbol"],
                name=h["name"],
                quantity=h["quantity"],
                average_cost=h["average_cost"],
                current_price=h["current_price"],
                current_value=h["current_value"],
                gain_loss=h["gain_loss"],
                gain_loss_percentage=h["gain_loss_percentage"],
                asset_type=h["asset_type"],
                goal_allocation=h.get("goal_allocation"),
            )
            for h in holdings_data
        ]

        return PortfolioHoldingResponse(
            user_id=user_id,
            holdings=holdings,
            total_value=total_value,
            total_invested=total_invested,
            total_gain_loss=total_gain_loss,
            total_gain_loss_percentage=round(total_gain_loss_percentage, 2),
            asset_allocation=asset_allocation,
            last_updated=datetime.utcnow().isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to get portfolio holdings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve portfolio holdings",
        )


@router.get("/portfolio/performance", response_model=PortfolioPerformanceResponse)
async def get_portfolio_performance(user_id: str):
    """
    Get portfolio performance metrics.

    Args:
        user_id: User ID

    Returns:
        Performance metrics including history, best/worst performers
    """
    try:
        # Get or generate holdings
        if user_id not in portfolio_storage:
            portfolio_storage[user_id] = _generate_mock_holdings(user_id)

        holdings_data = portfolio_storage[user_id]

        # Calculate current performance
        total_value = sum(h["current_value"] for h in holdings_data)
        total_invested = sum(h["quantity"] * h["average_cost"] for h in holdings_data)
        total_gain_loss = total_value - total_invested
        total_return_percentage = (total_gain_loss / total_invested) * 100 if total_invested > 0 else 0

        # Generate performance history (mock data)
        performance_history = [
            PerformanceMetrics(
                period="1W",
                return_percentage=round(random.uniform(-2, 3), 2),
                absolute_return=round(total_invested * random.uniform(-0.02, 0.03), 2),
                benchmark_comparison=round(random.uniform(-1, 1), 2),
            ),
            PerformanceMetrics(
                period="1M",
                return_percentage=round(random.uniform(-5, 8), 2),
                absolute_return=round(total_invested * random.uniform(-0.05, 0.08), 2),
                benchmark_comparison=round(random.uniform(-2, 2), 2),
            ),
            PerformanceMetrics(
                period="3M",
                return_percentage=round(random.uniform(-10, 15), 2),
                absolute_return=round(total_invested * random.uniform(-0.1, 0.15), 2),
                benchmark_comparison=round(random.uniform(-3, 3), 2),
            ),
            PerformanceMetrics(
                period="6M",
                return_percentage=round(random.uniform(-15, 25), 2),
                absolute_return=round(total_invested * random.uniform(-0.15, 0.25), 2),
                benchmark_comparison=round(random.uniform(-5, 5), 2),
            ),
            PerformanceMetrics(
                period="1Y",
                return_percentage=round(random.uniform(-20, 35), 2),
                absolute_return=round(total_invested * random.uniform(-0.2, 0.35), 2),
                benchmark_comparison=round(random.uniform(-8, 8), 2),
            ),
        ]

        # Find best and worst performers
        if holdings_data:
            best = max(holdings_data, key=lambda h: h["gain_loss_percentage"])
            worst = min(holdings_data, key=lambda h: h["gain_loss_percentage"])

            best_performer = {
                "symbol": best["symbol"],
                "name": best["name"],
                "gain_loss_percentage": round(best["gain_loss_percentage"], 2),
                "gain_loss": round(best["gain_loss"], 2),
            }
            worst_performer = {
                "symbol": worst["symbol"],
                "name": worst["name"],
                "gain_loss_percentage": round(worst["gain_loss_percentage"], 2),
                "gain_loss": round(worst["gain_loss"], 2),
            }
        else:
            best_performer = None
            worst_performer = None

        return PortfolioPerformanceResponse(
            user_id=user_id,
            current_value=total_value,
            total_invested=total_invested,
            total_gain_loss=total_gain_loss,
            total_return_percentage=round(total_return_percentage, 2),
            current_date=datetime.utcnow().isoformat(),
            holdings_count=len(holdings_data),
            performance_history=performance_history,
            best_performer=best_performer,
            worst_performer=worst_performer,
        )

    except Exception as e:
        logger.error(f"Failed to get portfolio performance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve portfolio performance",
        )


@router.post("/portfolio/rebalance")
async def rebalance_portfolio(user_id: str, target_allocation: Dict[str, float]):
    """
    Get rebalancing recommendations for the portfolio.

    Args:
        user_id: User ID
        target_allocation: Target asset allocation percentages

    Returns:
        Rebalancing recommendations
    """
    try:
        # Get current holdings
        if user_id not in portfolio_storage:
            portfolio_storage[user_id] = _generate_mock_holdings(user_id)

        holdings_data = portfolio_storage[user_id]

        total_value = sum(h["current_value"] for h in holdings_data)

        # Calculate current allocation
        current_allocation: Dict[str, float] = {}
        for holding in holdings_data:
            asset_type = holding["asset_type"]
            if asset_type not in current_allocation:
                current_allocation[asset_type] = 0
            current_allocation[asset_type] += holding["current_value"]

        if total_value > 0:
            current_allocation = {
                k: round((v / total_value) * 100, 2)
                for k, v in current_allocation.items()
            }

        # Calculate rebalancing needed
        rebalancing_needed = []
        for asset_type, target_pct in target_allocation.items():
            current_pct = current_allocation.get(asset_type, 0)
            difference = target_pct - current_pct
            amount = (difference / 100) * total_value

            rebalancing_needed.append(
                {
                    "asset_type": asset_type,
                    "current_percentage": current_pct,
                    "target_percentage": target_pct,
                    "difference": round(difference, 2),
                    "amount_to_buy_or_sell": round(amount, 2),
                    "action": "buy" if amount > 0 else "sell",
                }
            )

        return {
            "user_id": user_id,
            "total_value": total_value,
            "current_allocation": current_allocation,
            "target_allocation": target_allocation,
            "rebalancing_needed": rebalancing_needed,
            "generated_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to generate rebalancing recommendations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate rebalancing recommendations",
        )
