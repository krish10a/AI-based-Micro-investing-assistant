"""Pytest configuration and fixtures."""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def sample_user_input():
    """Sample valid user financial input."""
    return {
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


@pytest.fixture
def stressed_user_input():
    """Sample user with negative savings."""
    return {
        "income": 15000,
        "rent": 5000,
        "loan_repayment": 6000,
        "insurance": 500,
        "groceries": 2000,
        "transport": 500,
        "eating_out": 500,
        "entertainment": 200,
        "utilities": 300,
        "healthcare": 200,
        "education": 0,
        "miscellaneous": 300,
        "dependents": 2
    }


@pytest.fixture
def high_income_user():
    """Sample high income user with healthy savings."""
    return {
        "income": 120000,
        "rent": 20000,
        "loan_repayment": 5000,
        "insurance": 3000,
        "groceries": 6000,
        "transport": 3000,
        "eating_out": 3000,
        "entertainment": 2000,
        "utilities": 2000,
        "healthcare": 1000,
        "education": 2000,
        "miscellaneous": 1000,
        "dependents": 0
    }
