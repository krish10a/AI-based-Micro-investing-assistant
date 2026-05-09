# System Contract: Micro-Investing Assistant

## 1. Product Definition & Scope Freeze

### Core Positioning
**Beginner-safe micro-investing assistant operating exclusively within financial education and behavioral guidance.**

**Explicitly OUT of scope:**
- Stock-picking or individual equity recommendations
- Market movement predictions
- Guaranteed return claims
- Financial advisory services (SEBI registered)
- Open-ended predictive chat

### Input Variables (Fixed)
The system processes ONLY these inputs:
- `income`: Monthly income (₹)
- `expenses`: Categorized monthly expenses
- `savings`: Derived surplus
- `debt_pressure`: Loan repayments
- `savings_ratio`: Calculated metric
- `dependents`: Family size

### Behavioral Levels (Frozen)
Three immutable behavioral classifications:
1. **Financially Stressed**: Negative cash flow, excessive debt, zero emergency reserves
2. **Balanced Planner**: Stable cash flow, insufficient long-term strategy
3. **Investment Ready**: Optimized savings ratio, capital available for deployment

### System Output (Structured JSON)
```json
{
  "segment": "Financially Stressed | Balanced Planner | Investment Ready",
  "risk_level": "low | medium | high",
  "suggested_monthly_investment": float,
  "investment_appetite": "Very Low | Low | Medium | High | Very High",
  "reason_codes": string[],
  "confidence": 0.0-1.0,
  "financial_summary": { ... },
  "safe_action": string,
  "warnings": string[],
  "gemini_explanation": string
}
```

## 2. Data Flow Contract

**Rigid unidirectional flow (NO DEVIATION):**

```
User Request → Frontend UI → FastAPI Validation → ML Inference → 
Policy Guardrails → Gemini Explanation → Final Response
```

**CRITICAL:** Frontend NEVER queries ML or Gemini directly. All intelligence flows through the backend.

## 3. Architecture Principles

### Separation of Concerns
```
app-core/
├── config/          # Configuration variables only
├── routes/          # API endpoint definitions
├── models/          # Pydantic schemas, ML pipeline
├── services/        # Business logic orchestration
├── utils/           # Feature engineering, diagnostics
└── main.py          # Application entry point
```

### Model Loading
- ML artifacts loaded ONCE at startup
- No per-request model reloading
- Feature engineering MUST match training pipeline exactly

### Train-Serve Parity
- Same imputer, scaler, feature order
- Identical preprocessing logic
- No divergence between training and inference

## 4. API Surface (Minimalist)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/analyze-user` | POST | Primary recommendation flow |
| `/api/v1/chat` | POST | Conversational follow-up (profile-locked) |
| `/api/v1/health` | GET | Deployment readiness |
| `/api/v1/model-info` | GET | Model metadata, versioning |

## 5. Input Validation Rules

- **Pydantic schemas** for all payloads
- **Immediate rejection** of invalid data (422)
- **No silent inference** by LLM
- **Negative income** → HTTP 422
- **Missing parameters** → HTTP 422

## 6. ML Integration Protocol

### Artifact Package (Versioned)
1. Imputer (missing value handling)
2. Scaler (normalization)
3. Clustering model (K-Means)
4. Segment map (cluster → label)
5. Feature order file
6. Cluster profile summary
7. Model metadata JSON

### Inference Sequence (Rigid)
1. Accept validated user data
2. Compute engineered features
3. Apply saved imputer
4. Apply saved scaler
5. Predict cluster
6. Map to business segment
7. Apply policy guardrails
8. Return structured result

## 7. Gemini Layer Protocol

### System Prompt Constraints
- Persona: Conservative educational guide
- Domain: Financial education ONLY
- Forbidden: Stock tips, guaranteed returns, aggressive growth
- Required: Simple language, safety emphasis, short paragraphs

### Prompt Packet Structure
Backend constructs prompt with:
- User financial summary
- ML-derived segment
- Suggested investment amount
- Guardrail warnings
- Response type instruction

### Temperature Settings
- `temperature`: 0.2 (low variance)
- `top_p`: 0.7 (focused)
- `max_tokens`: 1024 (concise)

## 8. Policy Guardrails (Final Defense)

### Forced Behaviors
- Zero savings → Emergency fund recommendation
- Severe overspending → Dampened advice
- Stock tip requests → Refusal + strategy redirect
- Low confidence → Caution banner

### Fallback Protocol
If Gemini fails:
- Return ML structured recommendation
- Use hardcoded explanation templates
- NEVER crash or fail silently

## 9. Deployment Architecture

### Separation
- **Backend**: Railway (FastAPI + ML artifacts)
- **Frontend**: Vercel (React/Next.js edge)
- **Communication**: HTTPS REST API only

### Security
- Backend owns all API keys
- Frontend never accesses intelligence layer
- No direct Gemini calls from client

## 10. Observability Requirements

### Logging
- Request logs (all inputs)
- Prediction logs (cluster, segment)
- Timing metrics
- Error logs (validation, Gemini failures)
- Input validation failures
- API communication failures

### Test Coverage
- Normal financial profiles
- Severe overspending edge cases
- Zero-savings profiles
- Malformed/incomplete payloads
- Gemini outage simulation

## 11. Regulatory Compliance

### SEBI 2025/2026 Requirements
- AI usage disclosure
- Developer liability acknowledgment
- No registered advisory claims
- Educational positioning only

### Defense Mechanisms
1. **Immutability**: Transparent, auditable algorithm
2. **Audit Trails**: Complete traceability
3. **Domain Confinement**: No securities discussion
4. **Structured Output**: No free-form financial advice

## 12. Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2026-05-02 | Financial intelligence engine, goal-based allocation |
| 1.0.0 | 2026-04-15 | Initial ML clustering implementation |
