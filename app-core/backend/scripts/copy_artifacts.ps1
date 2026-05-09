# PowerShell script to copy ML artifacts from notebook location to backend
# Update the SOURCE_DIR if your artifacts are in a different location

$SOURCE_DIR = "C:\Users\ASUS\Desktop\micro investing"  # Update if needed
$DEST_DIR = Join-Path $PSScriptRoot "..\artifacts" | Resolve-Path

$ARTIFACTS = @("imputer.pkl", "robust_scaler.pkl", "kmeans_model.pkl", "segment_map.json", "feature_order.json")

Write-Host "Copying ML artifacts from $SOURCE_DIR to $DEST_DIR" -ForegroundColor Cyan

foreach ($artifact in $ARTIFACTS) {
    $sourcePath = Join-Path $SOURCE_DIR $artifact
    $destPath = Join-Path $DEST_DIR $artifact

    if (Test-Path $sourcePath) {
        Copy-Item $sourcePath $destPath -Force
        Write-Host "  Copied: $artifact" -ForegroundColor Green
    } else {
        Write-Host "  WARNING: $artifact not found in $SOURCE_DIR" -ForegroundColor Yellow
    }
}

Write-Host "`nArtifacts directory: $DEST_DIR" -ForegroundColor Cyan
Write-Host "Contents:" -ForegroundColor Cyan
Get-ChildItem $DEST_DIR | ForEach-Object { Write-Host "  $($_.Name)" }
