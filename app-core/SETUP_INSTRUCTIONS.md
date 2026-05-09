# Micro-Investing Assistant - Setup Instructions

## Quick Start

### 1. Install Dependencies

```bash
cd app-core/backend

# Using uv (recommended)
uv sync

# Or pip
pip install -r requirements.txt
```

### 2. Copy ML Artifacts

You need to copy the ML model artifacts from your notebook training location to the backend artifacts folder.

**Option A: From Google Colab**

Add this code to the end of your notebook cell that trains the model:

```python
import shutil
import os

# Backend artifacts directory (mount Google Drive first if needed)
backend_dir = "/content/drive/MyDrive/app-core/backend/artifacts"
os.makedirs(backend_dir, exist_ok=True)

# Copy artifacts
artifacts = ["imputer.pkl", "robust_scaler.pkl", "kmeans_model.pkl", "segment_map.json", "feature_order.json"]
for f in artifacts:
    shutil.copy(os.path.join("/content/micro_investing_artifacts", f), backend_dir)
    print(f"Copied: {f}")

print("Artifacts ready for backend!")
```

**Option B: From Local Machine**

If you trained the model locally, copy the files from the training output location to:
`app-core/backend/artifacts/`

### 3. Configure Environment

The `.env.example` file already has the NVIDIA NIM API key configured. Copy it:

```bash
cp .env.example .env
```

### 4. Run Tests

```bash
# Run feature engineering tests (these don't need artifacts)
uv run pytest tests/test_feature_engineering.py -v

# Run all tests (may fail if artifacts not loaded)
uv run pytest -v
```

### 5. Start the Server

**PowerShell (Windows):**
```powershell
cd backend; uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Bash/Mac/Linux:**
```bash
cd backend && uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Endpoints

- `GET /health` - Health check
- `GET /api/v1/model-info` - Model metadata
- `POST /api/v1/analyze-user` - Get investment recommendation
- `POST /api/v1/chat` - Conversational follow-up

## Testing the API

Use curl or Postman to test:

```bash
curl -X POST http://localhost:8000/api/v1/analyze-user \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
```

## Project Structure

```
app-core/
└── backend/
    ├── main.py                 # FastAPI entry point
    ├── config/
    │   └── settings.py         # Settings (NIM API key, model config)
    ├── models/
    │   ├── schemas.py          # Pydantic request/response models
    │   └── ml_pipeline.py      # ML inference class
    ├── services/
    │   ├── ml_service.py       # ML service wrapper
    │   ├── nim_service.py      # NVIDIA NIM explanation service
    │   └── recommendation_service.py  # Main orchestration
    ├── routes/
    │   └── api.py              # API endpoints
    ├── utils/
    │   └── feature_engineering.py  # Feature computation
    ├── scripts/
    │   ├── train_model.py      # Train model locally
    │   ├── export_artifacts.py # Export from notebook
    │   └── copy_artifacts.ps1  # PowerShell copy script
    ├── tests/
    │   ├── conftest.py         # Pytest fixtures
    │   ├── test_feature_engineering.py
    │   ├── test_ml_pipeline.py
    │   └── test_endpoints.py
    ├── artifacts/              # ML model artifacts (place here)
    ├── requirements.txt
    ├── .env.example
    └── README.md
```

## Next Steps

1. Copy ML artifacts to `backend/artifacts/`
2. Run tests to verify everything works
3. Start the server
4. Test the API endpoints
5. (Later) UI integration using Google Stitch Labs
