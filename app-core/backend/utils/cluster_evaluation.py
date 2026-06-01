"""Cluster evaluation utility for ML pipeline.

This module provides empirical evaluation of clustering results including:
- Silhouette score analysis across different k values
- Elbow method for optimal cluster selection
- Stability analysis across multiple random seeds
- Cluster profiling and characterization
"""

import json
import numpy as np
from typing import Dict, List, Any, Tuple
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import RobustScaler
from sklearn.impute import SimpleImputer


class ClusterEvaluator:
    """
    Empirical cluster evaluation and analysis.

    Provides:
    - Silhouette score computation for k=2 to k=6
    - Elbow method (inertia vs k)
    - Stability analysis across random seeds
    - Cluster profiles (mean/median per cluster)
    """

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.results: Dict[str, Any] = {}

    def evaluate_k_range(
        self,
        X: np.ndarray,
        k_range: Tuple[int, int] = (2, 7)
    ) -> Dict[str, Any]:
        """
        Evaluate clustering across a range of k values.

        Args:
            X: Feature matrix
            k_range: Range of k values to evaluate (inclusive start, exclusive end)

        Returns:
            Dictionary with silhouette scores and inertia for each k
        """
        silhouette_scores = {}
        inertia_values = {}

        for k in range(k_range[0], k_range[1]):
            kmeans = KMeans(n_clusters=k, random_state=self.random_state, n_init=10)
            labels = kmeans.fit_predict(X)

            # Silhouette score
            if len(np.unique(labels)) > 1:
                sil_score = silhouette_score(X, labels)
                silhouette_scores[f"k={k}"] = float(sil_score)
            else:
                silhouette_scores[f"k={k}"] = 0.0

            # Inertia (within-cluster sum of squares)
            inertia_values[f"k={k}"] = float(kmeans.inertia_)

        return {
            "silhouette_scores": silhouette_scores,
            "inertia": inertia_values
        }

    def find_optimal_k(
        self,
        X: np.ndarray,
        k_range: Tuple[int, int] = (2, 7)
    ) -> int:
        """
        Find optimal k using silhouette score.

        Args:
            X: Feature matrix
            k_range: Range of k values to evaluate

        Returns:
            Optimal k value
        """
        evaluation = self.evaluate_k_range(X, k_range)
        silhouette_scores = evaluation["silhouette_scores"]

        # Find k with maximum silhouette score
        optimal_k = max(
            silhouette_scores.items(),
            key=lambda x: x[1]
        )[0]

        # Extract k value from "k=3" format
        return int(optimal_k.split("=")[1])

    def analyze_stability(
        self,
        X: np.ndarray,
        k: int,
        n_seeds: int = 10
    ) -> Dict[str, Any]:
        """
        Analyze cluster stability across multiple random seeds.

        Args:
            X: Feature matrix
            k: Number of clusters
            n_seeds: Number of random seeds to test

        Returns:
            Stability analysis results
        """
        silhouette_scores = []
        cluster_centers_list = []

        for i in range(n_seeds):
            seed = self.random_state + i
            kmeans = KMeans(n_clusters=k, random_state=seed, n_init=10)
            labels = kmeans.fit_predict(X)

            if len(np.unique(labels)) > 1:
                sil_score = silhouette_score(X, labels)
                silhouette_scores.append(sil_score)

            cluster_centers_list.append(kmeans.cluster_centers_)

        # Compute statistics
        mean_silhouette = np.mean(silhouette_scores)
        std_silhouette = np.std(silhouette_scores)

        # Compute cluster center stability (average distance between centers)
        center_stability = self._compute_center_stability(cluster_centers_list)

        return {
            "mean_silhouette": float(mean_silhouette),
            "std_silhouette": float(std_silhouette),
            "cluster_stability": [float(s) for s in center_stability],
            "n_seeds": n_seeds
        }

    def _compute_center_stability(self, centers_list: List[np.ndarray]) -> List[float]:
        """Compute stability of cluster centers across runs."""
        if len(centers_list) < 2:
            return [1.0]

        n_clusters = centers_list[0].shape[0]
        stability_scores = []

        for i in range(n_clusters):
            # Get center i from all runs
            centers_i = np.array([c[i] for c in centers_list])

            # Compute average pairwise distance
            distances = []
            for j in range(len(centers_i)):
                for k in range(j + 1, len(centers_i)):
                    dist = np.linalg.norm(centers_i[j] - centers_i[k])
                    distances.append(dist)

            if distances:
                avg_distance = np.mean(distances)
                # Convert to stability score (lower distance = higher stability)
                # Normalize by average center magnitude
                avg_magnitude = np.mean(np.linalg.norm(centers_i, axis=1))
                stability = 1.0 - (avg_distance / (avg_magnitude + 1e-9))
                stability_scores.append(max(0.0, min(1.0, stability)))
            else:
                stability_scores.append(1.0)

        return stability_scores

    def generate_cluster_profiles(
        self,
        X: np.ndarray,
        labels: np.ndarray,
        feature_names: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Generate profiles for each cluster.

        Args:
            X: Feature matrix
            labels: Cluster labels
            feature_names: Names of features

        Returns:
            List of cluster profiles
        """
        unique_labels = np.unique(labels)
        profiles = []

        for label in unique_labels:
            mask = labels == label
            cluster_data = X[mask]

            profile = {
                "cluster_id": int(label),
                "n_samples": int(np.sum(mask)),
                "mean": {feature_names[i]: float(np.mean(cluster_data[:, i])) for i in range(len(feature_names))},
                "median": {feature_names[i]: float(np.median(cluster_data[:, i])) for i in range(len(feature_names))},
                "std": {feature_names[i]: float(np.std(cluster_data[:, i])) for i in range(len(feature_names))},
                "min": {feature_names[i]: float(np.min(cluster_data[:, i])) for i in range(len(feature_names))},
                "max": {feature_names[i]: float(np.max(cluster_data[:, i])) for i in range(len(feature_names))}
            }

            profiles.append(profile)

        return profiles

    def generate_segment_map(
        self,
        cluster_profiles: List[Dict[str, Any]],
        feature_names: List[str]
    ) -> Dict[int, Dict[str, Any]]:
        """
        Generate segment map based on cluster profiles.

        Args:
            cluster_profiles: List of cluster profiles
            feature_names: Names of features

        Returns:
            Segment map with cluster labels and investment multipliers
        """
        # Sort clusters by median savings ratio (assuming it's the first feature)
        savings_ratio_idx = feature_names.index("Savings_Ratio") if "Savings_Ratio" in feature_names else 0

        sorted_profiles = sorted(
            cluster_profiles,
            key=lambda p: p["median"][feature_names[savings_ratio_idx]]
        )

        # Assign segments based on sorted order
        segment_map = {}

        for i, profile in enumerate(sorted_profiles):
            cluster_id = profile["cluster_id"]
            median_savings = profile["median"][feature_names[savings_ratio_idx]]

            if i == 0:
                # Lowest savings - Financially Stressed
                segment_map[cluster_id] = {
                    "name": "Financially Stressed",
                    "plan": "Debt Management & Stabilization",
                    "multiplier": 0.0,
                    "investment_appetite": "Zero (Build emergency fund)"
                }
            elif i == len(sorted_profiles) - 1:
                # Highest savings - Investment Ready
                segment_map[cluster_id] = {
                    "name": "Investment Ready",
                    "plan": "Moderate-to-Aggressive SIP",
                    "multiplier": 0.4,
                    "investment_appetite": "High"
                }
            else:
                # Middle - Cautious Saver
                segment_map[cluster_id] = {
                    "name": "Cautious Saver",
                    "plan": "Conservative SIP (Index/Liquid Funds)",
                    "multiplier": 0.2,
                    "investment_appetite": "Low-to-Medium"
                }

        return segment_map

    def run_full_evaluation(
        self,
        X: np.ndarray,
        feature_names: List[str],
        k_range: Tuple[int, int] = (2, 7)
    ) -> Dict[str, Any]:
        """
        Run complete cluster evaluation pipeline.

        Args:
            X: Feature matrix
            feature_names: Names of features
            k_range: Range of k values to evaluate

        Returns:
            Complete evaluation results
        """
        # Find optimal k
        optimal_k = self.find_optimal_k(X, k_range)

        # Train final model with optimal k
        kmeans = KMeans(n_clusters=optimal_k, random_state=self.random_state, n_init=10)
        labels = kmeans.fit_predict(X)

        # Evaluate k range
        k_evaluation = self.evaluate_k_range(X, k_range)

        # Analyze stability
        stability = self.analyze_stability(X, optimal_k)

        # Generate cluster profiles
        profiles = self.generate_cluster_profiles(X, labels, feature_names)

        # Generate segment map
        segment_map = self.generate_segment_map(profiles, feature_names)

        # Compile results
        results = {
            "optimal_k": optimal_k,
            "silhouette_scores": k_evaluation["silhouette_scores"],
            "inertia": k_evaluation["inertia"],
            "stability_analysis": stability,
            "cluster_profiles": profiles,
            "segment_map": segment_map,
            "final_silhouette_score": float(k_evaluation["silhouette_scores"][f"k={optimal_k}"]),
            "n_features": len(feature_names),
            "feature_names": feature_names
        }

        self.results = results
        return results

    def save_results(self, filepath: str):
        """Save evaluation results to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2)

    @staticmethod
    def load_results(filepath: str) -> Dict[str, Any]:
        """Load evaluation results from JSON file."""
        with open(filepath, 'r') as f:
            return json.load(f)
