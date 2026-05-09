# Micro-Investment Assistant - Implementation Plan

## Project Overview

A beginner-safe micro-investing assistant that helps users with small monthly savings understand how to start investing responsibly. The system uses behavioral clustering (ML) to segment users and Gemini AI to explain recommendations in beginner-friendly language.

## Architecture

```
User → Frontend (Vercel) → FastAPI Backend (Railway) → ML Inference → Gemini Explanation → Response
```

## Current State

- **ML Pipeline**: Complete and working (see `ml_part.ipynb`)
  - 20,000-row Indian personal finance dataset
  - 3 behavioral clusters (Savings_Ratio, Expense_Ratio)
  - Safety guardrails implemented
  - Artifacts: imputer, scaler, kmeans, segment_map, feature_order

- **app-core folder**: Empty structure ready for production code

## Implementation Phases

### Phase 1: Backend Foundation (FastAPI)

**Goal**: Create the core API that orchestrates ML inference and Gemini explanations.

**Files to create**:
```
app-core/backend/
├── main.py                    # FastAPI app entry point
├── config/
│   └── settings.py            # Pydantic settings (GEMINI_API_KEY, etc.)
├── models/
│   ├── schemas.py             # Request/Response Pydantic models
│   └── ml_pipeline.py         # ML inference class (from notebook)
├── services/
│   ├── ml_service.py          # ML inference wrapper
│   ├── gemini_service.py      # Gemini explanation layer
│   └── recommendation_service.py # Orchestration + policy guardrails
├── routes/
│   └── api.py                 # API endpoints
├── utils/
│   ├── feature_engineering.py # Feature computation (shared with training)
│   └── logging_config.py      # Logging setup
├── artifacts/                 # ML model artifacts (gitignored)
│   ├── imputer.pkl
│   ├── robust_scaler.pkl
│   ├── kmeans_model.pkl
│   ├── segment_map.json
│   └── feature_order.json
├── tests/
│   ├── test_ml_service.py
│   ├── test_gemini_service.py
│   └── test_endpoints.py
└── requirements.txt
```

**Endpoints**:
- `POST /analyze-user` - Full recommendation flow
- `POST /chat` - Conversational follow-up
- `GET /health` - Health check
- `GET /model-info` - Model metadata

### Phase 2: ML Integration

**Goal**: Port the working ML code from notebook to production structure.

**Key tasks**:
1. Copy `MicroInvestmentAssistant` class to `models/ml_pipeline.py`
2. Copy feature engineering functions to `utils/feature_engineering.py`
3. Set up artifact loading at startup
4. Add input validation (negative income, missing values, etc.)
5. Add confidence scoring
6. Write unit tests for ML service

### Phase 3: Gemini Explanation Layer

**Goal**: Add controlled natural language explanations.

**System prompt requirements**:
- Micro-investing guide for beginners
- Stay inside finance education domain
- No specific stock recommendations
- No profit promises
- Simple language, short paragraphs
- Reinforce safety before risk

**Policy guardrails**:
- Zero savings → emergency fund first
- Negative savings → reduce risk aggressiveness
- Stock tips → refuse and redirect to strategy

### Phase 4: Testing & Deployment

**Goal**: Ensure reliability and deploy to Railway.

**Tasks**:
1. Add request/response logging
2. Add error handling with fallbacks
3. Test edge cases (zero savings, overspending, incomplete inputs)
4. Add timeout handling for Gemini
5. Deploy backend to Railway
6. Set environment variables

### Phase 5: UI Integration (Final)

**Goal**: Wrap with Stitch-generated UI.

**Note**: UI will be generated separately using Google Stitch Labs.
When ready, user will explicitly command: "wrap our project with stitch ui"

---

## Next Steps

1. **Start Phase 1**: Create backend folder structure and FastAPI foundation
2. **Port ML code**: Move working ML pipeline to production structure
3. **Add Gemini layer**: Implement controlled explanation service
4. **Test thoroughly**: Edge cases, error handling, fallbacks
5. **Deploy**: Railway deployment with environment config
6. **UI**: Wait for explicit command to integrate Stitch UI
