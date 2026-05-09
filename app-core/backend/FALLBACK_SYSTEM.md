# Multi-Model Fallback System

## Overview
Bulletproof NVIDIA NIM API system with automatic model switching when primary models fail.

## Root Cause Fix (Applied)
The initial 401 errors were caused by:
1. **System message format** - NVIDIA NIM works better with combined user+system messages
2. **Temperature/top_p mismatch** - Changed from (0.2, 0.7) to (0.7, 0.9) to match working config
3. **Max tokens** - Reduced from 1024 to 512 for faster responses

## Model Pool (Priority Order)
1. **meta/llama-3.1-70b-instruct** (Primary)
2. **mistralai/mistral-medium-3.5-128b**
3. **google/gemma-4-31b-it**
4. **qwen/qwen3-next-80b-a3b-instruct**
5. **meta/llama-3.1-405b-instruct**

## How It Works

### Automatic Fallback Flow
```
User Request → Primary Model (Llama 70B)
    ↓ (401/500 error)
Try Model 2 (Mistral 128B)
    ↓ (401/500 error)
Try Model 3 (Gemma 31B)
    ↓ (401/500 error)
Try Model 4 (Qwen 80B)
    ↓ (401/500 error)
Try Model 5 (Llama 405B)
    ↓ (all fail)
Rule-Based Fallback Explanation
```

### Health Tracking
- Each model tracks success/failure rates
- Consecutive failures are counted
- After 5 consecutive failures, model is marked "unhealthy"
- Healthy models are tried first in fallback chain

### API Endpoints

#### POST `/api/v1/analyze-user`
Now uses multi-model fallback automatically. No code changes needed.

#### GET `/api/v1/model-health`
Returns health status of all models:
```json
{
  "models": {
    "meta/llama-3.1-70b-instruct": {
      "success_rate": 0.85,
      "success_count": 100,
      "failure_count": 15,
      "consecutive_failures": 0,
      "is_healthy": true
    }
  },
  "pool": [...],
  "primary_model": "meta/llama-3.1-70b-instruct"
}
```

## Files Modified/Created

### New Files
- `config/nim.py` - Model pool configuration and health tracker
- `services/nim_fallback_service.py` - Core fallback logic

### Modified Files
- `services/nim_service.py` - Now wraps fallback service
- `routes/api.py` - Added `/model-health` endpoint

## Configuration

### Adding New Models
Edit `config/nim.py`:
```python
NIM_MODEL_POOL: List[NIMModelConfig] = [
    NIMModelConfig(
        model_id="your-model-id",
        name="Display Name",
        priority=6  # Lower = higher priority
    ),
]
```

### Adjusting Retry Behavior
Edit `services/nim_fallback_service.py`:
```python
self.max_total_retries = 5  # Max models to try
```

## Benefits
1. **Zero Downtime**: If one model's API key fails, auto-switches to next
2. **Health Monitoring**: Track which models are working
3. **Graceful Degradation**: Falls back to rule-based explanations if all APIs fail
4. **No Code Changes**: Drop-in replacement for existing NIMService

## Testing
```bash
# Check model health
curl http://localhost:8001/api/v1/model-health

# Test fallback with analysis
curl -X POST http://localhost:8001/api/v1/analyze-user \
  -H "Content-Type: application/json" \
  -d '{"income":50000, ...}'
```
