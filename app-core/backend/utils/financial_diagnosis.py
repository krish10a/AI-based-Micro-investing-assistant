"""Financial diagnosis layer - computes derived metrics and insights."""

from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from enum import Enum


class FinancialState(Enum):
    """User financial state classification."""
    FINANCIALLY_STRESSED = "Financially Stressed"
    CASH_FLOW_TIGHT = "Cash-Flow Tight"
    STABLE_BUILDER = "Stable Builder"
    HIGH_SURPLUS_BUILDER = "High-Surplus Builder"
    WEALTH_ACCELERATOR = "Wealth Accelerator"


@dataclass
class FinancialMetrics:
    """Computed financial metrics."""
    # Basic metrics
    monthly_income: float
    total_expenses: float
    net_surplus: float
    savings_rate: float
    expense_ratio: float

    # Derived ratios
    essential_expense_ratio: float
    discretionary_expense_ratio: float
    fixed_obligation_ratio: float
    dependency_burden: float

    # Category totals
    essentials_total: float
    obligations_total: float
    lifestyle_total: float
    future_capacity_total: float

    # Financial state
    financial_state: FinancialState
    financial_health_score: float

    # Alerts
    alerts: List[Dict[str, Any]]


def compute_financial_metrics(user_input: Dict[str, Any]) -> FinancialMetrics:
    """
    Compute comprehensive financial metrics from user input.

    Returns FinancialMetrics with all derived insights.
    """
    income = user_input.get("income", 0.0)

    # Expense categories
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
    emergency_fund_corpus = user_input.get("emergency_fund_corpus", 0)

    # Group expenses
    essentials = rent + groceries + transport + utilities + healthcare
    obligations = loan_repayment + insurance
    lifestyle = eating_out + entertainment + miscellaneous
    future_capacity = education

    total_expenses = essentials + obligations + lifestyle + future_capacity
    net_surplus = income - total_expenses

    # Compute ratios (with safety for division by zero)
    income_safe = income if income > 0 else 1.0

    savings_rate = net_surplus / income_safe
    expense_ratio = total_expenses / income_safe
    essential_expense_ratio = essentials / income_safe
    discretionary_expense_ratio = (eating_out + entertainment + miscellaneous) / income_safe
    fixed_obligation_ratio = (rent + loan_repayment) / income_safe
    dependency_burden = dependents * 0.05  # 5% burden per dependent

    # Compute financial health score (0-100)
    health_score = compute_health_score(
        savings_rate=savings_rate,
        debt_burden=fixed_obligation_ratio,
        dependency_burden=dependency_burden,
        expense_control=1 - discretionary_expense_ratio,
        surplus_size=net_surplus,
        income=income
    )

    # Classify financial state
    financial_state = classify_financial_state(
        savings_rate=savings_rate,
        income=income,
        expense_ratio=expense_ratio,
        net_surplus=net_surplus
    )

    # Generate alerts
    alerts = generate_alerts(
        savings_rate=savings_rate,
        net_surplus=net_surplus,
        fixed_obligation_ratio=fixed_obligation_ratio,
        discretionary_expense_ratio=discretionary_expense_ratio,
        insurance=insurance,
        dependents=dependents,
        income=income,
        financial_state=financial_state,
        health_score=health_score,
        emergency_fund_corpus=emergency_fund_corpus
    )

    return FinancialMetrics(
        monthly_income=income,
        total_expenses=total_expenses,
        net_surplus=net_surplus,
        savings_rate=savings_rate,
        expense_ratio=expense_ratio,
        essential_expense_ratio=essential_expense_ratio,
        discretionary_expense_ratio=discretionary_expense_ratio,
        fixed_obligation_ratio=fixed_obligation_ratio,
        dependency_burden=dependency_burden,
        essentials_total=essentials,
        obligations_total=obligations,
        lifestyle_total=lifestyle,
        future_capacity_total=future_capacity,
        financial_state=financial_state,
        financial_health_score=health_score,
        alerts=alerts
    )


