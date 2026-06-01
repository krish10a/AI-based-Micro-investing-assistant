"""Pydantic schemas for API request/response validation."""

import enum
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Dict, Any, Union


# =============================================================================
# Request Schemas
# =============================================================================

class UserFinancialInput(BaseModel):
    """User financial information for analysis."""

    income: float = Field(..., description="Monthly income (zero or positive)", ge=0)
    rent: float = Field(default=0, ge=0)
    loan_repayment: float = Field(default=0, ge=0)
    insurance: float = Field(default=0, ge=0)
    groceries: float = Field(default=0, ge=0)
    transport: float = Field(default=0, ge=0)
    eating_out: float = Field(default=0, ge=0)
    entertainment: float = Field(default=0, ge=0)
    utilities: float = Field(default=0, ge=0)
    healthcare: float = Field(default=0, ge=0)
    education: float = Field(default=0, ge=0)
    miscellaneous: float = Field(default=0, ge=0)
    dependents: int = Field(default=1, ge=0)
    emergency_fund_corpus: float = Field(default=0, ge=0, description="Current emergency fund savings in rupees")
    goals: List[str] = Field(default=[], description="Financial goals: Retirement, Child Education, Home Purchase, Wealth Building, Travel, Education Upskilling")

    @field_validator('income')
    @classmethod
    def validate_income(cls, v):
        """Validate income is within reasonable bounds."""
        if v < 0:
            raise ValueError('Income cannot be negative. Please enter a valid monthly income.')
        if v > 10000000:  # 1 Crore per month
            raise ValueError('Income exceeds reasonable range (₹1 crore/month). Please verify your input.')
        return v

    @field_validator('rent', 'loan_repayment', 'insurance', 'groceries',
                      'transport', 'eating_out', 'entertainment', 'utilities',
                      'healthcare', 'education', 'miscellaneous')
    @classmethod
    def validate_non_negative(cls, v, info):
        """Validate expense fields are non-negative."""
        if v < 0:
            field_name = info.field_name if hasattr(info, 'field_name') else 'This field'
            raise ValueError(f'{field_name.capitalize()} cannot be negative. Please enter a value of 0 or greater.')
        return v

    @field_validator('dependents')
    @classmethod
    def validate_dependents(cls, v):
        """Validate dependents count is reasonable."""
        if v < 0:
            raise ValueError('Number of dependents cannot be negative.')
        if v > 50:
            raise ValueError('Number of dependents exceeds reasonable range. Please verify your input.')
        return v

    @field_validator('emergency_fund_corpus')
    @classmethod
    def validate_emergency_fund(cls, v):
        """Validate emergency fund corpus is non-negative."""
        if v < 0:
            raise ValueError('Emergency fund corpus cannot be negative.')
        return v

    @field_validator('goals')
    @classmethod
    def validate_goals(cls, v):
        """Validate goals are from allowed list."""
        valid_goals = [
            "Retirement", "Child Education", "Home Purchase",
            "Wealth Building", "Travel", "Education Upskilling"
        ]
        for goal in v:
            if goal not in valid_goals:
                raise ValueError(f'Invalid goal: {goal}. Valid options: {", ".join(valid_goals)}')
        return v

    @model_validator(mode='after')
    def validate_income_expense_consistency(self) -> 'UserFinancialInput':
        """Cross-field validation for income vs expense consistency."""
        total_expenses = (
            self.rent + self.loan_repayment + self.insurance + self.groceries +
            self.transport + self.eating_out + self.entertainment + self.utilities +
            self.healthcare + self.education + self.miscellaneous
        )

        # Expenses can't exceed 120% of income
        if total_expenses > self.income * 1.2:
            raise ValueError(
                f'Total expenses (₹{total_expenses:,.0f}) exceed 120% of income (₹{self.income:,.0f}). '
                'Please verify your expense entries.'
            )

        # Check for suspicious zero expenses with reasonable income
        if total_expenses == 0 and self.income > 10000:
            raise ValueError(
                'Total expenses are zero. This is unusual. Please verify your expense entries.'
            )

        return self

    class Config:
        json_schema_extra = {
            "example": {
                "income": 45000,
                "rent": 10000,
                "loan_repayment": 3000,
                "insurance": 1000,
                "groceries": 4000,
                "transport": 2000,
                "eating_out": 2000,
                "entertainment": 1000,
                "utilities": 1500,
                "healthcare": 500,
                "education": 1000,
                "miscellaneous": 500,
                "dependents": 1
            }
        }


