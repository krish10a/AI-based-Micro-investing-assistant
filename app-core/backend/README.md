# Micro-Investing Assistant Backend

FastAPI backend for beginner-safe micro-investing recommendations using behavioral clustering and NVIDIA NIM AI.

## Setup

### 1. Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or pip
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

The NVIDIA NIM API key is already configured in `.env.example`.

### 3. Set Up ML Artifacts

Option A: Copy from notebook (if running on Colab):
```python
# In your notebook after training
from google.colab import files
import shutil

artifacts_dir = "/content/micro_investing_artifacts"
backend_dir = "/content/drive/MyDrive/app-core/backend/artifacts"

os.makedirs(backend_dir, exist_ok=True)
for f in ["imputer.pkl", "robust_scaler.pkl", "kmeans_model.pkl", "segment_map.json", "feature_order.json"]:
    shutil.copy(os.path.join(artifacts_dir, f), backend_dir)
```

Option B: Train locally:
```bash
uv run python scripts/train_model.py
```

### 4. Run Tests

```bash
uv run pytest
```

### 5. Run Server

**PowerShell (Windows):**
```powershell
cd backend; uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Bash/Mac/Linux:**
```bash
cd backend && uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service info |
| `/health` | GET | Health check |
| `/api/v1/model-info` | GET | Model metadata |
| `/api/v1/analyze-user` | POST | Get investment recommendation |
| `/api/v1/chat` | POST | Conversational follow-up |

## Request/Response Examples

### Analyze User

**Request:**
```json
{
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
}
```

**Response:**
```json
{
  "segment": "Cautious Saver",
  "risk_level": "medium",
  "suggested_monthly_investment": 1800.0,
  "investment_appetite": "Low-to-Medium",
  "reason_codes": [],
  "confidence": 0.75,
  "financial_summary": "Monthly income: 45000, Monthly savings: 9000",
  "safe_action": "Start a small SIP of 500-1000 per month in a liquid or index fund",
  "nim_explanation": "Based on your financial profile...",
  "warnings": []
}
```

## Project Structure

```
backend/
├── main.py                 # FastAPI entry point
├── config/
│   └── settings.py         # Pydantic settings
├── models/
│   ├── schemas.py          # Request/Response models
│   └── ml_pipeline.py      # ML inference class
├── services/
│   ├── ml_service.py       # ML wrapper
│   ├── nim_service.py      # NVIDIA NIM explanations
│   └── recommendation_service.py  # Orchestration
├── routes/
│   └── api.py              # API endpoints
├── utils/
│   └── feature_engineering.py  # Feature computation
├── scripts/
│   ├── train_model.py      # Training script
│   └── export_artifacts.py # Export from notebook
├── tests/
│   ├── conftest.py         # Pytest fixtures
│   ├── test_feature_engineering.py
│   ├── test_ml_pipeline.py
│   └── test_endpoints.py
└── artifacts/              # ML model artifacts (gitignored)
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NVIDIA_NIM_API_KEY` | Yes | - | NVIDIA NIM API key |
| `HOST` | No | 0.0.0.0 | Server host |
| `PORT` | No | 8000 | Server port |
| `ARTIFACTS_DIR` | No | ./artifacts | ML artifacts directory |
| `LOG_LEVEL` | No | INFO | Logging level |
| `NIM_MODEL` | No | moonshotai/kimi-k2-thinking | NIM model for explanations |
| `NIM_TEMPERATURE` | No | 1.0 | Generation temperature |
| `NIM_TOP_P` | No | 0.9 | Top-p sampling |
| `NIM_MAX_TOKENS` | No | 16384 | Max response tokens |