def compute_health_score(
    savings_rate: float,
    debt_burden: float,
    dependency_burden: float,
    expense_control: float,
    surplus_size: float,
    income: float
) -> float:
    """
    Compute financial health score (0-100).

    Components:
    - Savings rate (30%): Higher is better
    - Debt burden (20%): Lower is better
    - Dependency burden (10%): Lower is better
    - Expense control (15%): Lower discretionary = better
    - Surplus size (15%): Absolute surplus relative to income
    - Emergency buffer (10%): Based on surplus sustainability
    """
    # Savings rate score (0-30)
    savings_score = min(30, savings_rate * 60)  # 50% savings = 30 points

    # Debt burden score (0-20) - lower debt = higher score
    debt_score = max(0, 20 - debt_burden * 40)  # 50% debt = 0 points

    # Dependency burden score (0-10)
    dependency_score = max(0, 10 - dependency_burden * 50)

    # Expense control score (0-15)
    expense_score = expense_control * 15

    # Surplus size score (0-15)
    surplus_ratio = surplus_size / (income + 1e-9)
    surplus_score = min(15, surplus_ratio * 30)

    # Emergency buffer score (0-10)
    # Assume 3+ months surplus = full points
    emergency_score = min(10, surplus_ratio * 30)

    total = savings_score + debt_score + dependency_score + expense_score + surplus_score + emergency_score
    return round(min(100, max(0, total)), 1)


def classify_financial_state(
    savings_rate: float,
    income: float,
    expense_ratio: float,
    net_surplus: float
) -> FinancialState:
    """
    Classify user into meaningful financial state.

    States:
    - Financially Stressed: Negative or <10% savings
    - Cash-Flow Tight: 10-25% savings
    - Stable Builder: 25-40% savings
    - High-Surplus Builder: 40-50% savings
    - Wealth Accelerator: 50%+ savings
    """
    if net_surplus <= 0 or savings_rate < 0.10:
        return FinancialState.FINANCIALLY_STRESSED
    elif savings_rate < 0.25:
        return FinancialState.CASH_FLOW_TIGHT
    elif savings_rate < 0.40:
        return FinancialState.STABLE_BUILDER
    elif savings_rate < 0.50:
        return FinancialState.HIGH_SURPLUS_BUILDER
    else:
        return FinancialState.WEALTH_ACCELERATOR


