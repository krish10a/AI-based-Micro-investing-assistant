"""
Training script for micro-investing segmentation model.

Run this to train the model and save artifacts to the backend artifacts directory.
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
import kagglehub

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
    """Train the clustering model and save artifacts."""
    os.makedirs(ARTIFACT_DIR, exist_ok=True)

    print("Downloading dataset...")
    try:
        path = kagglehub.dataset_download("shriyashjagtap/indian-personal-finance-and-spending-habits")
        csv_file = [f for f in os.listdir(path) if f.endswith(".csv")][0]
        df = pd.read_csv(os.path.join(path, csv_file))
    except Exception as e:
        print(f"Kaggle download failed: {e}")
        print("Please manually download the dataset and place it in data/ folder")
        return

    print(f"Dataset shape: {df.shape}")

    # Feature engineering
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
    imputer = SimpleImputer(strategy="median")
    X_imp = imputer.fit_transform(X)

    scaler = RobustScaler()
    X_scaled = scaler.fit_transform(X_imp)

    # Cluster
    print(f"\nTraining KMeans with {K_CLUSTERS} clusters...")
    kmeans = KMeans(n_clusters=K_CLUSTERS, random_state=42, n_init=10)
    df["cluster_id"] = kmeans.fit_predict(X_scaled)

    sil = silhouette_score(X_scaled, df["cluster_id"])
    print(f"Silhouette Score: {sil:.4f}")

    # Cluster profiles
    profile_df = df.groupby("cluster_id").agg(
        mean_income=("Income", "mean"),
        median_savings_ratio=("Savings_Ratio", "median"),
        mean_expense_ratio=("Expense_Ratio", "mean")
    ).round(4)
    print("\nCluster profiles:")
    print(profile_df)

    # Dynamic persona mapping
    median_sr = profile_df["median_savings_ratio"]
    sorted_clusters = median_sr.sort_values().index.tolist()

    SEGMENT_MAP = {
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
    joblib.dump(imputer, os.path.join(ARTIFACT_DIR, "imputer.pkl"))
    joblib.dump(scaler, os.path.join(ARTIFACT_DIR, "robust_scaler.pkl"))
    joblib.dump(kmeans, os.path.join(ARTIFACT_DIR, "kmeans_model.pkl"))

    with open(os.path.join(ARTIFACT_DIR, "segment_map.json"), "w") as f:
        json.dump(SEGMENT_MAP, f, indent=2)

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
        "segment_labels": [SEGMENT_MAP[k]["name"] for k in sorted(SEGMENT_MAP.keys())],
        "limitations": [
            "Based on clustering only - no supervised learning",
            "Assumes Indian financial context",
            "Does not account for age, dependents, or debt types"
        ]
    }

    with open(os.path.join(ARTIFACT_DIR, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nArtifacts saved to: {ARTIFACT_DIR}")
    print("Training complete!")


if __name__ == "__main__":
    train_pipeline()