class ChatRequest(BaseModel):
    """Conversational follow-up request."""

    message: str = Field(..., description="User's follow-up question")
    user_profile: Optional[Dict[str, Any]] = Field(default=None, description="Previously computed user profile")


# =============================================================================
# Response Schemas
# =============================================================================

class FinancialHealthScore(BaseModel):
    """Financial health score breakdown."""

    total_score: float = Field(..., description="Overall health score (0-100)")
    savings_score: float = Field(..., description="Savings rate component (0-30)")
    debt_score: float = Field(..., description="Debt burden component (0-20)")
    dependency_score: float = Field(..., description="Dependency burden component (0-10)")
    expense_control_score: float = Field(..., description="Expense control component (0-15)")
    surplus_score: float = Field(..., description="Surplus size component (0-15)")
    emergency_score: float = Field(..., description="Emergency buffer component (0-10)")


class ExpenseCategoryBreakdown(BaseModel):
    """Expense breakdown by category."""

    essentials: Dict[str, float] = Field(..., description="Essential expenses breakdown")
    obligations: Dict[str, float] = Field(..., description="Obligations breakdown")
    lifestyle: Dict[str, float] = Field(..., description="Lifestyle expenses breakdown")
    future_capacity: Dict[str, float] = Field(..., description="Future capacity expenses")


class RiskLevel(BaseModel):
    """Structured risk level with label and color for UI rendering."""

    label: str = Field(..., description="Risk level label (e.g., LOW, MEDIUM, HIGH)")
    color: str = Field(..., description="UI color theme (success, info, warning, error)")
    description: Optional[str] = Field(None, description="Detailed risk description")


class Alert(BaseModel):
    """Financial alert."""

    type: str = Field(..., description="Alert type")
    severity: str = Field(..., description="Alert severity: critical, warning, caution, info")
    message: str = Field(..., description="Alert message")


class ExpenseInsight(BaseModel):
    """Expense insight."""

    category: str = Field(..., description="Expense category")
    severity: str = Field(..., description="Insight severity")
    message: str = Field(..., description="Insight message")
    recommendation: str = Field(..., description="Actionable recommendation")


class GoalAllocation(BaseModel):
    """Goal-based allocation."""

    goal_name: str = Field(..., description="Goal name")
    amount: float = Field(..., description="Monthly amount in rupees")
    percentage: float = Field(..., description="Percentage of surplus")
    description: str = Field(..., description="Goal description")
    priority: str = Field(..., description="Priority: high, medium, low")


class UserFacingProfile(BaseModel):
    """Clean user-facing profile for the dashboard."""

    user_segment: str = Field(..., description="Financial state classification")
    risk_level: RiskLevel = Field(..., description="Structured risk level with label and color")
    suggested_monthly_investment: float = Field(..., description="Suggested monthly investment")
    investment_appetite: str = Field(..., description="Investment appetite")
    confidence: float = Field(..., description="Model confidence (0-1)")
    recommended_plan: str = Field(..., description="Recommended investment plan")
    segment_explanation: Optional[str] = Field(default=None, description="Detailed explanation of the segment")


