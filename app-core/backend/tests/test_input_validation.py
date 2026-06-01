"""Tests for input validation."""

import pytest
from utils.input_validator import InputValidator, ValidationError, ValidationLevel


class TestInputValidator:
    """Tests for InputValidator class."""

    def test_valid_input_passes(self):
        """Test that valid input passes validation."""
        validator = InputValidator()
        user_input = {
            "income": 45000,
            "rent": 10000,
            "groceries": 4000,
            "transport": 2000,
            "dependents": 1,
            "emergency_fund_corpus": 50000
        }

        is_valid, errors, warnings = validator.validate(user_input)

        assert is_valid is True
        assert len(errors) == 0

    def test_negative_income_fails(self):
        """Test that negative income fails validation."""
        validator = InputValidator()
        user_input = {
            "income": -1000,
            "rent": 5000,
            "groceries": 3000
        }

        is_valid, errors, warnings = validator.validate(user_input)

        assert is_valid is False
        assert any("negative" in error.lower() for error in errors)

    def test_zero_income_passes(self):
        """Test that zero income is accepted for onboarding edge cases."""
        validator = InputValidator()
        user_input = {
            "income": 0,
            "rent": 0,
            "groceries": 0
        }

        is_valid, errors, warnings = validator.validate(user_input)

        assert is_valid is True
        assert len(errors) == 0

    def test_expenses_exceed_income_fails(self):
        """Test that expenses exceeding 120% of income fails."""
        validator = InputValidator()
        user_input = {
            "income": 10000,
            "rent": 8000,
            "groceries": 5000,
            "transport": 2000
        }

        is_valid, errors, warnings = validator.validate(user_input)

        assert is_valid is False
        assert any("exceed" in error.lower() for error in errors)

    def test_negative_expense_fails(self):
        """Test that negative expense fails validation."""
        validator = InputValidator()
        user_input = {
            "income": 45000,
            "rent": -1000,
            "groceries": 4000
        }

        is_valid, errors, warnings = validator.validate(user_input)

        assert is_valid is False
        assert any("cannot be negative" in error.lower() for error in errors)

    def test_negative_dependents_fails(self):
        """Test that negative dependents fails validation."""
        validator = InputValidator()
        user_input = {
            "income": 45000,
            "rent": 10000,
            "dependents": -1
        }

        is_valid, errors, warnings = validator.validate(user_input)

        assert is_valid is False
        assert any("cannot be negative" in error.lower() for error in errors)

    def test_invalid_goal_warns(self):
        """Test that invalid goal generates warning."""
        validator = InputValidator()
        user_input = {
            "income": 45000,
            "rent": 10000,
            "goals": ["Invalid Goal", "Retirement"]
        }

        is_valid, errors, warnings = validator.validate(user_input)

        assert is_valid is True
        assert any("Invalid Goal" in warning for warning in warnings)

    def test_should_recommend_investment_low_income(self):
        """Test investment recommendation for low income."""
        validator = InputValidator()
        user_input = {
            "income": 15000,
            "rent": 5000,
            "groceries": 3000,
            "transport": 1000
        }

        should_invest, reason = validator.should_recommend_investment(user_input)

        assert should_invest is False
        assert "below minimum threshold" in reason.lower()

    def test_should_recommend_investment_no_savings(self):
        """Test investment recommendation with no savings."""
        validator = InputValidator()
        user_input = {
            "income": 45000,
            "rent": 30000,
            "groceries": 15000,
            "transport": 5000
        }

        should_invest, reason = validator.should_recommend_investment(user_input)

        assert should_invest is False
        assert "no savings" in reason.lower()

    def test_liquidity_status_insufficient(self):
        """Test liquidity status with insufficient emergency fund."""
        validator = InputValidator()
        user_input = {
            "income": 45000,
            "rent": 15000,
            "groceries": 8000,
            "transport": 3000,
            "utilities": 2000,
            "healthcare": 1000,
            "emergency_fund_corpus": 10000
        }

        status = validator.get_liquidity_status(user_input)

        assert status == "insufficient"

    def test_liquidity_status_strong(self):
        """Test liquidity status with strong emergency fund."""
        validator = InputValidator()
        user_input = {
            "income": 45000,
            "rent": 15000,
            "groceries": 8000,
            "transport": 3000,
            "utilities": 2000,
            "healthcare": 1000,
            "emergency_fund_corpus": 500000
        }

        status = validator.get_liquidity_status(user_input)

        assert status == "strong"

    def test_investment_cap_insufficient_liquidity(self):
        """Test investment cap with insufficient liquidity."""
        validator = InputValidator()
        user_input = {
            "income": 45000,
            "rent": 15000,
            "groceries": 8000,
            "transport": 3000,
            "utilities": 2000,
            "healthcare": 1000,
            "emergency_fund_corpus": 10000
        }

        cap = validator.get_investment_cap(user_input)

        assert cap == 0.0
