"""Main recommendation service that orchestrates ML + Financial Intelligence."""

import logging
from typing import Dict, Any, List

from services.ml_service import MLService
from services.nim_service import NIMService
from utils.financial_diagnosis import compute_financial_metrics, classify_financial_state, FinancialState
from utils.expense_intelligence import analyze_expenses, get_expense_summary
from utils.goal_allocation import compute_goal_based_allocation
from utils.policy_guardrails import PolicyGuardrails

logger = logging.getLogger(__name__)


class RecommendationService:
    """Orchestrates ML inference and financial intelligence."""

    def __init__(self):
        self.ml_service = MLService()
        self.nim_service = NIMService()
        self.guardrails = PolicyGuardrails()

    def analyze_user(self, user_input: Dict[str, Any], skip_gemini: bool = False) -> Dict[str, Any]:
        """
        Full analysis flow: Financial diagnosis + ML inference + Policy guardrails + Goal allocation.

        Args:
            user_input: User financial data
            skip_gemini: If True, skip NIM and return ML-only response

        Returns:
            Complete recommendation response with structured dashboard data
        """
        try:
            # Step 1: Financial Diagnosis Layer
            financial_metrics = compute_financial_metrics(user_input)

            # Step 2: Expense Intelligence
            expense_insights = analyze_expenses(user_input)
            expense_summary = get_expense_summary(user_input)

            # Step 3: ML Inference
            ml_result = self.ml_service.analyze(user_input)

            # Step 4: Apply Policy Guardrails (BEFORE goal allocation)
            ml_result, guardrails_triggered = self.guardrails.apply_guardrails(ml_result, user_input)

            # Step 5: Goal-Based Allocation (after guardrails)
            goal_allocation = compute_goal_based_allocation(
                savings=financial_metrics.net_surplus,
                income=financial_metrics.monthly_income,
                financial_state=financial_metrics.financial_state.value,
                health_score=financial_metrics.financial_health_score,
                alerts=financial_metrics.alerts,
                dependents=user_input.get("dependents", 1),
                goals=user_input.get("goals", [])
            )

            # Step 6: Generate NIM explanation (optional)
            nim_explanation = None
            if not skip_gemini:
                try:
                    nim_explanation = self.nim_service.generate_explanation({
                        "segment": financial_metrics.financial_state.value,
                        "recommended_plan": self._get_recommended_plan(financial_metrics),
                        "suggested_monthly_investment": goal_allocation["total_monthly_investment"],
                        "investment_appetite": self._get_investment_appetite(financial_metrics),
                        "confidence": self._compute_confidence(financial_metrics, ml_result),
                        "financial_summary_dict": {
                            "income": financial_metrics.monthly_income,
                            "savings": financial_metrics.net_surplus,
                            "savings_ratio": financial_metrics.savings_rate
                        },
                        "portfolio": goal_allocation,
                        "expense_summary": {
                            "obligations": {
                                "insurance": user_input.get("insurance", 0),
                                "dependents": user_input.get("dependents", 1)
                            }
                        }
                    })
                except Exception as e:
                    logger.warning(f"NIM failed, returning ML-only response: {e}")

            # Step 7: Assemble final response
            return self._build_response(
                financial_metrics=financial_metrics,
                expense_insights=expense_insights,
                expense_summary=expense_summary,
                ml_result=ml_result,
                goal_allocation=goal_allocation,
                nim_explanation=nim_explanation
            )

        except Exception as e:
            logger.error(f"Recommendation service failed: {e}")
            raise

    def _build_response(
        self,
        financial_metrics,
        expense_insights,
        expense_summary,
        ml_result: Dict[str, Any],
        goal_allocation: Dict[str, Any],
        nim_explanation: str
    ) -> Dict[str, Any]:
        """Build structured response with all components."""

        profile = self._build_profile(ml_result, financial_metrics, goal_allocation)
        snapshot = self._build_snapshot(financial_metrics)
        portfolio = self._build_portfolio(goal_allocation)
        reasoning = self._build_reasoning(financial_metrics, expense_insights, goal_allocation)

        legacy = {
            "segment": financial_metrics.financial_state.value,
            "risk_level": ml_result.get("risk_level", self._get_risk_level(financial_metrics)),
            "suggested_monthly_investment": goal_allocation["total_monthly_investment"],
            "investment_appetite": self._get_investment_appetite(financial_metrics),
            "reason_codes": ml_result.get("reason_codes", []),
            "confidence": self._compute_confidence(financial_metrics, ml_result),
            "financial_summary": f"Monthly income: {financial_metrics.monthly_income:,.0f}, Monthly savings: {financial_metrics.net_surplus:,.0f} (Savings rate: {financial_metrics.savings_rate*100:.1f}%)",
            "financial_summary_dict": {
                "income": financial_metrics.monthly_income,
                "total_expenses": financial_metrics.total_expenses,
                "savings": financial_metrics.net_surplus,
                "savings_ratio": financial_metrics.savings_rate
            },
            "safe_action": self._get_safe_action(financial_metrics, goal_allocation),
            "nim_explanation": nim_explanation,
            "warnings": [a["message"] for a in financial_metrics.alerts],
            "income_level": "high" if financial_metrics.monthly_income >= 500000 else "normal",
            "recommended_plan": self._get_recommended_plan(financial_metrics),
            "allocation_details": {a["goal_name"]: f"₹{a['amount']:,.0f}/month ({a['percentage']*100:.0f}%)" for a in goal_allocation["allocations"]}
        }

        return {
            "profile": profile,
            "financial_snapshot": snapshot,
            "portfolio": portfolio,
            "reasoning": reasoning,
            "health_score": {
                "total_score": financial_metrics.financial_health_score,
                "rating": self._get_health_rating(financial_metrics.financial_health_score)
            },
            "insights": [
                {
                    "category": ei.category,
                    "severity": ei.severity,
                    "message": ei.message,
                    "recommendation": ei.recommendation
                }
                for ei in expense_insights
            ],
            "expense_summary": expense_summary,
            "alerts": [
                {
                    "type": alert["type"],
                    "severity": alert["severity"],
                    "message": alert["message"]
                }
                for alert in financial_metrics.alerts
            ],
            **legacy
        }

    def _build_profile(self, ml_result: Dict, financial_metrics, goal_allocation: Dict[str, Any]) -> Dict[str, Any]:
        """Build user-facing profile card."""
        return {
            "user_segment": financial_metrics.financial_state.value,
            "segment_explanation": self._get_segment_explanation(financial_metrics.financial_state),
            "risk_level": ml_result.get("risk_level", self._get_risk_level(financial_metrics)),
            "suggested_monthly_investment": goal_allocation.get("total_monthly_investment", 0),
            "investment_appetite": self._get_investment_appetite(financial_metrics),
            "confidence": self._compute_confidence(financial_metrics, ml_result),
            "recommended_plan": self._get_recommended_plan(financial_metrics)
        }

    def _build_snapshot(self, financial_metrics) -> Dict[str, Any]:
        """Build financial snapshot card."""
        return {
            "monthly_income": financial_metrics.monthly_income,
            "monthly_expenses": financial_metrics.total_expenses,
            "monthly_savings": financial_metrics.net_surplus,
            "savings_rate": financial_metrics.savings_rate,
            "expense_ratio": financial_metrics.expense_ratio,
            "essential_ratio": financial_metrics.essential_expense_ratio,
            "obligations_ratio": financial_metrics.fixed_obligation_ratio,
            "lifestyle_ratio": financial_metrics.discretionary_expense_ratio
        }

    def _build_portfolio(self, goal_allocation: Dict[str, Any]) -> Dict[str, Any]:
        """Build portfolio allocation card."""
        return {
            "primary_action": self._get_safe_action(None, goal_allocation),
            "allocation_breakdown": {
                a["goal_name"]: f"₹{a['amount']:,.0f}/month"
                for a in goal_allocation["allocations"]
            },
            "total_monthly_investment": goal_allocation["total_monthly_investment"],
            "allocations": goal_allocation["allocations"]
        }

    def _build_reasoning(self, financial_metrics, expense_insights, goal_allocation) -> Dict[str, Any]:
        """Build reasoning and warnings card - actionable, no fluff."""
        state = financial_metrics.financial_state
        is_high_income = financial_metrics.monthly_income > 500000
        why_fits = []

        if financial_metrics.savings_rate > 0.30:
            why_fits.append(f'Excellent savings rate of {financial_metrics.savings_rate*100:.1f}% (well above the 20% benchmark)')
        if financial_metrics.fixed_obligation_ratio < 0.30:
            why_fits.append(f'Managed debt burden: Only {financial_metrics.fixed_obligation_ratio*100:.1f}% of income goes to fixed costs')
        if financial_metrics.discretionary_expense_ratio < 0.15:
            why_fits.append('Disciplined lifestyle spending: High efficiency in discretionary costs')

        if state == FinancialState.FINANCIALLY_STRESSED:
            why_fits.append('Foundational Step: Prioritizing stability over market risk')
        elif state == FinancialState.WEALTH_ACCELERATOR:
            why_fits.append('Multi-Asset Advantage: Diversified enough to weather market volatility')

        watch_out = [a['message'] for a in financial_metrics.alerts]
        if not watch_out:
            if is_high_income:
                watch_out.append('Review portfolio quarterly; consider consulting fee-only advisor')
            else:
                watch_out.append('Review this plan if income or expenses change significantly')

        next_step = self._get_safe_action(financial_metrics, goal_allocation)

        return {
            'why_this_fits': why_fits,
            'watch_out': watch_out,
            'next_step': next_step
        }

    def _get_investment_appetite(self, financial_metrics) -> str:
        """Determine investment appetite based on financial state."""
        state = financial_metrics.financial_state
        if state == FinancialState.FINANCIALLY_STRESSED:
            return "Very Low"
        elif state == FinancialState.CASH_FLOW_TIGHT:
            return "Low"
        elif state == FinancialState.STABLE_BUILDER:
            return "Medium"
        elif state == FinancialState.HIGH_SURPLUS_BUILDER:
            return "High"
        else:
            return "Very High"

    def _compute_confidence(self, financial_metrics, ml_result) -> float:
        """Compute overall confidence score."""
        ml_confidence = ml_result.get("confidence", 0.5)

        if financial_metrics.financial_health_score > 70:
            return min(0.9, ml_confidence + 0.1)
        elif financial_metrics.financial_health_score < 40:
            return max(0.3, ml_confidence - 0.1)
        return ml_confidence

    def _get_recommended_plan(self, financial_metrics) -> str:
        """Get recommended plan based on financial state."""
        state = financial_metrics.financial_state
        plans = {
            FinancialState.FINANCIALLY_STRESSED: "Emergency Fund & Debt Management",
            FinancialState.CASH_FLOW_TIGHT: "Stabilization & Small SIP",
            FinancialState.STABLE_BUILDER: "Balanced SIP Portfolio",
            FinancialState.HIGH_SURPLUS_BUILDER: "Aggressive SIP with Direct Stocks",
            FinancialState.WEALTH_ACCELERATOR: "Multi-Asset Wealth Building"
        }
        return plans.get(state, "Balanced Investment Approach")

    def _get_risk_level(self, financial_metrics) -> Dict[str, str]:
        """Determine risk level with color coding."""
        state = financial_metrics.financial_state
        if state == FinancialState.FINANCIALLY_STRESSED:
            return {"label": "LOW", "color": "success", "description": "Capital Preservation"}
        elif state == FinancialState.CASH_FLOW_TIGHT:
            return {"label": "MEDIUM-LOW", "color": "info", "description": "Conservative Growth"}
        elif state == FinancialState.STABLE_BUILDER:
            return {"label": "MEDIUM", "color": "warning", "description": "Balanced"}
        elif state == FinancialState.HIGH_SURPLUS_BUILDER:
            return {"label": "HIGH", "color": "error", "description": "Growth Focused"}
        else:
            return {"label": "AGGRESSIVE", "color": "error", "description": "Aggressive Growth"}

    def _get_segment_explanation(self, state: FinancialState) -> str:
        """Provide a human-readable explanation of the financial segment."""
        explanations = {
            FinancialState.FINANCIALLY_STRESSED: "You're currently in a 'survival' phase where expenses are nearly equal to or exceed your income. Your primary goal is to plug leakages and build a safety net before thinking about the stock market.",
            FinancialState.CASH_FLOW_TIGHT: "You have your basics covered but don't have much room for error. You're ready to start 'micro-investing'—small, consistent amounts that won't strain your daily life.",
            FinancialState.STABLE_BUILDER: "You have a healthy gap between what you earn and what you spend. You're in a prime position to build long-term wealth through disciplined, automated investing.",
            FinancialState.HIGH_SURPLUS_BUILDER: "You're a super-saver. Because your 'financial runway' is long, you can afford to take more market risks to accelerate your path to financial freedom.",
            FinancialState.WEALTH_ACCELERATOR: "You're in the elite tier of savers. Your income far exceeds your lifestyle costs, allowing you to deploy capital aggressively across multiple asset classes for maximum velocity."
        }
        return explanations.get(state, "We're still analyzing your specific profile to provide a detailed explanation.")

    def _get_health_rating(self, score: float) -> str:
        """Convert numeric health score to rating label."""
        if score >= 80:
            return "Excellent"
        elif score >= 60:
            return "Good"
        elif score >= 40:
            return "Fair"
        else:
            return "Needs Improvement"

    def _get_safe_action(self, financial_metrics, goal_allocation) -> str:
        """Determine the safest first action."""
        if not financial_metrics:
            return "Start investing consistently"

        state = financial_metrics.financial_state
        total_investment = goal_allocation.get("total_monthly_investment", 0) if goal_allocation else 0
        allocations = goal_allocation.get("allocations", []) if goal_allocation else []

        if state == FinancialState.FINANCIALLY_STRESSED:
            return "Action: Stop all non-essential spending and build a ₹10,000 mini-emergency fund"
        elif state == FinancialState.CASH_FLOW_TIGHT:
            first_alloc = allocations[0]["amount"] if allocations else 1000
            return f"Action: Set up an auto-debit for ₹{min(first_alloc, 2000):,.0f} to a Liquid Fund by the 5th of next month"
        elif state == FinancialState.STABLE_BUILDER:
            return f"Action: Invest ₹{total_investment/2:,.0f} in an Index Fund (Nifty 50) to start your core portfolio"
        elif state == FinancialState.HIGH_SURPLUS_BUILDER:
            return f"Action: Deploy the first ₹{total_investment * 0.4:,.0f} into Equity SIPs and balance in Debt/Gold"
        else:
            primary_goal = allocations[0]["goal_name"] if allocations else "Multi-Asset"
            return f"Action: Prioritize the '{primary_goal}' bucket by allocating ₹{allocations[0]['amount'] if allocations else total_investment:,.0f} immediately"

    async def chat(self, message: str, user_profile: Dict[str, Any]) -> str:
        """Handle conversational follow-up."""
        return self.nim_service.chat_explanation(message, user_profile)
