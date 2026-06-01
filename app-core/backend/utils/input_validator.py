"""Input validation utility for financial data.

This module provides defensive validation for user financial inputs,
ensuring data consistency and rejecting impossible inputs before ML processing.
"""

from typing import Dict, Any, Tuple, List
from enum import Enum


class ValidationLevel(Enum):
    """Severity level for validation issues."""
    ERROR = "error"           # Reject input completely
    WARNING = "warning"       # Allow but flag for review
    INFO = "info"             # Informational only


class ValidationError(Exception):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: str = None, level: ValidationLevel = ValidationLevel.ERROR):
        self.message = message
        self.field = field
        self.level = level
        super().__init__(message)


class InputValidator:
    """
    Defensive input validation for financial data.

    Validates:
    - Income vs expense consistency
    - Essential expenses ratio
    - Total expenses sum matches individual categories
    - Impossible inputs (negative values, absurd ratios)
    - Income floor for investment recommendations
    """

    # Validation thresholds
    MIN_INCOME_FOR_INVESTMENT = 25000  # Below this, no investment recommended
    MAX_EXPENSE_INCOME_RATIO = 1.2  # Expenses can't exceed 120% of income
    MAX_ESSENTIALS_RATIO = 0.8  # Essentials can't be >80% of income
    MIN_EMERGENCY_MONTHS = 3  # Minimum 3 months expenses for emergency fund

    # Essential expense categories
    ESSENTIAL_EXPENSES = ["rent", "groceries", "utilities", "transport", "healthcare"]

    # Reasonable bounds
    MAX_MONTHLY_INCOME = 10000000  # 1 Crore per month
    MAX_SINGLE_EXPENSE = 5000000  # 50 Lakhs for any single expense

    def __init__(self):
        self.warnings: List[str] = []
        self.errors: List[str] = []

    def validate(self, user_input: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """
        Validate user financial input.

        Args:
            user_input: Dictionary with financial data

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self.warnings = []
        self.errors = []

        try:
            self._validate_income(user_input)
            self._validate_expenses(user_input)
            self._validate_income_expense_consistency(user_input)
            self._validate_essential_expenses(user_input)
            self._validate_emergency_fund(user_input)
            self._validate_dependents(user_input)
            self._validate_goals(user_input)

            return len(self.errors) == 0, self.errors, self.warnings

        except Exception as e:
            self.errors.append(f"Validation error: {str(e)}")
            return False, self.errors, self.warnings

    def _validate_income(self, user_input: Dict[str, Any]):
        """Validate income field."""
        income = user_input.get("income", 0)

        if income < 0:
            raise ValidationError("Income cannot be negative.", "income")

        if income > self.MAX_MONTHLY_INCOME:
            raise ValidationError(
                f"Income exceeds reasonable range (₹{self.MAX_MONTHLY_INCOME:,}/month). "
                "Please verify your input.",
                "income"
            )

        # Check for suspiciously low income
        if 0 < income < 5000:
            self.warnings.append(
                f"Income of ₹{income:,} is very low. "
                "Please verify this is monthly income, not annual."
            )

    def _validate_expenses(self, user_input: Dict[str, Any]):
        """Validate individual expense fields."""
        expense_fields = [
            "rent", "loan_repayment", "insurance", "groceries", "transport",
            "eating_out", "entertainment", "utilities", "healthcare",
            "education", "miscellaneous"
        ]

        for field in expense_fields:
            value = user_input.get(field, 0)

            if value < 0:
                raise ValidationError(
                    f"{field.replace('_', ' ').title()} cannot be negative.",
                    field
                )

            if value > self.MAX_SINGLE_EXPENSE:
                raise ValidationError(
                    f"{field.replace('_', ' ').title()} exceeds reasonable range.",
                    field
                )

    def _validate_income_expense_consistency(self, user_input: Dict[str, Any]):
        """Validate that expenses are consistent with income."""
        income = user_input.get("income", 0)
        total_expenses = self._compute_total_expenses(user_input)

        if income > 0 and total_expenses > income * self.MAX_EXPENSE_INCOME_RATIO:
            raise ValidationError(
                f"Total expenses (₹{total_expenses:,}) exceed {self.MAX_EXPENSE_INCOME_RATIO*100:.0f}% "
                f"of income (₹{income:,}). Please verify your expense entries.",
                "total_expenses"
            )

        # Check for suspicious expense patterns
        if total_expenses == 0 and income > 10000:
            self.warnings.append(
                "Total expenses are zero. This is unusual. Please verify your expense entries."
            )

    def _validate_essential_expenses(self, user_input: Dict[str, Any]):
        """Validate essential expenses ratio."""
        income = user_input.get("income", 0)
        essential_expenses = self._compute_essential_expenses(user_input)
        essentials_ratio = essential_expenses / income if income > 0 else 0

        if essentials_ratio > self.MAX_ESSENTIALS_RATIO:
            self.warnings.append(
                f"Essential expenses ({essentials_ratio*100:.1f}% of income) are high. "
                "Consider reviewing your fixed costs."
            )

    def _validate_emergency_fund(self, user_input: Dict[str, Any]):
        """Validate emergency fund corpus."""
        emergency_fund = user_input.get("emergency_fund_corpus", 0)
        essential_expenses = self._compute_essential_expenses(user_input)

        if emergency_fund < 0:
            raise ValidationError("Emergency fund corpus cannot be negative.", "emergency_fund_corpus")

        # Check if emergency fund is adequate
        required_emergency_fund = essential_expenses * self.MIN_EMERGENCY_MONTHS
        if emergency_fund < required_emergency_fund and essential_expenses > 0:
            self.warnings.append(
                f"Emergency fund (₹{emergency_fund:,}) is below recommended "
                f"₹{required_emergency_fund:,} ({self.MIN_EMERGENCY_MONTHS} months of essential expenses)."
            )

    def _validate_dependents(self, user_input: Dict[str, Any]):
        """Validate dependents count."""
        dependents = user_input.get("dependents", 0)

        if dependents < 0:
            raise ValidationError("Number of dependents cannot be negative.", "dependents")

        if dependents > 50:
            raise ValidationError(
                "Number of dependents exceeds reasonable range. Please verify your input.",
                "dependents"
            )

    def _validate_goals(self, user_input: Dict[str, Any]):
        """Validate financial goals."""
        goals = user_input.get("goals", [])

        valid_goals = [
            "Retirement", "Child Education", "Home Purchase",
            "Wealth Building", "Travel", "Education Upskilling"
        ]

        for goal in goals:
            if goal not in valid_goals:
                self.warnings.append(
                    f"Goal '{goal}' is not a recognized option. "
                    f"Valid options: {', '.join(valid_goals)}"
                )

    def _compute_total_expenses(self, user_input: Dict[str, Any]) -> float:
        """Compute total expenses from individual categories."""
        expense_fields = [
            "rent", "loan_repayment", "insurance", "groceries", "transport",
            "eating_out", "entertainment", "utilities", "healthcare",
            "education", "miscellaneous"
        ]
        return sum(user_input.get(field, 0) for field in expense_fields)

    def _compute_essential_expenses(self, user_input: Dict[str, Any]) -> float:
        """Compute essential expenses."""
        return sum(user_input.get(field, 0) for field in self.ESSENTIAL_EXPENSES)

    def should_recommend_investment(self, user_input: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Determine if investment should be recommended based on income floor.

        Args:
            user_input: User financial data

        Returns:
            Tuple of (should_invest, reason)
        """
        income = user_input.get("income", 0)
        total_expenses = self._compute_total_expenses(user_input)
        savings = income - total_expenses

        if income < self.MIN_INCOME_FOR_INVESTMENT:
            return False, (
                f"Income (₹{income:,}) is below minimum threshold (₹{self.MIN_INCOME_FOR_INVESTMENT:,}) "
                "for investment recommendations. Focus on building emergency fund first."
            )

        if savings <= 0:
            return False, (
                "No savings available for investment. "
                "Focus on reducing expenses and increasing income first."
            )

        return True, ""

    def get_liquidity_status(self, user_input: Dict[str, Any]) -> str:
        """
        Determine liquidity status based on emergency fund coverage.

        Returns:
            One of: "insufficient", "minimal", "adequate", "strong"
        """
        emergency_fund = user_input.get("emergency_fund_corpus", 0)
        essential_expenses = self._compute_essential_expenses(user_input)

        if essential_expenses == 0:
            return "minimal"

        months_covered = emergency_fund / essential_expenses

        if months_covered < self.MIN_EMERGENCY_MONTHS:
            return "insufficient"
        elif months_covered < 6:
            return "minimal"
        elif months_covered < 12:
            return "adequate"
        else:
            return "strong"

    def get_investment_cap(self, user_input: Dict[str, Any]) -> float:
        """
        Get investment cap based on liquidity status.

        Returns:
            Investment multiplier (0.0 to 0.5)
        """
        liquidity_status = self.get_liquidity_status(user_input)

        caps = {
            "insufficient": 0.0,
            "minimal": 0.1,
            "adequate": 0.3,
            "strong": 0.5
        }

        return caps.get(liquidity_status, 0.0)