class FinancialSnapshot(BaseModel):
    """Financial numbers for the snapshot card."""

    monthly_income: float = Field(..., description="Monthly income")
    monthly_expenses: float = Field(..., description="Total monthly expenses")
    monthly_savings: float = Field(..., description="Monthly savings/surplus")
    savings_rate: float = Field(..., description="Savings rate (0-1)")
    expense_ratio: float = Field(..., description="Expense ratio (0-1)")
    essential_ratio: float = Field(..., description="Essential expenses ratio")
    obligations_ratio: float = Field(..., description="Fixed obligations ratio")
    lifestyle_ratio: float = Field(..., description="Lifestyle expenses ratio")


class PortfolioAllocation(BaseModel):
    """Recommended portfolio split."""

    primary_action: str = Field(..., description="Primary action recommendation")
    allocation_breakdown: Dict[str, str] = Field(..., description="Allocation by goal")
    total_monthly_investment: float = Field(..., description="Total monthly investment")
    allocations: List[GoalAllocation] = Field(..., description="Detailed allocations")


class UserReasoning(BaseModel):
    """User-friendly reasoning section."""

    why_this_fits: List[str] = Field(..., description="Why this plan fits the user")
    watch_out: List[str] = Field(..., description="Warnings and cautions")
    next_step: str = Field(..., description="Next actionable step")


class AnalyzeUserResponse(BaseModel):
    """Complete analysis response with structured dashboard data."""

    # Structured dashboard components
    profile: UserFacingProfile = Field(..., description="User-facing profile")
    financial_snapshot: FinancialSnapshot = Field(..., description="Financial snapshot")
    portfolio: PortfolioAllocation = Field(..., description="Portfolio allocation")
    reasoning: UserReasoning = Field(..., description="Reasoning and warnings")

    # Financial health
    financial_health_score: float = Field(..., description="Overall financial health score (0-100)")

    # Expense analysis
    expense_insights: List[ExpenseInsight] = Field(..., description="Expense insights")
    expense_summary: Dict[str, Any] = Field(..., description="Expense category summary")

    # Legacy fields for compatibility
    segment: str
    risk_level: RiskLevel
    suggested_monthly_investment: float
    investment_appetite: str
    reason_codes: List[str]
    confidence: float
    financial_summary: str
    financial_summary_dict: Optional[Dict[str, Any]] = None
    safe_action: str
    nim_explanation: Optional[str] = None
    warnings: List[str] = []
    income_level: Optional[str] = None
    recommended_plan: Optional[str] = None
    allocation_details: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str = "2.0.0"


class SIPRequest(BaseModel):
    """SIP calculation request."""

    monthly_investment: float = Field(..., gt=0, description="Monthly SIP amount in rupees")
    years: int = Field(..., gt=0, le=50, description="Investment tenure in years (1-50)")
    expected_return: float = Field(default=12, gt=0, le=30, description="Expected annual return rate in percentage (1-30%)")

    class Config:
        json_schema_extra = {
            "example": {
                "monthly_investment": 5000,
                "years": 10,
                "expected_return": 12
            }
        }


class SIPCalculationResponse(BaseModel):
    """SIP calculation response."""

    monthly_investment: float
    years: int
    expected_return: float
    future_value: float
    total_invested: float
    total_growth: float
    growth_percentage: float
    formatted_future_value: str
    formatted_total_invested: str


class ExpenseBreakdownItem(BaseModel):
    """Single expense category breakdown."""

    total: float
    ratio: float
    breakdown: Dict[str, float]


class ExpenseBreakdownResponse(BaseModel):
    """Complete expense breakdown for pie chart visualization."""

    essentials: ExpenseBreakdownItem
    obligations: ExpenseBreakdownItem
    lifestyle: ExpenseBreakdownItem
    future_capacity: ExpenseBreakdownItem
    total_expenses: float
    pie_chart_data: List[Dict[str, Any]]


class ModelInfoResponse(BaseModel):
    """Model metadata response."""

    model_name: str
    version: str
    segment_labels: List[str]
    features: List[str]
    training_date: Optional[str] = None
    silhouette_score: Optional[float] = None
    limitations: List[str]
    explanation_model: Optional[str] = None


# =============================================================================
# Internal Schemas
# =============================================================================

