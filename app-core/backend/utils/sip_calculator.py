"""SIP (Systematic Investment Plan) calculator utilities."""

from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class SIPResult:
    """SIP calculation result."""
    monthly_investment: float
    years: int
    expected_return: float
    future_value: float
    total_invested: float
    total_growth: float
    growth_percentage: float


def calculate_sip_future_value(
    monthly_investment: float,
    years: int,
    expected_return: float
) -> SIPResult:
    """
    Calculate future value of a SIP investment.

    Formula: FV = P × ({(1 + r)^n - 1} / r) × (1 + r)

    Where:
    - P = Monthly investment
    - r = Monthly return rate (annual return / 12 / 100)
    - n = Total number of months (years × 12)

    Args:
        monthly_investment: Monthly SIP amount in rupees
        years: Investment tenure in years
        expected_return: Expected annual return rate in percentage

    Returns:
        SIPResult with all calculation details
    """
    # Validate inputs
    if monthly_investment <= 0:
        raise ValueError("Monthly investment must be positive")
    if years <= 0:
        raise ValueError("Investment period must be positive")
    if expected_return <= 0:
        raise ValueError("Expected return must be positive")

    monthly_rate = expected_return / 12 / 100
    months = years * 12

    # SIP Future Value Formula
    # FV = P × ({(1 + r)^n - 1} / r) × (1 + r)
    future_value = monthly_investment * ((1 + monthly_rate) ** months - 1) / monthly_rate * (1 + monthly_rate)

    total_invested = monthly_investment * months
    total_growth = future_value - total_invested
    growth_percentage = (total_growth / total_invested) * 100 if total_invested > 0 else 0

    return SIPResult(
        monthly_investment=monthly_investment,
        years=years,
        expected_return=expected_return,
        future_value=round(future_value, 2),
        total_invested=round(total_invested, 2),
        total_growth=round(total_growth, 2),
        growth_percentage=round(growth_percentage, 2)
    )


def get_sip_examples() -> Dict[str, Dict[str, Any]]:
    """Return common SIP scenarios for reference."""
    return {
        "starter": {
            "monthly_investment": 500,
            "years": 10,
            "expected_return": 12,
            "description": "Small monthly SIP for beginners"
        },
        "moderate": {
            "monthly_investment": 5000,
            "years": 15,
            "expected_return": 12,
            "description": "Moderate SIP for working professionals"
        },
        "aggressive": {
            "monthly_investment": 25000,
            "years": 20,
            "expected_return": 14,
            "description": "Aggressive SIP for wealth building"
        }
    }
