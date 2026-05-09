"""Tests for feature engineering functions."""

import pytest
from utils.feature_engineering import (
    compute_total_expenses,
    compute_savings_ratio,
    compute_expense_ratio,
    build_features
)


def test_compute_total_expenses():
    """Test total expenses calculation."""
    user = {
        "rent": 10000,
        "groceries": 4000,
        "transport": 2000,
        "eating_out": 2000
    }
    result = compute_total_expenses(user)
    assert result == 18000


def test_compute_total_expenses_empty():
    """Test with empty user dict."""
    result = compute_total_expenses({})
    assert result == 0.0


def test_compute_savings_ratio():
    """Test savings ratio calculation."""
    result = compute_savings_ratio(50000, 30000)
    assert result == 0.4


def test_compute_savings_ratio_zero_income():
    """Test savings ratio with zero income."""
    result = compute_savings_ratio(0, 10000)
    assert result == 0.0


def test_compute_expense_ratio():
    """Test expense ratio calculation."""
    result = compute_expense_ratio(50000, 30000)
    assert result == 0.6


def test_build_features():
    """Test complete feature building."""
    user = {
        "income": 50000,
        "rent": 10000,
        "groceries": 5000,
        "transport": 2000
    }

    features, income, expenses, savings = build_features(user)

    assert len(features) == 2  # savings_ratio, expense_ratio
    assert income == 50000
    assert expenses == 17000
    assert savings == 33000
    assert 0 <= features[0] <= 1.5  # savings ratio
    assert 0 <= features[1] <= 1.5  # expense ratio


def test_build_features_clips_values():
    """Test that build_features clips impossible values."""
    user = {
        "income": 10000,
        "rent": 20000,  # More than income
        "groceries": 5000
    }

    features, _, _, _ = build_features(user)

    # Savings ratio should be clipped to -1
    assert features[0] >= -1.0
    # Expense ratio should be clipped to 1.5
    assert features[1] <= 1.5
