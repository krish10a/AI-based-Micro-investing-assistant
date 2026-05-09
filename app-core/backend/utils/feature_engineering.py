"""Feature engineering functions - shared between training and inference."""

from typing import Dict, List, Tuple, Any


def compute_total_expenses(row: Dict) -> float:
    """Sum all spending categories to get total monthly outflow."""
    cats = [
        "rent", "loan_repayment", "insurance", "groceries", "transport",
        "eating_out", "entertainment", "utilities", "healthcare", "education",
        "miscellaneous"
    ]
    return sum(row.get(c, 0.0) for c in cats)


def compute_savings_ratio(income: float, total_expenses: float) -> float:
    """Compute savings ratio (savings / income)."""
    if income <= 0:
        return 0.0
    return (income - total_expenses) / income


def compute_expense_ratio(income: float, total_expenses: float) -> float:
    """Compute expense ratio (expenses / income)."""
    if income <= 0:
        return 0.0
    return total_expenses / income


def build_features(user_input: Dict) -> Tuple[List[float], float, float, float]:
    """
    Build feature vector from user input.

    Returns:
        tuple of (feature_vector, income, total_expenses, savings)
    """
    income = user_input.get("income", 0.0)
    total_expenses = compute_total_expenses(user_input)
    savings = income - total_expenses
    savings_ratio = compute_savings_ratio(income, total_expenses)
    expense_ratio = compute_expense_ratio(income, total_expenses)

    # Clip impossible values
    savings_ratio = max(-1.0, min(1.5, savings_ratio))
    expense_ratio = max(0.0, min(1.5, expense_ratio))

    return [savings_ratio, expense_ratio], income, total_expenses, savings


def build_extended_features(user_input: Dict) -> Dict[str, Any]:
    """
    Build extended feature set with all derived metrics.

    Returns comprehensive feature dict for ML and rule-based systems.
    """
    income = user_input.get("income", 0.0)
    rent = user_input.get("rent", 0.0)
    loan_repayment = user_input.get("loan_repayment", 0.0)
    insurance = user_input.get("insurance", 0.0)
    groceries = user_input.get("groceries", 0.0)
    transport = user_input.get("transport", 0.0)
    eating_out = user_input.get("eating_out", 0.0)
    entertainment = user_input.get("entertainment", 0.0)
    utilities = user_input.get("utilities", 0.0)
    healthcare = user_input.get("healthcare", 0.0)
    education = user_input.get("education", 0.0)
    miscellaneous = user_input.get("miscellaneous", 0.0)
    dependents = user_input.get("dependents", 1)

    income_safe = income if income > 0 else 1.0

    # Category totals
    essentials = rent + groceries + transport + utilities + healthcare
    obligations = loan_repayment + insurance
    lifestyle = eating_out + entertainment + miscellaneous
    future_capacity = education

    total_expenses = essentials + obligations + lifestyle + future_capacity
    savings = income - total_expenses

    # Ratios
    savings_ratio = savings / income_safe
    expense_ratio = total_expenses / income_safe
    essential_ratio = essentials / income_safe
    obligations_ratio = obligations / income_safe
    lifestyle_ratio = lifestyle / income_safe
    fixed_obligation_ratio = (rent + loan_repayment) / income_safe
    discretionary_ratio = (eating_out + entertainment + miscellaneous) / income_safe

    # Extended features for ML
    extended_features = [
        savings_ratio,
        expense_ratio,
        essential_ratio,
        obligations_ratio,
        lifestyle_ratio,
        fixed_obligation_ratio,
        discretionary_ratio,
        dependents * 0.01,  # Normalized dependent count
        education / income_safe,  # Education investment ratio
    ]

    return {
        "basic": {
            "income": income,
            "total_expenses": total_expenses,
            "savings": savings,
            "savings_ratio": savings_ratio,
            "expense_ratio": expense_ratio
        },
        "category_breakdown": {
            "essentials": essentials,
            "obligations": obligations,
            "lifestyle": lifestyle,
            "future_capacity": future_capacity
        },
        "ratios": {
            "essential_ratio": essential_ratio,
            "obligations_ratio": obligations_ratio,
            "lifestyle_ratio": lifestyle_ratio,
            "fixed_obligation_ratio": fixed_obligation_ratio,
            "discretionary_ratio": discretionary_ratio
        },
        "extended_features": extended_features
    }
