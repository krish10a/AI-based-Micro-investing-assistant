"""
Export ML artifacts from the trained model to the backend artifacts directory.

Run this after training the model in the notebook to copy artifacts to the backend.
"""

import os
import json
import shutil
import joblib

# Source: notebook artifacts directory (update if different)
NOTEBOOK_ARTIFACTS_DIR = "/content/micro_investing_artifacts"

# Target: backend artifacts directory
BACKEND_ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "..", "artifacts")


def export_artifacts():
    """Copy ML artifacts from notebook to backend."""
    os.makedirs(BACKEND_ARTIFACTS_DIR, exist_ok=True)

    artifacts = [
        "imputer.pkl",
        "robust_scaler.pkl",
        "kmeans_model.pkl",
        "segment_map.json",
        "feature_order.json"
    ]

    for artifact in artifacts:
        src = os.path.join(NOTEBOOK_ARTIFACTS_DIR, artifact)
        dst = os.path.join(BACKEND_ARTIFACTS_DIR, artifact)

        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"Copied: {artifact}")
        else:
            print(f"WARNING: {artifact} not found at {src}")

    print(f"\nArtifacts exported to: {BACKEND_ARTIFACTS_DIR}")


if __name__ == "__main__":
    export_artifacts()
