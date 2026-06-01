"""Liquidity rules for investment recommendations.

This module provides operationalized liquidity guardrails including:
- Minimum cash buffer calculation (3 months essential expenses)
- Emergency fund adequacy assessment
- Investment caps based on liquidity status
"""

from typing import Dict, Any, Tuple
from enum import Enum


class LiquidityStatus(Enum):
    """Liquidity status based on emergency fund coverage."""
    INSUFFICIENT = "insufficient"  # <3 months emergency fund
    MINIMAL = "minimal"           # 3-6 months
    ADEQUATE = "adequate"          # 6-12 months
    STRONG = "strong"              # >12 months


class LiquidityRules:
    """
    Operationalized liquidity guardrails for investment recommendations.

    Rules:
    - Minimum cash buffer = 3 months essential expenses
    - Investment caps based on liquidity status
    - Emergency fund priority before any investment
    """

    # Operationalized cash buffer
    MIN_EMERGENCY_MONTHS = 3
    RECOMMENDED_EMERGENCY_MONTHS = 6

    # Essential expense categories
    ESSENTIAL_EXPENSES = ["rent", "groceries", "utilities", "transport", "healthcare"]

    # Investment caps based on liquidity status
    LIQUIDITY_INVESTMENT_CAPS = {
        LiquidityStatus.INSUFFICIENT: 0.0,  # No investment
        LiquidityStatus.MINIMAL: 0.1,        # 10% of savings
        LiquidityStatus.ADEQUATE: 0.3,       # 30% of savings
        LiquidityStatus.STRONG: 0.5          # 50% of savings
    }

    # Income floor for investment recommendations
    MIN_INCOME_FOR_INVESTMENT = 25000  # Below this, no investment recommended

    def __init__(self):
        self.triggered_rules: list = []

    def assess_liquidity(
        self,
        user_input: Dict[str, Any]
    ) -> Tuple[LiquidityStatus, float, float]:
        """
        Assess liquidity status based on emergency fund coverage.

        Args:
            user_input: User financial data

        Returns:
            Tuple of (liquidity_status, months_covered, required_emergency_fund)
        """
        emergency_fund = user_input.get("emergency_fund_corpus", 0)
        essential_expenses = self._compute_essential_expenses(user_input)

        if essential_expenses == 0:
            return LiquidityStatus.MINIMAL, 0.0, 0.0

        months_covered = emergency_fund / essential_expenses
        required_emergency_fund = essential_expenses * self.MIN_EMERGENCY_MONTHS

        if months_covered < self.MIN_EMERGENCY_MONTHS:
            status = LiquidityStatus.INSUFFICIENT
        elif months_covered < self.RECOMMENDED_EMERGENCY_MONTHS:
            status = LiquidityStatus.MINIMAL
        elif months_covered < 12:
            status = LiquidityStatus.ADEQUATE
        else:
            status = LiquidityStatus.STRONG

        return status, months_covered, required_emergency_fund

    def get_investment_cap(
        self,
        user_input: Dict[str, Any]
    ) -> float:
        """
        Get investment cap based on liquidity status.

        Args:
            user_input: User financial data

        Returns:
            Investment multiplier (0.0 to 0.5)
        """
        liquidity_status, _, _ = self.assess_liquidity(user_input)
        return self.LIQUIDITY_INVESTMENT_CAPS[liquidity_status]

    def should_allow_investment(
        self,
        user_input: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Determine if investment should be allowed based on liquidity.

        Args:
            user_input: User financial data

        Returns:
            Tuple of (should_invest, reason)
        """
        income = user_input.get("income", 0)
        liquidity_status, months_covered, required_emergency_fund = self.assess_liquidity(user_input)

        # Check income floor
        if income < self.MIN_INCOME_FOR_INVESTMENT:
            return False, (
                f"Income (₹{income:,}) is below minimum threshold (₹{self.MIN_INCOME_FOR_INVESTMENT:,}) "
                "for investment recommendations. Focus on building emergency fund first."
            )

        # Check liquidity status
        if liquidity_status == LiquidityStatus.INSUFFICIENT:
            return False, (
                f"Emergency fund covers only {months_covered:.1f} months of essential expenses. "
                f"Build emergency fund to ₹{required_emergency_fund:,.0f} "
                f"({self.MIN_EMERGENCY_MONTHS} months) before investing."
            )

        return True, ""

    def apply_liquidity_guardrails(
        self,
        recommendation: Dict[str, Any],
        user_input: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], list]:
        """
        Apply liquidity guardrails to recommendation.

        Args:
            recommendation: ML recommendation
            user_input: User financial data

        Returns:
            Tuple of (modified_recommendation, triggered_rules)
        """
        self.triggered_rules = []
        liquidity_status, months_covered, required_emergency_fund = self.assess_liquidity(user_input)

        # Check if investment should be allowed
        should_invest, reason = self.should_allow_investment(user_input)

        if not should_invest:
            # Force emergency fund mode
            recommendation["suggested_monthly_investment"] = 0
            recommendation["investment_appetite"] = "Very Low"
            recommendation["risk_level"] = {
                "label": "LOW",
                "color": "success",
                "description": "Emergency Focus"
            }
            recommendation["safe_action"] = reason

            # Override allocation
            recommendation["allocation_details"] = {
                "Emergency Fund": f"Priority: Build ₹{required_emergency_fund:,.0f} emergency fund"
            }

            self.triggered_rules.append({
                "type": "liquidity_insufficient",
                "level": "critical",
                "message": reason,
                "months_covered": months_covered,
                "required_emergency_fund": required_emergency_fund
            })

        else:
            # Apply investment cap based on liquidity
            investment_cap = self.get_investment_cap(user_input)
            current_investment = recommendation.get("suggested_monthly_investment", 0)
            savings = user_input.get("income", 0) - self._compute_total_expenses(user_input)

            if savings > 0:
                capped_investment = min(current_investment, savings * investment_cap)

                if capped_investment < current_investment:
                    recommendation["suggested_monthly_investment"] = capped_investment

                    self.triggered_rules.append({
                        "type": "liquidity_cap",
                        "level": "warning",
                        "message": (
                            f"Investment capped to {investment_cap*100:.0f}% of savings "
                            f"due to {liquidity_status.value} liquidity status "
                            f"({months_covered:.1f} months emergency fund coverage)."
                        ),
                        "liquidity_status": liquidity_status.value,
                        "investment_cap": investment_cap
                    })

        # Add guardrail warnings to recommendation
        if self.triggered_rules:
            existing_warnings = recommendation.get("warnings", [])
            for rule in self.triggered_rules:
                if rule["message"] not in existing_warnings:
                    existing_warnings.append(rule["message"])
            recommendation["warnings"] = existing_warnings
            recommendation["liquidity_guardrails_triggered"] = self.triggered_rules

        return recommendation, self.triggered_rules

    def _compute_essential_expenses(self, user_input: Dict[str, Any]) -> float:
        """Compute essential expenses."""
        return sum(user_input.get(field, 0) for field in self.ESSENTIAL_EXPENSES)

    def _compute_total_expenses(self, user_input: Dict[str, Any]) -> float:
        """Compute total expenses from individual categories."""
        expense_fields = [
            "rent", "loan_repayment", "insurance", "groceries", "transport",
            "eating_out", "entertainment", "utilities", "healthcare",
            "education", "miscellaneous"
        ]
        return sum(user_input.get(field, 0) for field in expense_fields)

    def get_emergency_fund_guidance(
        self,
        user_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get guidance for building emergency fund.

        Args:
            user_input: User financial data

        Returns:
            Emergency fund guidance
        """
        liquidity_status, months_covered, required_emergency_fund = self.assess_liquidity(user_input)
        current_emergency_fund = user_input.get("emergency_fund_corpus", 0)
        essential_expenses = self._compute_essential_expenses(user_input)
        savings = user_input.get("income", 0) - self._compute_total_expenses(user_input)

        gap = max(0, required_emergency_fund - current_emergency_fund)

        # Estimate time to build emergency fund
        if savings > 0:
            months_to_build = gap / savings
        else:
            months_to_build = float('inf')

        guidance = {
            "liquidity_status": liquidity_status.value,
            "months_covered": months_covered,
            "current_emergency_fund": current_emergency_fund,
            "required_emergency_fund": required_emergency_fund,
            "gap": gap,
            "essential_monthly_expenses": essential_expenses,
            "monthly_savings": savings,
            "estimated_months_to_build": months_to_build if months_to_build != float('inf') else None,
            "priority": "high" if liquidity_status == LiquidityStatus.INSUFFICIENT else "medium",
            "action": (
                f"Build emergency fund to ₹{required_emergency_fund:,.0f} "
                f"({self.MIN_EMERGENCY_MONTHS} months of essential expenses)"
            )
        }

        return guidance
