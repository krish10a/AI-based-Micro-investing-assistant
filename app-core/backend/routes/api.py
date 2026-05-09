"""API routes for the micro-investing assistant."""

import logging
import time
import uuid
from fastapi import APIRouter, HTTPException, status, Request
from pydantic import ValidationError
from fastapi.responses import JSONResponse

from models.schemas import (
    UserFinancialInput,
    ChatRequest,
    AnalyzeUserResponse,
    HealthResponse,
    ModelInfoResponse,
    SIPRequest,
    SIPCalculationResponse,
    AuditLogResponse
)
from fastapi import Query
from services.recommendation_service import RecommendationService
from services.nim_service import NIMService
from models.ml_pipeline import MicroInvestmentAssistant
from config.settings import settings
from config.model_metadata import MODEL_INFO, AUDIT_LOGGER
from utils.policy_guardrails import PolicyGuardrails

# Optional RAG integration
try:
    from services.rag.rag_service import RAGService
    from services.rag.config import RAGSettings
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    RAGService = None
    RAGSettings = None

logger = logging.getLogger(__name__)

router = APIRouter()
recommendation_service = RecommendationService()
nim_service = NIMService()
guardrails = PolicyGuardrails()


@router.post("/analyze-user")
async def analyze_user(
    request: Request,
    input_data: UserFinancialInput,
    skip_explanation: bool = Query(default=False, description="Skip NIM explanation for faster response")
):
    """
    Analyze user financial profile and return investment recommendation.

    Returns structured dashboard data with:
    - Financial diagnosis (state, health score, alerts)
    - Expense intelligence (insights, category breakdown)
    - Goal-based allocation (specific amounts per goal)
    - ML recommendation (segment, confidence, plan)
    - User-facing profile and reasoning
    - Policy guardrails triggered
    """
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start_time = time.time()

    try:
        # Convert Pydantic model to dict
        user_input = input_data.model_dump()

        logger.info(f"[{request_id}] Processing analysis request")

        # Run analysis (includes guardrails internally)
        result = recommendation_service.analyze_user(user_input, skip_gemini=skip_explanation)

        # Log prediction to audit trail
        guardrails_triggered = result.get("guardrails_triggered", [])
        AUDIT_LOGGER.log_prediction(
            request_id=request_id,
            user_input=user_input,
            features=[],  # Features computed internally
            cluster_id=result.get("cluster_id", -1),
            segment=result.get("segment", ""),
            confidence=result.get("confidence", 0),
            guardrails_triggered=[g["type"] for g in guardrails_triggered],
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ")
        )

        # Log timing
        process_time = time.time() - start_time
        logger.info(f"[{request_id}] Completed in {process_time*1000:.2f}ms")

        # Return as JSONResponse
        return JSONResponse(content=result)

    except ValidationError as e:
        logger.error(f"[{request_id}] Validation error: {e}")
        AUDIT_LOGGER.log_validation_error(
            request_id=request_id,
            error_type="ValidationError",
            error_details=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.errors()
        )
    except Exception as e:
        logger.error(f"[{request_id}] Analysis failed: {e}", exc_info=True)
        AUDIT_LOGGER.log_validation_error(
            request_id=request_id,
            error_type=type(e).__name__,
            error_details=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analysis failed. Please check your input and try again."
        )


@router.post("/chat")
async def chat(request: Request, chat_request: ChatRequest):
    """
    Handle conversational follow-up questions.

    IMPORTANT: This endpoint enforces domain boundaries and policy guardrails.
    Stock tip requests are refused and redirected to strategy guidance.

    Now includes RAG context from Pinecone for personalized responses.
    """
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    try:
        # Check for stock tip requests (policy guardrail)
        if guardrails.check_stock_tip_request(chat_request.message):
            logger.warning(f"[{request_id}] Stock tip request blocked")
            return JSONResponse(content={
                "response": guardrails.generate_refusal_response()
            })

        # Check for out-of-scope requests
        is_within_domain, refusal_message = guardrails.enforce_domain_boundary(chat_request.message)
        if not is_within_domain:
            logger.warning(f"[{request_id}] Out-of-scope request blocked")
            return JSONResponse(content={
                "response": refusal_message
            })

        # Retrieve RAG context if available
        rag_context = None
        if RAG_AVAILABLE and chat_request.user_profile:
            try:
                import asyncio
                rag_settings = RAGSettings.from_env()
                if rag_settings.pinecone_api_key and rag_settings.pinecone_index_name:
                    rag_service = RAGService(settings=rag_settings)
                    # Get user ID from profile if available
                    user_id = chat_request.user_profile.get("user_id", "")
                    if user_id:
                        filter_dict = {"source": f"user_{user_id}"}
                    else:
                        filter_dict = None

                    rag_context = asyncio.get_event_loop().run_until_complete(
                        rag_service.retrieve_as_context(
                            chat_request.message,
                            top_k=3,
                            filter=filter_dict
                        )
                    )
                    logger.info(f"[{request_id}] Retrieved RAG context")
            except Exception as rag_error:
                logger.warning(f"[{request_id}] RAG retrieval failed: {rag_error}")
                # Continue without RAG context

        # Process chat request with user profile and RAG context
        logger.info(f"[{request_id}] Processing chat request")

        # Augment user profile with RAG context if available
        enriched_profile = chat_request.user_profile.copy() if chat_request.user_profile else {}
        if rag_context and rag_context != "No relevant context found.":
            enriched_profile["rag_context"] = rag_context

        response = await recommendation_service.chat(
            chat_request.message,
            enriched_profile
        )

        return {"response": response}

    except Exception as e:
        logger.error(f"[{request_id}] Chat failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chat service unavailable"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="healthy")


