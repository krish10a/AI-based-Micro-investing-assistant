"""Tests for ML pipeline."""

import pytest
import os
import sys
import json
import joblib
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_test_artifacts():
    """Create minimal test artifacts for testing."""
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import RobustScaler
    from sklearn.impute import SimpleImputer

    artifacts_dir = os.path.join(os.path.dirname(__file__), "..", "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)

    # Create dummy models
    imputer = SimpleImputer(strategy="median")
    scaler = RobustScaler()
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)

    # Fit on dummy data
    dummy_data = np.array([[0.2, 0.8], [0.5, 0.5], [0.8, 0.2]])
    imputer.fit(dummy_data)
    scaler.fit(imputer.transform(dummy_data))
    kmeans.fit(scaler.transform(imputer.transform(dummy_data)))

    # Save artifacts
    joblib.dump(imputer, os.path.join(artifacts_dir, "imputer.pkl"))
    joblib.dump(scaler, os.path.join(artifacts_dir, "robust_scaler.pkl"))
    joblib.dump(kmeans, os.path.join(artifacts_dir, "kmeans_model.pkl"))

    segment_map = {
        0: {"name": "Financially Stressed", "plan": "Debt Management", "multiplier": 0.0, "investment_appetite": "Zero"},
        1: {"name": "Cautious Saver", "plan": "Conservative SIP", "multiplier": 0.2, "investment_appetite": "Low"},
        2: {"name": "Investment Ready", "plan": "Moderate SIP", "multiplier": 0.4, "investment_appetite": "High"}
    }
    with open(os.path.join(artifacts_dir, "segment_map.json"), "w") as f:
        json.dump(segment_map, f)

    with open(os.path.join(artifacts_dir, "feature_order.json"), "w") as f:
        json.dump(["Savings_Ratio", "Expense_Ratio"], f)


@pytest.fixture(scope="module")
def test_artifacts():
    """Ensure test artifacts exist."""
    create_test_artifacts()


@pytest.mark.usefixtures("test_artifacts")
class TestMLPipeline:
    """Tests for ML pipeline."""

    def test_load_assistant(self):
        """Test that assistant loads successfully."""
        from models.ml_pipeline import MicroInvestmentAssistant
        assistant = MicroInvestmentAssistant()
        assert assistant.imputer is not None
        assert assistant.scaler is not None
        assert assistant.kmeans is not None
        assert assistant.segment_map is not None

    def test_recommend_stressed_user(self):
        """Test recommendation for financially stressed user."""
        from models.ml_pipeline import MicroInvestmentAssistant
        assistant = MicroInvestmentAssistant()

        # Test with negative savings - should trigger guardrail
        rec, override, mult_override = assistant.recommend([0.1, 0.9], -1000, 50000)

        # Should apply guardrail
        assert rec["suggested_monthly_investment"] == 0.0
        assert len(rec["reason_codes"]) > 0

    def test_cluster_separation_score_range(self):
        """Test that cluster separation score is in valid range."""
        from models.ml_pipeline import MicroInvestmentAssistant
        assistant = MicroInvestmentAssistant()

        score = assistant.cluster_separation_score([0.5, 0.5])
        assert 0.0 <= score <= 1.0

    def test_get_model_info(self):
        """Test model info retrieval."""
        from models.ml_pipeline import MicroInvestmentAssistant
        assistant = MicroInvestmentAssistant()

        info = assistant.get_model_info()

        assert "model_name" in info
        assert "version" in info
        assert "segment_labels" in info
        assert "features" in info
        assert len(info["segment_labels"]) == 3
