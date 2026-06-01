"""Policy guardrails - final defense layer for compliance and safety."""

from typing import Dict, List, Any, Tuple
from enum import Enum

from utils.liquidity_rules import LiquidityRules


class SafetyLevel(Enum):
    """Safety level for recommendations."""
    CRITICAL = "critical"
    WARNING = "warning"
    CAUTION = "caution"
    INFO = "info"
    SAFE = "safe"


class PolicyGuardrails:
    """
    Policy guardrails layer - final defense before response.

    This layer ensures:
    1. Zero savings → Emergency fund recommendation
    2. Severe overspending → Dampened advice
    3. Stock tip requests → Refusal + redirect
    4. Low confidence → Caution banner
    5. Compliance with regulatory requirements
    6. Liquidity guardrails → Emergency fund priority
    """

    def __init__(self):
        # Thresholds
        self.ZERO_SAVINGS_THRESHOLD = 0
        self.LOW_SAVINGS_RATIO = 0.10
        self.HIGH_DEBT_RATIO = 0.40
        self.LOW_CONFIDENCE_THRESHOLD = 0.50
        self.HIGH_DISCRETIONARY_RATIO = 0.20

        # Initialize liquidity rules
        self.liquidity_rules = LiquidityRules()

    def apply_guardrails(
        self,
        recommendation: Dict[str, Any],
        user_input: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Apply policy guardrails to recommendation.

        Returns:
            Tuple of (modified_recommendation, triggered_guardrails)
        """
        guardrails_triggered = []

        # Step 1: Apply liquidity guardrails FIRST (highest priority)
        recommendation, liquidity_triggered = self.liquidity_rules.apply_liquidity_guardrails(
            recommendation, user_input
        )
        guardrails_triggered.extend(liquidity_triggered)

        # If liquidity guardrails forced emergency mode, skip other checks
        if any(rule.get("type") == "liquidity_insufficient" for rule in liquidity_triggered):
            return recommendation, guardrails_triggered

        # Extract values
        savings = recommendation.get("financial_summary", {}).get("savings", 0)
        savings_ratio = recommendation.get("financial_summary", {}).get("savings_ratio", 0)
        confidence = recommendation.get("confidence", 0.5)
        segment = recommendation.get("segment", "")

        loan_repayment = user_input.get("loan_repayment", 0)
        income = user_input.get("income", 1)
        insurance = user_input.get("insurance", 0)
        dependents = user_input.get("dependents", 0)

        debt_ratio = loan_repayment / income if income > 0 else 0
        discretionary = (
            user_input.get("eating_out", 0) +
            user_input.get("entertainment", 0) +
            user_input.get("miscellaneous", 0)
        )
        discretionary_ratio = discretionary / income if income > 0 else 0

        # Guardrail 1: Zero/Negative Savings
        if savings <= self.ZERO_SAVINGS_THRESHOLD:
            recommendation = self._enforce_emergency_mode(recommendation)
            guardrails_triggered.append({
                "type": "zero_savings",
                "level": SafetyLevel.CRITICAL.value,
                "message": "Forced emergency fund mode - zero investment recommended"
            })

        # Guardrail 2: Low Savings Ratio
        elif savings_ratio < self.LOW_SAVINGS_RATIO:
            recommendation = self._cap_risk_level(recommendation)
            guardrails_triggered.append({
                "type": "low_savings_ratio",
                "level": SafetyLevel.WARNING.value,
                "message": f"Savings ratio {savings_ratio*100:.1f}% below threshold - risk capped"
            })

        # Guardrail 3: High Debt Pressure
        if debt_ratio > self.HIGH_DEBT_RATIO:
            recommendation = self._prioritize_debt_reduction(recommendation)
            guardrails_triggered.append({
                "type": "high_debt",
                "level": SafetyLevel.WARNING.value,
                "message": f"Debt ratio {debt_ratio*100:.1f}% exceeds threshold - debt reduction prioritized"
            })

        # Guardrail 4: Low Confidence
        if confidence < self.LOW_CONFIDENCE_THRESHOLD:
            guardrails_triggered.append({
                "type": "low_confidence",
                "level": SafetyLevel.CAUTION.value,
                "message": f"Model confidence {confidence*100:.1f}% below threshold - caution advised"
            })

        # Guardrail 5: High Discretionary Spending
        if discretionary_ratio > self.HIGH_DISCRETIONARY_RATIO:
            guardrails_triggered.append({
                "type": "lifestyle_inflation",
                "level": SafetyLevel.INFO.value,
                "message": f"Discretionary spending {discretionary_ratio*100:.1f}% - consider reducing"
            })

        # Guardrail 6: Missing Protection
        if dependents > 0 and insurance < income * 0.05:
            guardrails_triggered.append({
                "type": "missing_protection",
                "level": SafetyLevel.WARNING.value,
                "message": f"With {dependents} dependent(s), insurance coverage is inadequate"
            })

        # Add guardrail warnings to recommendation
        if guardrails_triggered:
            existing_warnings = recommendation.get("warnings", [])
            for gr in guardrails_triggered:
                if gr["message"] not in existing_warnings:
                    existing_warnings.append(gr["message"])
            recommendation["warnings"] = existing_warnings
            recommendation["guardrails_triggered"] = guardrails_triggered

        return recommendation, guardrails_triggered

    def _enforce_emergency_mode(self, recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """Force emergency fund mode for zero/negative savings."""
        recommendation["suggested_monthly_investment"] = 0
        recommendation["safe_action"] = (
            "Build an emergency fund of 3-6 months expenses before any investing. "
            "Focus on reducing expenses and increasing income first."
        )
        recommendation["investment_appetite"] = "Very Low"
        recommendation["risk_level"] = {"label": "LOW", "color": "success", "description": "Emergency Focus"}

        # Override allocation to emergency fund only
        recommendation["allocation_details"] = {
            "Emergency Fund": "Priority: Build 3-6 months of expenses in liquid savings"
        }

        return recommendation

    def _cap_risk_level(self, recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """Cap risk level for low savings ratio."""
        recommendation["risk_level"] = {"label": "LOW", "color": "success", "description": "Capped due to low savings"}
        recommendation["investment_appetite"] = "Low"

        # Reduce suggested investment
        current_investment = recommendation.get("suggested_monthly_investment", 0)
        savings = recommendation.get("financial_summary", {}).get("savings", 0)
        capped_investment = min(current_investment, savings * 0.20)
        recommendation["suggested_monthly_investment"] = capped_investment

        return recommendation

    def _prioritize_debt_reduction(self, recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """Prioritize debt reduction for high debt ratio."""
        # Adjust allocation to include debt paydown
        savings = recommendation.get("financial_summary", {}).get("savings", 0)
        debt_paydown = savings * 0.40  # 40% to debt

        existing_allocation = recommendation.get("allocation_details", {})
        existing_allocation["Debt Repayment"] = f"Priority: Pay down high-interest debt ({debt_paydown:,.0f}/month)"

        recommendation["allocation_details"] = existing_allocation
        recommendation["safe_action"] = (
            f"Prioritize paying down debt with ₹{debt_paydown:,.0f}/month. "
            "Once debt ratio drops below 30%, revisit investment options."
        )

        return recommendation

    def check_stock_tip_request(self, user_message: str) -> bool:
        """
        Check if user is asking for stock tips.

        Returns True if request should be refused.
        """
        stock_keywords = [
            "stock", "share", "buy", "sell", "tip", "recommendation",
            "which stock", "what to buy", "good stock", "best stock",
            "tata steel", "reliance", "infy", "hdfc", "icici",
            "nifty", "banknifty", "fno", "futures", "options"
        ]

        message_lower = user_message.lower()
        return any(keyword in message_lower for keyword in stock_keywords)

    def generate_refusal_response(self) -> str:
        """Generate standardized refusal for stock tip requests."""
        return (
            "I cannot recommend specific stocks or securities. "
            "My role is to provide educational guidance on investment strategies, "
            "not individual equity recommendations. "
            "For stock-specific advice, please consult a SEBI-registered investment advisor. "
            "I can help you understand asset allocation, risk management, and long-term wealth building strategies."
        )

    def enforce_domain_boundary(self, user_message: str) -> Tuple[bool, str]:
        """
        Check if user message is within allowed domain.

        Returns:
            Tuple of (is_within_domain, response_if_outside)
        """
        out_of_scope_keywords = [
            "market will go", "crash", "boom", "predict", "guarantee",
            "100% return", "double my money", "get rich", "quick profit",
            "intraday", "swing trade", "day trading"
        ]

        message_lower = user_message.lower()
        for keyword in out_of_scope_keywords:
            if keyword in message_lower:
                return False, self._generate_domain_refusal()

        return True, ""

    def _generate_domain_refusal(self) -> str:
        """Generate refusal for out-of-scope requests."""
        return (
            "I cannot provide market predictions, guaranteed returns, or trading advice. "
            "I'm designed to help you understand investment strategies and build long-term wealth. "
            "I can explain concepts like asset allocation, risk management, and the benefits of consistent investing."
        )