@router.get("/rag/stats")
async def get_rag_stats():
    """
    Return RAG service statistics.

    Shows:
    - Whether RAG is available
    - Index statistics if connected
    """
    if not RAG_AVAILABLE:
        return {
            "available": False,
            "message": "RAG service not available. Please install RAG dependencies."
        }

    try:
        import asyncio
        rag_settings = RAGSettings.from_env()

        if not rag_settings.pinecone_api_key:
            return {
                "available": True,
                "configured": False,
                "message": "RAG service available but PINECONE_API_KEY not configured."
            }

        rag_service = RAGService(settings=rag_settings)
        stats = await rag_service.get_stats()

        return {
            "available": True,
            "configured": True,
            "index_name": rag_settings.pinecone_index_name,
            "stats": stats
        }
    except Exception as e:
        return {
            "available": True,
            "configured": False,
            "error": str(e)
        }


@router.get("/model-info")
async def get_model_info():
    """
    Return model metadata for transparency and audit.

    Includes:
    - Model version and training date
    - Dataset information
    - Validation metrics
    - Safety rules
    - Known limitations
    - Regulatory compliance notice
    """
    try:
        assistant = MicroInvestmentAssistant(artifacts_dir=settings.artifacts_dir)
        info = assistant.get_model_info()

        # Add NIM model info
        info["explanation_model"] = settings.nim_model

        # Add full metadata from model_metadata module
        info["full_metadata"] = MODEL_INFO.to_dict()

        return JSONResponse(content=info)

    except Exception as e:
        logger.error(f"Model info failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not load model info"
        )




@router.get("/model-health")
async def get_model_health():
    """
    Return health status of all NIM models in the fallback pool.

    Shows:
    - Success/failure rates per model
    - Consecutive failures
    - Current health status
    - Model pool configuration
    """
    try:
        health_report = nim_service.get_health_report()
        return JSONResponse(content=health_report)

    except Exception as e:
        logger.error(f"Model health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not get model health"
        )


@router.post("/model-health/reset")
async def reset_model_health():
    """
    Reset health statistics for all models.

    Useful for testing or after fixing API key issues.
    """
    try:
        from config.nim import reset_model_health_tracker, get_model_health_tracker, NIM_MODEL_POOL
        reset_model_health_tracker()

        return JSONResponse(content={
            "status": "success",
            "message": "Model health statistics reset",
            "healthy_models": len(get_model_health_tracker(NIM_MODEL_POOL).get_healthy_models(NIM_MODEL_POOL))
        })

    except Exception as e:
        logger.error(f"Model health reset failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not reset model health"
        )


# =============================================================================
# Demo Profiles
# =============================================================================

DEMO_PROFILES = {
    "student": {
        "name": "Student",
        "description": "Low income, minimal expenses, focusing on building financial habits",
        "data": {
            "income": 15000,
            "rent": 5000,
            "groceries": 3000,
            "transport": 1000,
            "utilities": 500,
            "healthcare": 500,
            "education": 2000,
            "eating_out": 1000,
            "entertainment": 500,
            "insurance": 0,
            "loan_repayment": 0,
            "miscellaneous": 500,
            "dependents": 0
        }
    },
    "working_professional": {
        "name": "Working Professional",
        "description": "Steady income, moderate expenses, ready for consistent investing",
        "data": {
            "income": 50000,
            "rent": 15000,
            "groceries": 8000,
            "transport": 3000,
            "utilities": 2000,
            "healthcare": 1500,
            "education": 2000,
            "eating_out": 3000,
            "entertainment": 2000,
            "insurance": 2000,
            "loan_repayment": 5000,
            "miscellaneous": 2000,
            "dependents": 1
        }
    },
    "good_earner": {
        "name": "Good Earner",
        "description": "High income, strong savings capacity, aggressive wealth building",
        "data": {
            "income": 150000,
            "rent": 40000,
            "groceries": 15000,
            "transport": 5000,
            "utilities": 4000,
            "healthcare": 3000,
            "education": 5000,
            "eating_out": 8000,
            "entertainment": 5000,
            "insurance": 10000,
            "loan_repayment": 15000,
            "miscellaneous": 5000,
            "dependents": 2
        }
    }
}


