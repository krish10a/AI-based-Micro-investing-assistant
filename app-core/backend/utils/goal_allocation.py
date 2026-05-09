"""Goal-based allocation engine - generates specific allocation recommendations."""

from typing import Dict, List, Any
from dataclasses import dataclass, asdict


@dataclass
class GoalAllocation:
    """Single goal allocation bucket."""
    goal_name: str
    amount: float
    percentage: float
    description: str
    priority: str  # "high", "medium", "low"


def compute_goal_based_allocation(
    savings: float,
    income: float,
    financial_state: str,
    health_score: float,
    alerts: List[Dict[str, Any]],
    dependents: int = 1,
    has_emergency_fund: bool = False,
    goals: List[str] = None
) -> Dict[str, Any]:
    """
    Compute goal-based allocation for user's surplus.

    Returns structured allocation with specific amounts and goals.
    """
    goals = goals or []
    allocations = []
    total_allocated = 0.0

    # Goal descriptions for selected goals
    goal_descriptions = {
        "Retirement": "Long-term wealth building for retirement income",
        "Child Education": "Fund your child's higher education and career",
        "Home Purchase": "Save for down payment on a home",
        "Wealth Building": "General wealth accumulation and compounding",
        "Travel": "Fund for travel and experiences",
        "Education Upskilling": "Invest in courses and certifications for career growth"
    }

    # Handle negative savings case - no investment possible
    if savings <= 0:
        return {
            "total_monthly_investment": 0,
            "allocations": [
                {
                    "goal_name": "Emergency Fund",
                    "amount": 0,
                    "percentage": 0,
                    "description": "Focus on reducing expenses to build positive surplus first",
                    "priority": "high"
                }
            ],
            "summary": {
                "emergency_fund_target": 0,
                "emergency_fund_monthly": 0,
                "equity_allocation": 0,
                "debt_allocation": 0,
                "alternative_allocation": 0,
                "skill_allocation": 0,
                "tax_allocation": 0,
                "insurance_allocation": 0
            }
        }

    # Check for critical alerts that need priority handling
    has_debt_stress = any(a["type"] == "debt_stress" for a in alerts)
    has_missing_protection = any(a["type"] == "missing_protection" for a in alerts)
    has_emergency_alert = any(a["type"] == "emergency_fund" for a in alerts)
    is_high_income = income > 500000  # ₹5L/month threshold

    # ======================================================================
    # Priority 1: Emergency Fund (as TARGET with monthly contribution)
    # ======================================================================
    # Emergency fund is a corpus target, not a forever monthly allocation
    if has_emergency_alert or not has_emergency_fund:
        # Target: 3-6 months of EXPENSES (not income)
        monthly_expenses = income - savings
        emergency_target_low = monthly_expenses * 3
        emergency_target_high = monthly_expenses * 6

        # Build emergency fund in 6 months
        emergency_monthly = emergency_target_low / 6

        # Cap at 40% of savings to leave room for investing
        emergency_monthly = min(emergency_monthly, savings * 0.40)

        allocations.append(GoalAllocation(
            goal_name="Emergency Fund (Target Corpus)",
            amount=emergency_monthly,
            percentage=emergency_monthly / (savings + 1e-9),
            description=f"Build ₹{emergency_target_low:,.0f}-₹{emergency_target_high:,.0f} corpus (3-6 months expenses). Contribute ₹{emergency_monthly:,.0f}/month for 6 months, then redirect to investments.",
            priority="high"
        ))
        total_allocated += emergency_monthly

    # ======================================================================
    # Priority 2: Debt Paydown (if high debt)
    # ======================================================================
    if has_debt_stress:
        debt_paydown = savings * 0.30
        allocations.append(GoalAllocation(
            goal_name="Debt Repayment",
            amount=debt_paydown,
            percentage=debt_paydown / (savings + 1e-9),
            description="Accelerate loan repayment to reduce interest burden",
            priority="high"
        ))
        total_allocated += debt_paydown

    # ======================================================================
    # Priority 3: Insurance (single clear item - NO DUPLICATE)
    # ======================================================================
    if has_missing_protection:
        # Calculate recommended insurance budget (term insurance premium)
        # For high income: suggest adequate coverage (10-15x annual income)
        recommended_coverage = income * 12 * 10  # 10x annual income
        estimated_monthly_premium = recommended_coverage * 0.0002  # ~0.2% of coverage per year

        # Cap at reasonable premium (actual market rates vary)
        insurance_budget = min(estimated_monthly_premium, savings * 0.05, 5000)
        insurance_budget = max(insurance_budget, 1000)  # Minimum ₹1000 for basic coverage

        allocations.append(GoalAllocation(
            goal_name="Term Insurance Premium",
            amount=insurance_budget,
            percentage=insurance_budget / (savings + 1e-9),
            description=f"Secure ₹{recommended_coverage:,.0f} term coverage. Get quote from licensed advisor. This is NOT investment.",
            priority="high"
        ))
        total_allocated += insurance_budget

    # ======================================================================
    # Priority 4: Tax Planning (for high-income users)
    # ======================================================================
    if is_high_income:
        # High-income users need tax planning - allocate for tax-saving investments
        tax_allocation = savings * 0.10  # 10% for tax planning
        allocations.append(GoalAllocation(
            goal_name="Tax-Saving Investments (80C)",
            amount=tax_allocation,
            percentage=tax_allocation / (savings + 1e-9),
            description="ELSS, PPF, or NPS for tax efficiency. Consult CA for optimal strategy.",
            priority="medium"
        ))
        total_allocated += tax_allocation

    # ======================================================================
    # Priority 5: Core Investment Allocation (based on financial state)
    # ======================================================================
    remaining = savings - total_allocated

    if financial_state in ["Financially Stressed", "Cash-Flow Tight"]:
        allocations.extend([
            GoalAllocation(
                goal_name="Index Funds (Nifty 50)",
                amount=remaining * 0.50,
                percentage=0.50,
                description="Low-cost market exposure for long-term growth",
                priority="medium"
            ),
            GoalAllocation(
                goal_name="Liquid Fund",
                amount=remaining * 0.30,
                percentage=0.30,
                description="Park surplus in liquid fund for flexibility",
                priority="medium"
            ),
            GoalAllocation(
                goal_name="Skill Development",
                amount=remaining * 0.20,
                percentage=0.20,
                description="Courses/certifications for income growth",
                priority="medium"
            )
        ])
        total_allocated += remaining

    elif financial_state == "Stable Builder":
        allocations.extend([
            GoalAllocation(
                goal_name="Index Funds (Nifty 50 + Midcap)",
                amount=remaining * 0.40,
                percentage=0.40,
                description="Core equity exposure through index funds",
                priority="medium"
            ),
            GoalAllocation(
                goal_name="Flexi-Cap Fund",
                amount=remaining * 0.25,
                percentage=0.25,
                description="Diversified equity with manager flexibility",
                priority="medium"
            ),
            GoalAllocation(
                goal_name="Debt Fund / PPF",
                amount=remaining * 0.20,
                percentage=0.20,
                description="Stable debt component for balance",
                priority="medium"
            ),
            GoalAllocation(
                goal_name="Gold / International",
                amount=remaining * 0.10,
                percentage=0.10,
                description="Sovereign Gold Bonds or US ETFs",
                priority="low"
            ),
            GoalAllocation(
                goal_name="Skill/Business",
                amount=remaining * 0.05,
                percentage=0.05,
                description="Invest in yourself for higher returns",
                priority="low"
            )
        ])
        total_allocated += remaining

    elif financial_state == "High-Surplus Builder":
        allocations.extend([
            GoalAllocation(
                goal_name="Index Funds (Nifty 50 + Midcap)",
                amount=remaining * 0.35,
                percentage=0.35,
                description="Core large and mid-cap exposure",
                priority="medium"
            ),
            GoalAllocation(
                goal_name="Flexi-Cap / Multi-Cap",
                amount=remaining * 0.20,
                percentage=0.20,
                description="Active equity management",
                priority="medium"
            ),
            GoalAllocation(
                goal_name="Direct Stocks",
                amount=remaining * 0.15,
                percentage=0.15,
                description="Quality growth stocks in your domain",
                priority="low"
            ),
            GoalAllocation(
                goal_name="Debt / Bonds",
                amount=remaining * 0.15,
                percentage=0.15,
                description="Corporate bonds for stability",
                priority="medium"
            ),
            GoalAllocation(
                goal_name="Gold / Alternatives",
                amount=remaining * 0.10,
                percentage=0.10,
                description="Gold ETF + Small crypto allocation",
                priority="low"
            ),
            GoalAllocation(
                goal_name="Skill/Business",
                amount=remaining * 0.05,
                percentage=0.05,
                description="Highest ROI investment",
                priority="low"
            )
        ])
        total_allocated += remaining

    elif financial_state == "Wealth Accelerator":
        # For high-income users: more disciplined, goal-based allocation
        if is_high_income:
            # High-income specific allocation
            allocations.extend([
                GoalAllocation(
                    goal_name="Index Funds (Nifty 50 + Midcap)",
                    amount=remaining * 0.25,
                    percentage=0.25,
                    description="Core passive equity - diversify across 10+ funds max",
                    priority="medium"
                ),
                GoalAllocation(
                    goal_name="Direct Stocks",
                    amount=remaining * 0.20,
                    percentage=0.20,
                    description="High-conviction stocks (max 15-20 positions)",
                    priority="medium"
                ),
                GoalAllocation(
                    goal_name="Debt / Corporate Bonds",
                    amount=remaining * 0.15,
                    percentage=0.15,
                    description="Stable income + rebalancing buffer",
                    priority="medium"
                ),
                GoalAllocation(
                    goal_name="Gold (SGB)",
                    amount=remaining * 0.10,
                    percentage=0.10,
                    description="Inflation hedge, 8-year tenure",
                    priority="low"
                ),
                GoalAllocation(
                    goal_name="Alternatives (Crypto/Startup)",
                    amount=remaining * 0.05,
                    percentage=0.05,
                    description="High-risk bucket - cap at 5% of net worth",
                    priority="low"
                ),
                GoalAllocation(
                    goal_name="Goal-Specific Investments",
                    amount=remaining * 0.15,
                    percentage=0.15,
                    description="Child education, property, early retirement - create separate buckets",
                    priority="medium"
                ),
                GoalAllocation(
                    goal_name="Skill/Business Scaling",
                    amount=remaining * 0.10,
                    percentage=0.10,
                    description="Highest ROI - scale your earning power or start side business",
                    priority="medium"
                )
            ])
        else:
            # Standard wealth accelerator allocation
            allocations.extend([
                GoalAllocation(
                    goal_name="Index Funds (Nifty 50 + Midcap)",
                    amount=remaining * 0.30,
                    percentage=0.30,
                    description="Core passive equity exposure",
                    priority="medium"
                ),
                GoalAllocation(
                    goal_name="Flexi-Cap / Sectoral Funds",
                    amount=remaining * 0.15,
                    percentage=0.15,
                    description="Active equity + Sector bets",
                    priority="medium"
                ),
                GoalAllocation(
                    goal_name="Direct Stocks",
                    amount=remaining * 0.20,
                    percentage=0.20,
                    description="High-conviction growth stocks",
                    priority="low"
                ),
                GoalAllocation(
                    goal_name="Debt / Corporate Bonds",
                    amount=remaining * 0.12,
                    percentage=0.12,
                    description="Stable income component",
                    priority="medium"
                ),
                GoalAllocation(
                    goal_name="Gold (SGB)",
                    amount=remaining * 0.08,
                    percentage=0.08,
                    description="Sovereign Gold Bonds for inflation hedge",
                    priority="low"
                ),
                GoalAllocation(
                    goal_name="Alternatives (Crypto/Startup)",
                    amount=remaining * 0.10,
                    percentage=0.10,
                    description="High-risk, high-reward allocation",
                    priority="low"
                ),
                GoalAllocation(
                    goal_name="Skill/Business",
                    amount=remaining * 0.05,
                    percentage=0.05,
                    description="Scale your earning power",
                    priority="low"
                )
            ])
        total_allocated += remaining

    total_investment = sum(a.amount for a in allocations)

    # Calculate summary with new fields
    emergency_target = 0
    emergency_monthly = 0
    if has_emergency_alert or not has_emergency_fund:
        monthly_expenses = income - savings
        emergency_target = monthly_expenses * 3  # Low end target
        emergency_monthly = min(emergency_target / 6, savings * 0.40)

    return {
        "total_monthly_investment": total_investment,
        "allocations": [asdict(a) for a in allocations],
        "summary": {
            "emergency_fund_target": emergency_target,
            "emergency_fund_monthly": emergency_monthly,
            "equity_allocation": sum(a.amount for a in allocations if "Index" in a.goal_name or "Stock" in a.goal_name or "Flexi" in a.goal_name),
            "debt_allocation": sum(a.amount for a in allocations if "Debt" in a.goal_name or "Bond" in a.goal_name or "Liquid" in a.goal_name or "PPF" in a.goal_name),
            "alternative_allocation": sum(a.amount for a in allocations if "Gold" in a.goal_name or "Crypto" in a.goal_name or "Alternatives" in a.goal_name),
            "skill_allocation": sum(a.amount for a in allocations if "Skill" in a.goal_name),
            "tax_allocation": sum(a.amount for a in allocations if "Tax" in a.goal_name),
            "insurance_allocation": sum(a.amount for a in allocations if "Insurance" in a.goal_name or "Term" in a.goal_name)
        }
    }
