"""Expense intelligence - analyzes spending patterns and generates insights."""

from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class ExpenseInsight:
    """Single expense insight."""
    category: str
    severity: str  # "info", "warning", "critical"
    message: str
    recommendation: str


def analyze_expenses(user_input: Dict[str, Any]) -> List[ExpenseInsight]:
    """
    Analyze expense categories and generate insights.

    Returns list of actionable insights.
    """
    income = user_input.get("income", 0.0)
    income_safe = income if income > 0 else 1.0

    # Expense values
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

    insights = []

    # Essential expense analysis
    essentials_total = rent + groceries + transport + utilities + healthcare
    essentials_ratio = essentials_total / income_safe

    if essentials_ratio < 0.30:
        insights.append(ExpenseInsight(
            category="essentials",
            severity="info",
            message=f"Essential expenses are only {essentials_ratio*100:.1f}% of income (unusually low)",
            recommendation="This is excellent for wealth building. Ensure you're not under-maintaining essential needs."
        ))
    elif essentials_ratio > 0.60:
        insights.append(ExpenseInsight(
            category="essentials",
            severity="warning",
            message=f"Essential expenses consume {essentials_ratio*100:.1f}% of income",
            recommendation="Consider ways to reduce fixed costs (negotiate rent, optimize utilities) to free up investment capacity."
        ))

    # Rent analysis
    rent_ratio = rent / income_safe
    if rent_ratio > 0.40:
        insights.append(ExpenseInsight(
            category="rent",
            severity="warning",
            message=f"Rent is {rent_ratio*100:.1f}% of income (recommended: <30%)",
            recommendation="Consider roommates, relocating, or negotiating rent to reduce housing burden."
        ))
    elif rent_ratio < 0.20:
        insights.append(ExpenseInsight(
            category="rent",
            severity="info",
            message=f"Rent is only {rent_ratio*100:.1f}% of income",
            recommendation="Excellent housing cost management. This significantly boosts investment capacity."
        ))

    # Loan analysis
    loan_ratio = loan_repayment / income_safe
    if loan_ratio > 0.30:
        insights.append(ExpenseInsight(
            category="loans",
            severity="critical",
            message=f"Loan repayments consume {loan_ratio*100:.1f}% of income",
            recommendation="Prioritize debt repayment. Consider debt consolidation or refinancing to reduce interest burden."
        ))
    elif loan_ratio > 0.15:
        insights.append(ExpenseInsight(
            category="loans",
            severity="warning",
            message=f"Loan repayments are {loan_ratio*100:.1f}% of income",
            recommendation="Monitor debt levels. Aim to reduce loan burden before aggressive investing."
        ))
    elif loan_repayment == 0:
        insights.append(ExpenseInsight(
            category="loans",
            severity="info",
            message="No loan repayments",
            recommendation="Debt-free status is excellent. Direct the would-be debt payment toward investments."
        ))

    # Insurance analysis
    insurance_ratio = insurance / income_safe
    if dependents > 0 and insurance_ratio < 0.05:
        insights.append(ExpenseInsight(
            category="insurance",
            severity="critical",
            message=f"With {dependents} dependent(s), insurance is only {insurance_ratio*100:.1f}% of income",
            recommendation="Increase life and health insurance coverage immediately. Aim for 10-15x annual income."
        ))
    elif insurance_ratio < 0.02:
        insights.append(ExpenseInsight(
            category="insurance",
            severity="warning",
            message=f"Insurance is only {insurance_ratio*100:.1f}% of income",
            recommendation="Consider adequate health and term insurance, especially with dependents."
        ))

    # Discretionary spending analysis
    discretionary_total = eating_out + entertainment + miscellaneous
    discretionary_ratio = discretionary_total / income_safe

    if discretionary_ratio > 0.25:
        insights.append(ExpenseInsight(
            category="discretionary",
            severity="warning",
            message=f"Discretionary spending is {discretionary_ratio*100:.1f}% of income",
            recommendation="Reduce eating out/entertainment by 20-30% to free up ₹{:.0f}/month for investing.".format(income * 0.10)
        ))
    elif discretionary_ratio > 0.15:
        insights.append(ExpenseInsight(
            category="discretionary",
            severity="info",
            message=f"Discretionary spending is {discretionary_ratio*100:.1f}% of income",
            recommendation="Consider setting a monthly limit for non-essential spending."
        ))

    # Eating out specific
    eating_out_ratio = eating_out / income_safe
    if eating_out_ratio > 0.10:
        insights.append(ExpenseInsight(
            category="eating_out",
            severity="warning",
            message=f"Eating out is {eating_out_ratio*100:.1f}% of income (₹{eating_out:,.0f}/month)",
            recommendation="Cook at home more often. This could save ₹{:.0f}/month for investing.".format(eating_out * 0.3)
        ))

    # Education analysis
    education_ratio = education / income_safe
    if education_ratio < 0.02 and income_safe > 30000:
        insights.append(ExpenseInsight(
            category="education",
            severity="info",
            message="Low investment in education/skills",
            recommendation="Allocate 2-5% of income to skills/certifications. This has the highest ROI for income growth."
        ))
    elif education_ratio > 0.05:
        insights.append(ExpenseInsight(
            category="education",
            severity="info",
            message="Good investment in education/skills",
            recommendation="Continue upskilling. Higher income amplifies all investment returns."
        ))

    # Healthcare analysis
    healthcare_ratio = healthcare / income_safe
    if healthcare_ratio < 0.01:
        insights.append(ExpenseInsight(
            category="healthcare",
            severity="warning",
            message="Very low healthcare spending",
            recommendation="Ensure you have adequate health insurance. Preventive care saves money long-term."
        ))

    # Miscellaneous analysis
    misc_ratio = miscellaneous / income_safe
    if misc_ratio > 0.10:
        insights.append(ExpenseInsight(
            category="miscellaneous",
            severity="warning",
            message=f"Miscellaneous expenses are {misc_ratio*100:.1f}% of income",
            recommendation="Track miscellaneous spending. Often contains hidden leaks that can be plugged."
        ))

    # Transport analysis
    transport_ratio = transport / income_safe
    if transport_ratio > 0.15:
        insights.append(ExpenseInsight(
            category="transport",
            severity="warning",
            message=f"Transport is {transport_ratio*100:.1f}% of income",
            recommendation="Consider public transport, carpooling, or bike to reduce transport costs."
        ))

    return insights


def get_expense_summary(user_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get a summary of expense breakdown.

    Returns structured summary for UI display.
    """
    income = user_input.get("income", 0.0)
    income_safe = income if income > 0 else 1.0

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

    essentials = rent + groceries + transport + utilities + healthcare
    obligations = loan_repayment + insurance
    lifestyle = eating_out + entertainment + miscellaneous
    future = education

    return {
        "essentials": {
            "total": essentials,
            "ratio": essentials / income_safe,
            "breakdown": {
                "rent": rent,
                "groceries": groceries,
                "transport": transport,
                "utilities": utilities,
                "healthcare": healthcare
            }
        },
        "obligations": {
            "total": obligations,
            "ratio": obligations / income_safe,
            "breakdown": {
                "loan_repayment": loan_repayment,
                "insurance": insurance
            }
        },
        "lifestyle": {
            "total": lifestyle,
            "ratio": lifestyle / income_safe,
            "breakdown": {
                "eating_out": eating_out,
                "entertainment": entertainment,
                "miscellaneous": miscellaneous
            }
        },
        "future_capacity": {
            "total": education,
            "ratio": education / income_safe
        }
    }