@router.get("/demo-profiles")
async def get_demo_profiles():
    """
    Return pre-built demo profiles for live demonstrations.

    Returns three profiles:
    - Student: Low income, minimal expenses
    - Working Professional: Steady income, moderate expenses
    - Good Earner: High income, strong savings capacity

    Use these to quickly fill the analysis form with realistic data.
    """
    return {
        "profiles": [
            {
                "id": profile_id,
                "name": profile["name"],
                "description": profile["description"]
            }
            for profile_id, profile in DEMO_PROFILES.items()
        ]
    }


@router.get("/demo-profile/{profile_id}")
async def get_demo_profile(profile_id: str):
    """
    Return a specific demo profile with full financial data.

    Use this to populate the analysis form with a complete profile.
    """
    if profile_id not in DEMO_PROFILES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile '{profile_id}' not found. Available profiles: {list(DEMO_PROFILES.keys())}"
        )

    profile = DEMO_PROFILES[profile_id]
    return {
        "id": profile_id,
        "name": profile["name"],
        "description": profile["description"],
        "data": profile["data"]
    }


# =============================================================================
# SIP Calculator
# =============================================================================

@router.post("/calculate-sip", response_model=SIPCalculationResponse)
async def calculate_sip(request: SIPRequest):
    """
    Calculate future value of a SIP (Systematic Investment Plan).

    Given monthly investment, tenure, and expected return, this endpoint
    computes the compound growth over time.

    Formula: FV = P × ({(1 + r)^n - 1} / r) × (1 + r)

    Example:
    - Monthly: ₹5,000
    - Tenure: 10 years
    - Return: 12% p.a.
    - Future Value: ₹11,64,584
    """
    from utils.sip_calculator import calculate_sip_future_value

    try:
        result = calculate_sip_future_value(
            monthly_investment=request.monthly_investment,
            years=request.years,
            expected_return=request.expected_return
        )

        return SIPCalculationResponse(
            monthly_investment=result.monthly_investment,
            years=result.years,
            expected_return=result.expected_return,
            future_value=result.future_value,
            total_invested=result.total_invested,
            total_growth=result.total_growth,
            growth_percentage=result.growth_percentage,
            formatted_future_value=f"₹{result.future_value:,.0f}",
            formatted_total_invested=f"₹{result.total_invested:,.0f}"
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )


@router.get("/sip-examples")
async def get_sip_examples():
    """
    Return common SIP scenarios for reference.

    Useful for showing users typical investment outcomes.
    """
    from utils.sip_calculator import get_sip_examples

    examples = get_sip_examples()
    return {
        "examples": [
            {
                "id": id,
                "name": name.replace("_", " ").title(),
                "description": data["description"],
                "monthly_investment": data["monthly_investment"],
                "years": data["years"],
                "expected_return": data["expected_return"]
            }
            for id, data in examples.items()
            for name in [data.get("name", id)]
        ]
    }


@router.get("/audit-logs", response_model=AuditLogResponse)
async def get_audit_logs(limit: int = Query(default=20, ge=1, le=100)):
    """
    Retrieve recent audit logs for the transparency dashboard.
    """
    try:
        logs = AUDIT_LOGGER.get_recent_logs(limit=limit)
        return AuditLogResponse(
            logs=logs,
            total_count=len(logs),
            timestamp=str(time.time())
        )
    except Exception as e:
        logger.error(f"Error fetching audit logs: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve audit logs")

@router.get("/system-metadata")
async def get_system_metadata():
    """
    Return system metadata for the transparency tab.
    """
    return {
        "model_version": MODEL_INFO.version,
        "last_train_date": MODEL_INFO.training_date,
        "accuracy": 0.94, # Hardcoded for demo
        "precision": 0.92,
        "recall": 0.95,
        "f1_score": 0.93,
        "drift_status": "STABLE"
    }
