"""
Training script for micro-investing segmentation model with cluster evaluation.

Run this to train the model and save artifacts to the backend artifacts directory.
Includes empirical cluster evaluation (silhouette, elbow, stability).
"""

import os
import json
import warnings
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import RobustScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import silhouette_score
import joblib
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

warnings.filterwarnings("ignore")

# Configuration
ARTIFACT_DIR = os.path.join(os.path.dirname(__file__), "..", "artifacts")
K_CLUSTERS = 3


def compute_total_expenses(row: dict) -> float:
    """Sum all spending categories to get total monthly outflow."""
    cats = [
        "Rent", "Loan_Repayment", "Insurance", "Groceries", "Transport",
        "Eating_Out", "Entertainment", "Utilities", "Healthcare", "Education",
        "Miscellaneous"
    ]
    return sum(row.get(c, 0.0) for c in cats)


def savings_ratio(income: float, total_expenses: float) -> float:
    """Compute savings ratio."""
    return (income - total_expenses) / (income + 1e-9)


def expense_ratio(income: float, total_expenses: float) -> float:
    """Compute expense ratio."""
    return total_expenses / (income + 1e-9)


def train_pipeline():
    """Train the clustering model with cluster evaluation and save artifacts."""
    os.makedirs(ARTIFACT_DIR, exist_ok=True)

    print("=" * 60)
    print("Micro-Investing ML Pipeline Training")
    print("=" * 60)

    # Load dataset
    print("\n1. Loading dataset...")
    try:
        import kagglehub
        path = kagglehub.dataset_download("shriyashjagtap/indian-personal-finance-and-spending-habits")
        csv_file = [f for f in os.listdir(path) if f.endswith(".csv")][0]
        df = pd.read_csv(os.path.join(path, csv_file))
        print(f"   Dataset loaded: {df.shape}")
    except Exception as e:
        print(f"   Warning: Kaggle download failed ({e})")
        print("   Using synthetic data for training...")
        # Generate synthetic data
        np.random.seed(42)
        n_samples = 1000
        df = pd.DataFrame({
            'Income': np.random.lognormal(10.5, 0.5, n_samples),
            'Rent': np.random.lognormal(8.5, 0.5, n_samples),
            'Loan_Repayment': np.random.lognormal(7.5, 0.8, n_samples),
            'Insurance': np.random.lognormal(7.0, 0.5, n_samples),
            'Groceries': np.random.lognormal(8.0, 0.4, n_samples),
            'Transport': np.random.lognormal(7.5, 0.5, n_samples),
            'Eating_Out': np.random.lognormal(7.0, 0.6, n_samples),
            'Entertainment': np.random.lognormal(6.5, 0.6, n_samples),
            'Utilities': np.random.lognormal(7.0, 0.4, n_samples),
            'Healthcare': np.random.lognormal(6.5, 0.6, n_samples),
            'Education': np.random.lognormal(6.0, 0.8, n_samples),
            'Miscellaneous': np.random.lognormal(6.5, 0.6, n_samples),
        })
        print(f"   Synthetic dataset: {df.shape}")

    # Feature engineering
    print("\n2. Feature engineering...")
    if "Rent" in df.columns:
        df["Total_Expenses"] = df.apply(lambda row: compute_total_expenses(row), axis=1)
    else:
        if "Total_Expenses" not in df.columns:
            raise KeyError("Cannot compute Total_Expenses - missing columns")

    df["Savings_Ratio"] = df.apply(
        lambda row: savings_ratio(row["Income"], row["Total_Expenses"]), axis=1
    )
    df["Expense_Ratio"] = df.apply(
        lambda row: expense_ratio(row["Income"], row["Total_Expenses"]), axis=1
    )

    # Prepare features
    X = df[["Savings_Ratio", "Expense_Ratio"]].copy()
    X["Savings_Ratio"] = X["Savings_Ratio"].clip(-1, 1.5)
    X["Expense_Ratio"] = X["Expense_Ratio"].clip(0, 1.5)

    # Impute and scale
    print("\n3. Preprocessing...")
    imputer = SimpleImputer(strategy="median")
    X_imp = imputer.fit_transform(X)

    scaler = RobustScaler()
    X_scaled = scaler.fit_transform(X_imp)

    print("   Imputation and scaling complete")

    # Cluster evaluation
    print("\n4. Cluster evaluation...")
    try:
        from utils.cluster_evaluation import ClusterEvaluator
        evaluator = ClusterEvaluator(random_state=42)

        evaluation_results = evaluator.run_full_evaluation(
            X_scaled, ["Savings_Ratio", "Expense_Ratio"], k_range=(2, 7)
        )

        optimal_k = evaluation_results['optimal_k']
        print(f"   Optimal k: {optimal_k}")
        print(f"   Silhouette scores: {evaluation_results['silhouette_scores']}")
        print(f"   Final silhouette score: {evaluation_results['final_silhouette_score']:.4f}")
        print(f"   Stability: {evaluation_results['stability_analysis']}")

        # Use optimal k
        K_CLUSTERS = optimal_k
        segment_map = evaluation_results['segment_map']

        # Save evaluation results
        with open(os.path.join(ARTIFACT_DIR, "cluster_evaluation.json"), "w") as f:
            json.dump(evaluation_results, f, indent=2)

    except Exception as e:
        print(f"   Warning: Cluster evaluation failed ({e}), using default k=3")
        K_CLUSTERS = 3

    # Cluster
    print(f"\n5. Training KMeans with {K_CLUSTERS} clusters...")
    kmeans = KMeans(n_clusters=K_CLUSTERS, random_state=42, n_init=10)
    df["cluster_id"] = kmeans.fit_predict(X_scaled)

    sil = silhouette_score(X_scaled, df["cluster_id"])
    print(f"   Silhouette Score: {sil:.4f}")

    # Cluster profiles
    profile_df = df.groupby("cluster_id").agg(
        mean_income=("Income", "mean"),
        median_savings_ratio=("Savings_Ratio", "median"),
        mean_expense_ratio=("Expense_Ratio", "mean")
    ).round(4)
    print("\n   Cluster profiles:")
    print(profile_df)

    # Dynamic persona mapping (if not already set)
    if 'segment_map' not in locals():
        median_sr = profile_df["median_savings_ratio"]
        sorted_clusters = median_sr.sort_values().index.tolist()

        segment_map = {
            int(sorted_clusters[0]): {
                "name": "Financially Stressed",
                "plan": "Debt Management & Stabilization",
                "multiplier": 0.0,
                "investment_appetite": "Zero (Build emergency fund)"
            },
            int(sorted_clusters[1]): {
                "name": "Cautious Saver",
                "plan": "Conservative SIP (Index/Liquid Funds)",
                "multiplier": 0.2,
                "investment_appetite": "Low-to-Medium"
            },
            int(sorted_clusters[2]): {
                "name": "Investment Ready",
                "plan": "Moderate-to-Aggressive SIP",
                "multiplier": 0.4,
                "investment_appetite": "High"
            }
        }

    # Save artifacts
    print("\n6. Saving artifacts...")
    joblib.dump(imputer, os.path.join(ARTIFACT_DIR, "imputer.pkl"))
    joblib.dump(scaler, os.path.join(ARTIFACT_DIR, "robust_scaler.pkl"))
    joblib.dump(kmeans, os.path.join(ARTIFACT_DIR, "kmeans_model.pkl"))

    with open(os.path.join(ARTIFACT_DIR, "segment_map.json"), "w") as f:
        json.dump(segment_map, f, indent=2)

    with open(os.path.join(ARTIFACT_DIR, "feature_order.json"), "w") as f:
        json.dump(["Savings_Ratio", "Expense_Ratio"], f)

    # Save metadata
    metadata = {
        "dataset": "Indian Personal Finance and Spending Habits",
        "training_date": pd.Timestamp.now().isoformat(),
        "silhouette_score": float(sil),
        "n_samples": len(df),
        "n_clusters": K_CLUSTERS,
        "features": ["Savings_Ratio", "Expense_Ratio"],
        "segment_labels": [segment_map[k]["name"] for k in sorted(segment_map.keys())],
        "limitations": [
            "Based on clustering only - no supervised learning",
            "Assumes Indian financial context",
            "Does not account for age, dependents, or debt types",
            "Cluster labels may shift on retraining (stability not guaranteed)",
            "Investment allocations are heuristic, not validated by financial experts"
        ],
        "evaluation": {
            "optimal_k_selection": "Silhouette score analysis across k=2 to k=6",
            "stability_analysis": "Multiple random seeds (n=10)"
        }
    }

    with open(os.path.join(ARTIFACT_DIR, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"   Artifacts saved to: {ARTIFACT_DIR}")

    print("\n" + "=" * 60)
    print("Training complete!")
    print("=" * 60)


if __name__ == "__main__":
    train_pipeline()
