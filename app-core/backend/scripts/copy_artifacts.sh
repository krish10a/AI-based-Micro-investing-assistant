#!/bin/bash
# Bash script to copy ML artifacts from notebook location to backend
# Update the SOURCE_DIR if your artifacts are in a different location

SOURCE_DIR="/content/micro_investing_artifacts"  # Default Colab path
DEST_DIR="$(dirname "$0")/../artifacts"

# Check if running from Colab
if [ -d "/content/micro_investing_artifacts" ]; then
    SOURCE_DIR="/content/micro_investing_artifacts"
elif [ -d "C:/Users/ASUS/Desktop/micro investing" ]; then
    SOURCE_DIR="C:/Users/ASUS/Desktop/micro investing"
fi

echo "Copying ML artifacts from $SOURCE_DIR to $DEST_DIR"

mkdir -p "$DEST_DIR"

ARTIFACTS=("imputer.pkl" "robust_scaler.pkl" "kmeans_model.pkl" "segment_map.json" "feature_order.json")

for artifact in "${ARTIFACTS[@]}"; do
    if [ -f "$SOURCE_DIR/$artifact" ]; then
        cp "$SOURCE_DIR/$artifact" "$DEST_DIR/$artifact"
        echo "  Copied: $artifact"
    else
        echo "  WARNING: $artifact not found in $SOURCE_DIR"
    fi
done

echo ""
echo "Artifacts directory: $DEST_DIR"
echo "Contents:"
ls -la "$DEST_DIR"