def generate_alerts(
    savings_rate: float,
    net_surplus: float,
    fixed_obligation_ratio: float,
    discretionary_expense_ratio: float,
    insurance: float,
    dependents: int,
    income: float,
    financial_state: FinancialState,
    health_score: float,
    emergency_fund_corpus: float = 0
) -> List[Dict[str, Any]]:
    """
    Generate financial alerts based on analysis.

    Returns list of alert dicts with type, severity, and message.
    """
    alerts = []

    # Idle Cash Alert
    if savings_rate > 0.40 and net_surplus > income * 0.25:
        alerts.append({
            "type": "idle_cash",
            "severity": "warning",
            "message": f"You have ₹{net_surplus:,.0f}/month surplus ({savings_rate*100:.1f}% of income). Consider deploying idle cash into goal-based investments."
        })

    # Overconfidence Alert
    if health_score < 50:
        alerts.append({
            "type": "overconfidence",
            "severity": "caution",
            "message": f"Your financial health score is {health_score}/100. Focus on building stability before aggressive investing."
        })

    # Debt Stress Alert
    if fixed_obligation_ratio > 0.40:
        alerts.append({
            "type": "debt_stress",
            "severity": "critical",
            "message": f"Fixed obligations (rent + loans) consume {fixed_obligation_ratio*100:.1f}% of income. Prioritize debt reduction."
        })

    # Lifestyle Inflation Alert
    if discretionary_expense_ratio > 0.20:
        alerts.append({
            "type": "lifestyle_inflation",
            "severity": "warning",
            "message": f"Discretionary spending (eating out, entertainment) is {discretionary_expense_ratio*100:.1f}% of income. Consider reducing to increase investment capacity."
        })

    # Missing Protection Alert
    if dependents > 0 and insurance < income * 0.10:
        alerts.append({
            "type": "missing_protection",
            "severity": "critical",
            "message": f"With {dependents} dependent(s) and only ₹{insurance:,.0f} insurance, you lack adequate protection. Aim for 10x income coverage."
        })

    # Underinvestment Alert
    if savings_rate > 0.30 and financial_state not in [FinancialState.WEALTH_ACCELERATOR, FinancialState.HIGH_SURPLUS_BUILDER]:
        alerts.append({
            "type": "underinvestment",
            "severity": "warning",
            "message": "You're saving well but may not be investing enough. Compounding is being wasted on idle cash."
        })

    # Emergency Fund Alert
    if net_surplus < income * 0.10:
        alerts.append({
            "type": "emergency_fund",
            "severity": "critical",
            "message": "Low surplus detected. Priority should be building a 3-6 month emergency fund before investing."
        })

        # High Income Disclaimer (edge case guard)
    HIGH_INCOME_THRESHOLD = 500000  # 5L/month
    if income > HIGH_INCOME_THRESHOLD:
        alerts.append({
            'type': 'high_income_disclaimer',
            'severity': 'info',
            'message': f'DEMO MODE: Income exceeds typical training range. Output based on heuristic rules from behavioral clustering, NOT personalized financial planning. Consult a SEBI-registered advisor for high-net-worth strategies.'
        })

    # Emergency Fund Readiness Check
    monthly_expenses = income - net_surplus
    if monthly_expenses > 0:
        emergency_target = monthly_expenses * 3  # Minimum 3 months
        emergency_target_full = monthly_expenses * 6  # Full 6 months

        if emergency_fund_corpus < emergency_target:
            if emergency_fund_corpus == 0:
                alerts.append({
                    "type": "emergency_fund_missing",
                    "severity": "critical",
                    "message": f"CRITICAL: You have NO emergency fund. Build ₹{emergency_target:,.0f} (3 months expenses) BEFORE any investing. Start with ₹{min(net_surplus * 0.5, 10000):,.0f}/month until target is reached."
                })
            else:
                months_covered = emergency_fund_corpus / monthly_expenses
                # Only suggest saving if net_surplus is positive
                if net_surplus > 0:
                    savings_suggestion = f"Continue with ₹{min(net_surplus * 0.5, 10000):,.0f}/month until target is reached."
                else:
                    savings_suggestion = "Focus on reducing expenses or increasing income to build positive savings first."
                alerts.append({
                    "type": "emergency_fund_partial",
                    "severity": "critical",
                    "message": f"Your emergency fund (₹{emergency_fund_corpus:,.0f}) covers only {months_covered:.1f} months. Build ₹{emergency_target:,.0f} (3 months expenses) BEFORE any investing. {savings_suggestion}"
                })
        elif emergency_fund_corpus < emergency_target_full:
            months_covered = emergency_fund_corpus / monthly_expenses
            alerts.append({
                "type": "emergency_fund_incomplete",
                "severity": "warning",
                "message": f"Your emergency fund (₹{emergency_fund_corpus:,.0f}) covers only {months_covered:.1f} months. Target: ₹{emergency_target_full:,.0f} (6 months). Continue building before aggressive investing."
            })
        elif emergency_fund_corpus >= emergency_target_full:
            months_covered = emergency_fund_corpus / monthly_expenses
            alerts.append({
                "type": "emergency_fund_adequate",
                "severity": "info",
                "message": f"✅ Emergency fund (₹{emergency_fund_corpus:,.0f}) covers {months_covered:.1f} months. You're ready for investment planning."
            })

    return alerts
