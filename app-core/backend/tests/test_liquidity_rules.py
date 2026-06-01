"""Tests for liquidity rules."""

import pytest
from utils.liquidity_rules import LiquidityRules, LiquidityStatus


class TestLiquidityRules:
    """Tests for LiquidityRules class."""

    def test_assess_liquidity_insufficient(self):
        """Test liquidity assessment with insufficient emergency fund."""
        rules = LiquidityRules()
        user_input = {
            "income": 45000,
            "rent": 15000,
            "groceries": 8000,
            "transport": 3000,
            "utilities": 2000,
            "healthcare": 1000,
            "emergency_fund_corpus": 10000
        }

        status, months_covered, required = rules.assess_liquidity(user_input)

        assert status == LiquidityStatus.INSUFFICIENT
        assert months_covered < 3
        assert required > 0

    def test_assess_liquidity_minimal(self):
        """Test liquidity assessment with minimal emergency fund."""
        rules = LiquidityRules()
        user_input = {
            "income": 45000,
            "rent": 15000,
            "groceries": 8000,
            "transport": 3000,
            "utilities": 2000,
            "healthcare": 1000,
            "emergency_fund_corpus": 100000
        }

        status, months_covered, required = rules.assess_liquidity(user_input)

        assert status == LiquidityStatus.MINIMAL
        assert 3 <= months_covered < 6

    def test_assess_liquidity_adequate(self):
        """Test liquidity assessment with adequate emergency fund."""
        rules = LiquidityRules()
        user_input = {
            "income": 45000,
            "rent": 15000,
            "groceries": 8000,
            "transport": 3000,
            "utilities": 2000,
            "healthcare": 1000,
            "emergency_fund_corpus": 200000
        }

        status, months_covered, required = rules.assess_liquidity(user_input)

        assert status == LiquidityStatus.ADEQUATE
        assert 6 <= months_covered < 12

    def test_assess_liquidity_strong(self):
        """Test liquidity assessment with strong emergency fund."""
        rules = LiquidityRules()
        user_input = {
            "income": 45000,
            "rent": 15000,
            "groceries": 8000,
            "transport": 3000,
            "utilities": 2000,
            "healthcare": 1000,
            "emergency_fund_corpus": 500000
        }

        status, months_covered, required = rules.assess_liquidity(user_input)

        assert status == LiquidityStatus.STRONG
        assert months_covered >= 12

    def test_get_investment_cap_insufficient(self):
        """Test investment cap with insufficient liquidity."""
        rules = LiquidityRules()
        user_input = {
            "income": 45000,
            "rent": 15000,
            "groceries": 8000,
            "transport": 3000,
            "utilities": 2000,
            "healthcare": 1000,
            "emergency_fund_corpus": 10000
        }

        cap = rules.get_investment_cap(user_input)

        assert cap == 0.0

    def test_get_investment_cap_strong(self):
        """Test investment cap with strong liquidity."""
        rules = LiquidityRules()
        user_input = {
            "income": 45000,
            "rent": 15000,
            "groceries": 8000,
            "transport": 3000,
            "utilities": 2000,
            "healthcare": 1000,
            "emergency_fund_corpus": 500000
        }

        cap = rules.get_investment_cap(user_input)

        assert cap == 0.5

    def test_should_allow_investment_low_income(self):
        """Test investment allowance with low income."""
        rules = LiquidityRules()
        user_input = {
            "income": 15000,
            "rent": 5000,
            "groceries": 3000,
            "transport": 1000,
            "emergency_fund_corpus": 50000
        }

        should_invest, reason = rules.should_allow_investment(user_input)

        assert should_invest is False
        assert "below minimum threshold" in reason.lower()

    def test_should_allow_investment_insufficient_liquidity(self):
        """Test investment allowance with insufficient liquidity."""
        rules = LiquidityRules()
        user_input = {
            "income": 45000,
            "rent": 15000,
            "groceries": 8000,
            "transport": 3000,
            "utilities": 2000,
            "healthcare": 1000,
            "emergency_fund_corpus": 10000
        }

        should_invest, reason = rules.should_allow_investment(user_input)

        assert should_invest is False
        assert "emergency fund" in reason.lower()

    def test_should_allow_investment_adequate(self):
        """Test investment allowance with adequate liquidity."""
        rules = LiquidityRules()
        user_input = {
            "income": 45000,
            "rent": 15000,
            "groceries": 8000,
            "transport": 3000,
            "utilities": 2000,
            "healthcare": 1000,
            "emergency_fund_corpus": 200000
        }

        should_invest, reason = rules.should_allow_investment(user_input)

        assert should_invest is True
        assert reason == ""

    def test_apply_liquidity_guardrails_insufficient(self):
        """Test liquidity guardrails with insufficient liquidity."""
        rules = LiquidityRules()
        user_input = {
            "income": 45000,
            "rent": 15000,
            "groceries": 8000,
            "transport": 3000,
            "utilities": 2000,
            "healthcare": 1000,
            "emergency_fund_corpus": 10000
        }

        recommendation = {
            "suggested_monthly_investment": 5000,
            "investment_appetite": "High",
            "risk_level": {"label": "HIGH", "color": "error"},
            "warnings": []
        }

        modified_rec, triggered = rules.apply_liquidity_guardrails(recommendation, user_input)

        assert modified_rec["suggested_monthly_investment"] == 0
        assert modified_rec["investment_appetite"] == "Very Low"
        assert len(triggered) > 0
        assert triggered[0]["type"] == "liquidity_insufficient"

    def test_get_emergency_fund_guidance(self):
        """Test emergency fund guidance."""
        rules = LiquidityRules()
        user_input = {
            "income": 45000,
            "rent": 15000,
            "groceries": 8000,
            "transport": 3000,
            "utilities": 2000,
            "healthcare": 1000,
            "emergency_fund_corpus": 10000
        }

        guidance = rules.get_emergency_fund_guidance(user_input)

        assert "liquidity_status" in guidance
        assert "months_covered" in guidance
        assert "gap" in guidance
        assert "priority" in guidance
        assert guidance["priority"] == "high"
