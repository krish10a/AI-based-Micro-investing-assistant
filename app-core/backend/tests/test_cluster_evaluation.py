"""Tests for cluster evaluation."""

import pytest
import numpy as np
from utils.cluster_evaluation import ClusterEvaluator


class TestClusterEvaluator:
    """Tests for ClusterEvaluator class."""

    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing."""
        np.random.seed(42)
        # Create 3 distinct clusters
        cluster1 = np.random.normal([0.2, 0.8], 0.1, (50, 2))
        cluster2 = np.random.normal([0.5, 0.5], 0.1, (50, 2))
        cluster3 = np.random.normal([0.8, 0.2], 0.1, (50, 2))
        return np.vstack([cluster1, cluster2, cluster3])

    def test_evaluate_k_range(self, sample_data):
        """Test evaluation across k range."""
        evaluator = ClusterEvaluator(random_state=42)

        results = evaluator.evaluate_k_range(sample_data, k_range=(2, 5))

        assert "silhouette_scores" in results
        assert "inertia" in results
        assert len(results["silhouette_scores"]) == 3  # k=2,3,4
        assert all(0 <= score <= 1 for score in results["silhouette_scores"].values())

    def test_find_optimal_k(self, sample_data):
        """Test finding optimal k."""
        evaluator = ClusterEvaluator(random_state=42)

        optimal_k = evaluator.find_optimal_k(sample_data, k_range=(2, 5))

        assert 2 <= optimal_k <= 4
        assert isinstance(optimal_k, int)

    def test_analyze_stability(self, sample_data):
        """Test stability analysis."""
        evaluator = ClusterEvaluator(random_state=42)

        stability = evaluator.analyze_stability(sample_data, k=3, n_seeds=5)

        assert "mean_silhouette" in stability
        assert "std_silhouette" in stability
        assert "cluster_stability" in stability
        assert "n_seeds" in stability
        assert stability["n_seeds"] == 5
        assert 0 <= stability["mean_silhouette"] <= 1
        assert stability["std_silhouette"] >= 0

    def test_generate_cluster_profiles(self, sample_data):
        """Test cluster profile generation."""
        evaluator = ClusterEvaluator(random_state=42)

        kmeans = evaluator.__class__.__bases__[0]  # Get KMeans
        from sklearn.cluster import KMeans
        kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
        labels = kmeans.fit_predict(sample_data)

        profiles = evaluator.generate_cluster_profiles(
            sample_data, labels, ["Savings_Ratio", "Expense_Ratio"]
        )

        assert len(profiles) == 3
        for profile in profiles:
            assert "cluster_id" in profile
            assert "n_samples" in profile
            assert "mean" in profile
            assert "median" in profile
            assert "std" in profile
            assert "min" in profile
            assert "max" in profile

    def test_generate_segment_map(self, sample_data):
        """Test segment map generation."""
        evaluator = ClusterEvaluator(random_state=42)

        from sklearn.cluster import KMeans
        kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
        labels = kmeans.fit_predict(sample_data)

        profiles = evaluator.generate_cluster_profiles(
            sample_data, labels, ["Savings_Ratio", "Expense_Ratio"]
        )

        segment_map = evaluator.generate_segment_map(profiles, ["Savings_Ratio", "Expense_Ratio"])

        assert len(segment_map) == 3
        for cluster_id, segment in segment_map.items():
            assert "name" in segment
            assert "plan" in segment
            assert "multiplier" in segment
            assert "investment_appetite" in segment

    def test_run_full_evaluation(self, sample_data):
        """Test full evaluation pipeline."""
        evaluator = ClusterEvaluator(random_state=42)

        results = evaluator.run_full_evaluation(
            sample_data, ["Savings_Ratio", "Expense_Ratio"], k_range=(2, 5)
        )

        assert "optimal_k" in results
        assert "silhouette_scores" in results
        assert "inertia" in results
        assert "stability_analysis" in results
        assert "cluster_profiles" in results
        assert "segment_map" in results
        assert "final_silhouette_score" in results
        assert "n_features" in results
        assert "feature_names" in results

    def test_save_and_load_results(self, sample_data, tmp_path):
        """Test saving and loading evaluation results."""
        evaluator = ClusterEvaluator(random_state=42)

        results = evaluator.run_full_evaluation(
            sample_data, ["Savings_Ratio", "Expense_Ratio"], k_range=(2, 5)
        )

        filepath = tmp_path / "evaluation.json"
        evaluator.save_results(str(filepath))

        loaded_results = ClusterEvaluator.load_results(str(filepath))

        assert loaded_results == results