class AuditLogResponse(BaseModel):
    """Audit logs response."""

    logs: List[Dict[str, Any]]
    total_count: int
    timestamp: str


class FinancialMetrics(BaseModel):
    """Computed financial metrics."""

    monthly_income: float
    total_expenses: float
    net_surplus: float
    savings_rate: float
    expense_ratio: float
    essential_expense_ratio: float
    discretionary_expense_ratio: float
    fixed_obligation_ratio: float
    dependency_burden: float
    essentials_total: float
    obligations_total: float
    lifestyle_total: float
    future_capacity_total: float
    financial_state: str
    financial_health_score: float
    alerts: List[Alert]


# =============================================================================
# User Profile Schemas
# =============================================================================


class UserProfileUpdate(BaseModel):
    """User profile update request."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    phone: Optional[str] = Field(None, min_length=10, max_length=15)
    date_of_birth: Optional[str] = Field(None, description="Date of birth YYYY-MM-DD")
    address: Optional[str] = Field(None, max_length=200)
    risk_tolerance: Optional[str] = Field(None, description="low, moderate, high")

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        """Validate phone format."""
        if v is not None:
            import re
            if not re.match(r'^\+?[0-9\-\s]{10,15}$', v):
                raise ValueError('Invalid phone number format')
        return v

    @field_validator('date_of_birth')
    @classmethod
    def validate_dob(cls, v):
        """Validate date format."""
        if v is not None:
            import re
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
                raise ValueError('Invalid date format. Expected YYYY-MM-DD')
        return v

class UserProfileResponse(BaseModel):
    """User profile response."""

    user_id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None
    address: Optional[str] = None
    kyc_verified: bool = False
    segment: Optional[str] = None
    risk_tolerance: Optional[str] = None
    created_at: str


# =============================================================================
# Transaction Schemas
# =============================================================================


class TransactionType(str, enum.Enum):
    """Transaction types."""

    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    INVESTMENT = "investment"
    GOAL_ALLOCATION = "goal_allocation"


class TransactionStatus(str, enum.Enum):
    """Transaction statuses."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TransactionCreate(BaseModel):
    """Transaction creation request."""

    user_id: str = Field(..., description="User ID")
    type: TransactionType = Field(..., description="Transaction type")
    amount: float = Field(..., gt=0, description="Transaction amount")
    category: str = Field(..., max_length=100, description="Transaction category")
    goal_id: Optional[str] = Field(None, description="Associated goal ID")
    description: Optional[str] = Field(None, max_length=500)
    metadata: Optional[Dict[str, Any]] = Field(default=None)


class TransactionResponse(BaseModel):
    """Transaction response."""

    id: str
    user_id: str
    type: str
    amount: float
    category: str
    goal_id: Optional[str] = None
    description: Optional[str] = None
    status: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: str


class TransactionListResponse(BaseModel):
    """Transaction list response."""

    transactions: List[Dict[str, Any]]
    total_count: int
    page: int = 1
    page_size: int = 20


# =============================================================================
# SIP (Systematic Investment Plan) Schemas
# =============================================================================


