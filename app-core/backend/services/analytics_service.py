"""Analytics service for portfolio performance and AI reasoning."""

import logging
from typing import Dict, List, Any
from config.settings import settings

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for computing analytics and AI reasoning explanations."""

    def __init__(self):
        self.feature_weights = self._get_default_feature_weights()

    def _get_default_feature_weights(self) -> Dict[str, float]:
        """Return default feature importance weights for clustering."""
        return {
            "savings_rate": 0.25,
            "debt_burden": 0.20,
            "expense_ratio": 0.15,
            "dependency_burden": 0.10,
            "emergency_fund_ratio": 0.15,
            "discretionary_spending": 0.10,
            "future_capacity_ratio": 0.05,
        }

    def get_portfolio_performance(
        self,
        current_monthly_investment: float = 0,
        current_corpus: float = 0,
        user_segment: str = "Balanced Planner",
    ) -> Dict[str, Any]:
        """
        Generate portfolio performance time-series data.

        Returns historical and projected growth data points for chart rendering.
        """
        # Base annual returns by segment
        segment_returns = {
            "Financially Stressed": 0.06,  # Conservative (liquid funds)
            "Balanced Planner": 0.10,  # Moderate (hybrid funds)
            "Investment Ready": 0.12,  # Aggressive (equity funds)
        }

        annual_return_rate = segment_returns.get(user_segment, 0.10)

        # Generate time-series data (12 months historical + 60 months projected)
        time_series = []

        # Historical data (last 12 months - simulated)
        import random

        random.seed(42)  # Reproducible for demo
        current_value = current_corpus
        for month in range(-12, 0):
            monthly_contribution = current_monthly_investment * 0.8  # Assume 80% consistency
            monthly_growth = current_value * (annual_return_rate / 12) * random.uniform(0.8, 1.2)
            current_value += monthly_contribution + monthly_growth

            time_series.append(
                {
                    "month": month,
                    "period_label": f"Month {month}" if month < 0 else f"Month {month}",
                    "portfolio_value": round(current_value, 2),
                    "monthly_contribution": round(monthly_contribution, 2),
                    "growth": round(monthly_growth, 2),
                    "is_historical": True,
                }
            )

        # Projected data (next 60 months)
        for month in range(1, 61):
            monthly_contribution = current_monthly_investment
            monthly_growth = current_value * (annual_return_rate / 12)
            current_value += monthly_contribution + monthly_growth

            time_series.append(
                {
                    "month": month,
                    "period_label": f"Month {month}",
                    "portfolio_value": round(current_value, 2),
                    "monthly_contribution": round(monthly_contribution, 2),
                    "growth": round(monthly_growth, 2),
                    "is_historical": False,
                }
            )

        # Summary statistics
        final_value = time_series[-1]["portfolio_value"]
        total_invested = current_corpus + (current_monthly_investment * 60)
        total_growth = final_value - total_invested

        return {
            "current_corpus": current_corpus,
            "monthly_investment": current_monthly_investment,
            "annual_return_rate": annual_return_rate,
            "segment": user_segment,
            "projections": {
                "1_year": round(time_series[12]["portfolio_value"], 2),
                "3_year": round(time_series[36]["portfolio_value"], 2),
                "5_year": round(time_series[60]["portfolio_value"], 2),
            },
            "summary": {
                "final_value": round(final_value, 2),
                "total_invested": round(total_invested, 2),
                "total_growth": round(total_growth, 2),
                "growth_percentage": round((total_growth / total_invested) * 100, 2) if total_invested > 0 else 0,
            },
            "time_series": time_series,
        }

    def get_ai_reasoning(
        self,
        user_input: Dict[str, Any],
        cluster_id: int,
        segment: str,
    ) -> Dict[str, Any]:
        """
        Explain the clustering logic and feature importance for a user's cluster.

        Returns weights and feature contributions for visualization.
        """
        # Compute user's feature values
        income = user_input.get("income", 0)
        expenses = sum(
            [
                user_input.get("rent", 0),
                user_input.get("loan_repayment", 0),
                user_input.get("groceries", 0),
                user_input.get("transport", 0),
                user_input.get("utilities", 0),
                user_input.get("healthcare", 0),
                user_input.get("eating_out", 0),
                user_input.get("entertainment", 0),
                user_input.get("insurance", 0),
                user_input.get("education", 0),
                user_input.get("miscellaneous", 0),
            ]
        )
        savings = income - expenses
        savings_rate = savings / income if income > 0 else 0
        debt_burden = (user_input.get("loan_repayment", 0) + user_input.get("rent", 0)) / income if income > 0 else 0

        # Feature contributions
        feature_contributions = []

        # Savings rate contribution
        if savings_rate > 0.3:
            savings_contribution = "High savings capacity indicates strong investment readiness"
            savings_score = 0.9
        elif savings_rate > 0.15:
            savings_contribution = "Moderate savings capacity with room for optimization"
            savings_score = 0.6
        else:
            savings_contribution = "Low savings rate - emergency fund priority recommended"
            savings_score = 0.3

        feature_contributions.append(
            {
                "feature": "savings_rate",
                "value": round(savings_rate * 100, 2),
                "weight": self.feature_weights["savings_rate"],
                "contribution": round(savings_score * self.feature_weights["savings_rate"], 3),
                "interpretation": savings_contribution,
            }
        )

        # Debt burden contribution
        if debt_burden < 0.3:
            debt_contribution = "Low debt burden allows for aggressive investing"
            debt_score = 0.8
        elif debt_burden < 0.5:
            debt_contribution = "Moderate debt - balance debt repayment with investing"
            debt_score = 0.5
        else:
            debt_contribution = "High debt burden - prioritize debt reduction"
            debt_score = 0.2

        feature_contributions.append(
            {
                "feature": "debt_burden",
                "value": round(debt_burden * 100, 2),
                "weight": self.feature_weights["debt_burden"],
                "contribution": round(debt_score * self.feature_weights["debt_burden"], 3),
                "interpretation": debt_contribution,
            }
        )

        # Cluster-specific reasoning
        cluster_reasoning = {
            0: {
                "name": "Financially Stressed",
                "characteristics": [
                    "Low or negative savings rate",
                    "High debt-to-income ratio",
                    "Minimal emergency fund",
                ],
                "recommendation": "Focus on building emergency fund before investing",
                "priority_actions": [
                    "Create budget to identify expense reduction opportunities",
                    "Build emergency fund to ₹50,000-₹100,000",
                    "Address high-interest debt first",
                ],
            },
            1: {
                "name": "Balanced Planner",
                "characteristics": [
                    "Moderate savings rate (15-30%)",
                    "Manageable debt levels",
                    "Some emergency savings",
                ],
                "recommendation": "Start small SIP while building emergency fund",
                "priority_actions": [
                    "Complete emergency fund to 3-6 months expenses",
                    "Start SIP of ₹1,000-₹5,000 monthly",
                    "Consider term insurance if not covered",
                ],
            },
            2: {
                "name": "Investment Ready",
                "characteristics": [
                    "High savings rate (>30%)",
                    "Low debt burden",
                    "Adequate emergency fund",
                ],
                "recommendation": "Aggressive wealth building through diversified portfolio",
                "priority_actions": [
                    "Increase SIP to 20-30% of income",
                    "Diversify across equity, debt, and gold",
                    "Consider tax-advantaged instruments (ELSS, NPS)",
                ],
            },
        }

        cluster_info = cluster_reasoning.get(cluster_id, cluster_reasoning.get(1, cluster_reasoning[1]))

        return {
            "segment": segment,
            "cluster_id": cluster_id,
            "feature_weights": self.feature_weights,
            "feature_contributions": feature_contributions,
            "cluster_characteristics": cluster_info["characteristics"],
            "cluster_recommendation": cluster_info["recommendation"],
            "priority_actions": cluster_info["priority_actions"],
            "reasoning_summary": f"Based on your {round(savings_rate*100, 1)}% savings rate and {round(debt_burden*100, 1)}% debt burden, you are classified as {segment}.",
        }

    def get_global_stats(self) -> Dict[str, Any]:
        """Return global system statistics for the dashboard."""
        return {
            "total_assets_managed": 2400000000,  # $2.4B simulated
            "avg_yield": 12.4,
            "active_investors": 125000,
            "total_sips_active": 450000,
            "platform_uptime": 99.97,
            "total_users": 150000,
            "verified_users": 142500,
            "avg_monthly_contribution": 8500,
            "top_performing_segment": "Investment Ready",
            "system_health": "operational",
        }

    def get_notifications(self, user_segment: str = "Balanced Planner") -> List[Dict[str, Any]]:
        """Return personalized AI alerts and insights for the user."""
        notifications = []

        # General notifications
        notifications.append(
            {
                "id": "notif_1",
                "type": "insight",
                "priority": "medium",
                "title": "Market Update",
                "message": "Indian markets have shown resilience with Nifty up 2.3% this month.",
                "timestamp": "2026-05-02T10:00:00Z",
                "read": False,
            }
        )

        # Segment-specific notifications
        if user_segment == "Financially Stressed":
            notifications.append(
                {
                    "id": "notif_2",
                    "type": "alert",
                    "priority": "high",
                    "title": "Emergency Fund Priority",
                    "message": "Building an emergency fund should be your first financial goal. Aim for ₹50,000 as a starting point.",
                    "timestamp": "2026-05-01T08:00:00Z",
                    "read": False,
                }
            )
        elif user_segment == "Balanced Planner":
            notifications.append(
                {
                    "id": "notif_3",
                    "type": "tip",
                    "priority": "medium",
                    "title": "SIP Consistency Tip",
                    "message": "Users who maintain consistent SIPs for 3+ years see 15% better returns due to rupee cost averaging.",
                    "timestamp": "2026-05-02T14:30:00Z",
                    "read": False,
                }
            )
        elif user_segment == "Investment Ready":
            notifications.append(
                {
                    "id": "notif_4",
                    "type": "insight",
                    "priority": "low",
                    "title": "Tax Planning Opportunity",
                    "message": "Consider ELSS funds for tax-saving under Section 80C with potential 12-15% returns.",
                    "timestamp": "2026-05-03T09:00:00Z",
                    "read": False,
                }
            )

        return notifications