class SIPStatus(str, enum.Enum):
    """SIP statuses."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SIPCreate(BaseModel):
    """SIP creation request."""

    user_id: str = Field(..., description="User ID")
    goal_id: str = Field(..., description="Associated goal ID")
    monthly_amount: float = Field(..., gt=0, description="Monthly investment amount")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    duration_months: int = Field(..., gt=0, le=600, description="Duration in months (1-600)")
    expected_return_rate: float = Field(default=12, gt=0, le=30, description="Expected annual return rate (1-30%)")
    investment_type: str = Field(default="mutual_fund", max_length=50)
    metadata: Optional[Dict[str, Any]] = Field(default=None)


class SIPUpdate(BaseModel):
    """SIP update request."""

    monthly_amount: Optional[float] = Field(None, gt=0)
    expected_return_rate: Optional[float] = Field(None, gt=0, le=30)
    status: Optional[SIPStatus] = None
    metadata: Optional[Dict[str, Any]] = None


class SIPPauseResume(BaseModel):
    """SIP pause/resume request."""

    action: str = Field(..., description="pause or resume")


class SIPResponse(BaseModel):
    """SIP response."""

    id: str
    user_id: str
    goal_id: str
    monthly_amount: float
    start_date: str
    duration_months: int
    expected_return_rate: float
    investment_type: str
    status: str
    current_value: float = 0.0
    total_invested: float = 0.0
    months_elapsed: int = 0
    projected_maturity: float = 0.0
    metadata: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: str


class SIPListResponse(BaseModel):
    """SIP list response."""

    sips: List[Dict[str, Any]]
    total_count: int
    active_count: int
    paused_count: int
    completed_count: int


# =============================================================================
# Portfolio Schemas
# =============================================================================


class Holding(BaseModel):
    """Individual holding in portfolio."""

    symbol: str
    name: str
    quantity: float
    average_cost: float
    current_price: float
    current_value: float
    gain_loss: float
    gain_loss_percentage: float
    asset_type: str = "equity"
    goal_allocation: Optional[str] = None


class PortfolioHoldingResponse(BaseModel):
    """Portfolio holdings response."""

    user_id: str
    holdings: List[Holding]
    total_value: float
    total_invested: float
    total_gain_loss: float
    total_gain_loss_percentage: float
    asset_allocation: Dict[str, float]
    last_updated: str


class PerformanceMetrics(BaseModel):
    """Performance metrics."""

    period: str
    return_percentage: float
    absolute_return: float
    benchmark_comparison: Optional[float] = None


class PortfolioPerformanceResponse(BaseModel):
    """Portfolio performance response."""

    user_id: str
    current_value: float
    total_invested: float
    total_gain_loss: float
    total_return_percentage: float
    current_date: str
    holdings_count: int
    performance_history: List[PerformanceMetrics]
    best_performer: Optional[Dict[str, Any]] = None
    worst_performer: Optional[Dict[str, Any]] = None


# =============================================================================
# Reports Schemas
# =============================================================================


class ReportSummary(BaseModel):
    """Report summary data."""

    user_id: str
    report_date: str
    total_invested: float
    current_value: float
    total_gain_loss: float
    return_percentage: float
    active_sips: int
    total_goals: int
    completed_goals: int
    top_holding: Optional[str] = None
    asset_allocation_summary: Dict[str, float]
    risk_profile: str
    financial_health_score: Optional[float] = None


class ReportSummaryResponse(BaseModel):
    """Report summary response."""

    summary: ReportSummary
    generated_at: str


class ReportExportRequest(BaseModel):
    """Report export request."""

    report_type: str = Field(..., description="summary, transactions, portfolio, tax")
    format: str = Field(default="json", description="json, csv, pdf")
    start_date: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    include_charts: bool = Field(default=False)


class ReportExportResponse(BaseModel):
    """Report export response."""

    success: bool
    file_url: Optional[str] = None
    file_size: Optional[int] = None
    format: str
    message: str


class FinancialOnlyOnboardRequest(BaseModel):
    """Financial-only onboarding request without personal information requirements."""

    # Financial profile only
    income: float = Field(..., ge=0)
    rent: float = Field(default=0, ge=0)
    loan_repayment: float = Field(default=0, ge=0)
    insurance: float = Field(default=0, ge=0)
    groceries: float = Field(default=0, ge=0)
    transport: float = Field(default=0, ge=0)
    eating_out: float = Field(default=0, ge=0)
    entertainment: float = Field(default=0, ge=0)
    utilities: float = Field(default=0, ge=0)
    healthcare: float = Field(default=0, ge=0)
    education: float = Field(default=0, ge=0)
    miscellaneous: float = Field(default=0, ge=0)
    dependents: int = Field(default=1, ge=0)
    emergency_fund_corpus: float = Field(default=0, ge=0)
    goals: list = Field(default=[])
