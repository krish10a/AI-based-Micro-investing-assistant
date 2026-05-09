"""API routes for authentication and onboarding."""

import logging
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from services.recommendation_service import RecommendationService

logger = logging.getLogger(__name__)

router = APIRouter()
recommendation_service = RecommendationService()

# Optional RAG integration - imported lazily to avoid breaking if not configured
try:
    from services.rag.rag_service import RAGService
    from services.rag.config import RAGSettings
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    RAGService = None
    RAGSettings = None


# =============================================================================
# Request/Response Models
# =============================================================================


class LoginRequest(BaseModel):
    """Login request model."""

    email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$", description="User email")
    password: str = Field(..., min_length=6, description="User password")


class LoginResponse(BaseModel):
    """Login response model."""

    success: bool
    access_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int = 3600
    user_id: Optional[str] = None
    message: Optional[str] = None


class BiometricRequest(BaseModel):
    """Biometric authentication request."""

    credential_id: str = Field(..., description="WebAuthn credential ID")
    client_data_json: str = Field(..., description="Client data JSON")
    authenticator_data: str = Field(..., description="Authenticator data")
    signature: str = Field(..., description="Signature from authenticator")


class BiometricResponse(BaseModel):
    """Biometric authentication response."""

    success: bool
    access_token: Optional[str] = None
    message: str


class OnboardRequest(BaseModel):
    """Full onboarding request with identity verification and financial profile."""

    # Identity information
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    phone: str = Field(..., min_length=10, max_length=15)
    date_of_birth: str = Field(..., description="DOB in YYYY-MM-DD format")
    address: Optional[str] = Field(None, max_length=200)

    # Identity verification (mock)
    kyc_verified: bool = Field(default=False, description="Whether KYC is verified")
    kyc_document_type: Optional[str] = Field(None, description="Aadhaar/PAN/Passport")
    kyc_document_number: Optional[str] = Field(None, max_length=50)

    # Financial profile
    income: float = Field(..., gt=0)
    rent: float = Field(default=0, ge=0)
    loan_repayment: float = Field(default=0, ge=0)
    insurance: float = Field(default=0, ge=0)
    groceries: float = Field(default=0, ge=0)
    transport: float = Field(default=0, ge=0)
    eating_out: float = Field(default=0, ge=0)
    entertainment: float = Field(default=0, ge=0)
    utilities: float = Field(default=0, ge=0)
    healthcare: float = Field(default=0, ge=0)
    education: float = Field(default=0, ge=0)
    miscellaneous: float = Field(default=0, ge=0)
    dependents: int = Field(default=1, ge=0)
    emergency_fund_corpus: float = Field(default=0, ge=0)
    goals: list[str] = Field(default=[])

    # Risk tolerance
    risk_tolerance: str = Field(
        default="moderate",
        description="low, moderate, high",
    )
    investment_experience: str = Field(
        default="beginner", description="beginner, intermediate, experienced"
    )


class OnboardResponse(BaseModel):
    """Onboarding response with ML analysis and user profile."""

    success: bool
    user_id: str
    email: str
    segment: str
    risk_level: Dict[str, Any]
    suggested_monthly_investment: float
    investment_appetite: str
    recommended_plan: str
    confidence: float
    kyc_status: str
    message: str


class VerifyIdentityRequest(BaseModel):
    """Identity verification request."""

    document_type: str = Field(..., description="Aadhaar/PAN/Passport")
    document_number: str = Field(..., max_length=50)
    phone: str = Field(..., min_length=10)
    dob: str = Field(..., description="Date of birth YYYY-MM-DD")


class VerifyIdentityResponse(BaseModel):
    """Identity verification response."""

    success: bool
    verification_token: Optional[str] = None
    message: str
    verified_at: Optional[str] = None


# =============================================================================
# Mock Authentication Storage
# =============================================================================

# In-memory storage for demo (replace with database in production)
users_db: Dict[str, Dict[str, Any]] = {}
user_counter = 0


def _generate_access_token(user_id: str) -> str:
    """Generate a mock JWT-like access token."""
    payload = f"{user_id}:{datetime.utcnow().isoformat()}:{secrets.token_hex(16)}"
    return secrets.token_urlsafe(32)


# =============================================================================
# Auth Routes
# =============================================================================


@router.post("/auth/login", response_model=LoginResponse)
async def login(login_data: LoginRequest):
    """
    Authenticate user with email and password.

    Returns a JWT-like access token valid for 1 hour.
    """
    try:
        # Mock authentication - in production, verify against hashed password
        user = users_db.get(login_data.email)

        if not user:
            # Auto-create user for demo purposes
            user_id = f"user_{secrets.token_hex(8)}"
            user = {
                "user_id": user_id,
                "email": login_data.email,
                "created_at": datetime.utcnow().isoformat(),
            }
            users_db[login_data.email] = user

        # For demo, accept any password with 6+ chars
        access_token = _generate_access_token(user["user_id"])

        logger.info(f"User logged in: {login_data.email}")

        return LoginResponse(
            success=True,
            access_token=access_token,
            token_type="bearer",
            expires_in=3600,
            user_id=user["user_id"],
        )
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed",
        )


@router.post("/auth/biometric", response_model=BiometricResponse)
async def biometric_auth(request: BiometricRequest):
    """
    Authenticate user with biometric credentials (WebAuthn).

    This is a mock endpoint simulating biometric authentication.
    In production, integrate with a WebAuthn library like python-webauthn.
    """
    try:
        # Mock biometric verification
        # In production: verify signature with stored public key

        if not request.credential_id or not request.signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid credential data",
            )

        # Generate mock user ID from credential
        user_id = f"user_{request.credential_id[:16]}"

        access_token = _generate_access_token(user_id)

        logger.info(f"Biometric auth successful for user: {user_id}")

        return BiometricResponse(
            success=True,
            access_token=access_token,
            message="Biometric authentication successful",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Biometric auth failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Biometric authentication failed",
        )


@router.post("/auth/verify-identity", response_model=VerifyIdentityResponse)
async def verify_identity(request: VerifyIdentityRequest):
    """
    Verify user identity with government-issued document.

    This is a mock KYC endpoint. In production, integrate with a KYC provider
    like Signzy, Perfios, or Digio for Aadhaar/PAN verification.
    """
    try:
        # Mock verification - in production, call KYC provider API

        if not request.document_number or len(request.document_number) < 5:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid document number",
            )

        # Generate verification token
        verification_token = f"verify_{secrets.token_hex(16)}"

        logger.info(f"Identity verified for: {request.document_type} ending in {request.document_number[-4:]}")

        return VerifyIdentityResponse(
            success=True,
            verification_token=verification_token,
            message="Identity verified successfully",
            verified_at=datetime.utcnow().isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Identity verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Identity verification failed",
        )


@router.post("/users/onboard", response_model=OnboardResponse)
async def onboard_user(request: OnboardRequest):
    """
    Complete onboarding with identity verification and financial analysis.

    This endpoint:
    1. Creates user profile
    2. Verifies identity (mock)
    3. Runs ML clustering analysis
    4. Returns investment recommendation
    5. Ingests analysis into Pinecone for RAG (if configured)
    """
    try:
        global user_counter
        user_counter += 1

        # Create user ID
        user_id = f"user_{user_counter:08d}"

        # Prepare financial input for analysis
        financial_input = {
            "income": request.income,
            "rent": request.rent,
            "loan_repayment": request.loan_repayment,
            "insurance": request.insurance,
            "groceries": request.groceries,
            "transport": request.transport,
            "eating_out": request.eating_out,
            "entertainment": request.entertainment,
            "utilities": request.utilities,
            "healthcare": request.healthcare,
            "education": request.education,
            "miscellaneous": request.miscellaneous,
            "dependents": request.dependents,
            "emergency_fund_corpus": request.emergency_fund_corpus,
            "goals": request.goals,
        }

        # Run ML analysis
        analysis_result = recommendation_service.analyze_user(financial_input, skip_gemini=True)

        # Store user
        user_data = {
            "user_id": user_id,
            "email": request.email,
            "first_name": request.first_name,
            "last_name": request.last_name,
            "phone": request.phone,
            "date_of_birth": request.date_of_birth,
            "kyc_verified": request.kyc_verified,
            "created_at": datetime.utcnow().isoformat(),
            "financial_profile": financial_input,
            "segment": analysis_result.get("segment"),
            "risk_tolerance": request.risk_tolerance,
        }
        users_db[request.email] = user_data

        # Ingest user analysis into Pinecone for RAG (if available)
        # Format user analysis as readable text for RAG
        total_expenses = (request.rent + request.loan_repayment + request.insurance +
                         request.groceries + request.transport + request.eating_out +
                         request.entertainment + request.utilities + request.healthcare +
                         request.education + request.miscellaneous)
        surplus = request.income - total_expenses

        insights_text = "\n".join([f"- {insight.get('title', 'Insight')}: {insight.get('content', '')}"
                                  for insight in analysis_result.get('insights', [])])
        alerts_text = "\n".join([f"- {alert.get('title', 'Alert')}: {alert.get('content', '')}"
                                for alert in analysis_result.get('alerts', [])])

        analysis_text = f"""USER FINANCIAL PROFILE AND ANALYSIS REPORT
==========================================

User ID: {user_id}
Name: {request.first_name} {request.last_name}
Email: {request.email}
Segment: {analysis_result.get('segment', 'Unknown')}
Risk Tolerance: {request.risk_tolerance}
Risk Level: {analysis_result.get('risk_level', {}).get('label', 'Unknown')}

FINANCIAL SNAPSHOT:
- Monthly Income: Rs.{request.income:,.0f}
- Monthly Expenses: Rs.{total_expenses:,.0f}
- Monthly Surplus: Rs.{surplus:,.0f}
- Dependents: {request.dependents}

INVESTMENT RECOMMENDATIONS:
- Suggested Monthly Investment: Rs.{analysis_result.get('suggested_monthly_investment', 0):,.0f}
- Investment Appetite: {analysis_result.get('investment_appetite', 'Unknown')}
- Recommended Plan: {analysis_result.get('recommended_plan', 'No plan')}
- Confidence Score: {analysis_result.get('confidence', 0)*100:.0f}%

KEY INSIGHTS:
{insights_text}

ALERTS:
{alerts_text}
"""

        # Create RAG service and ingest document
        if RAG_AVAILABLE:
            try:
                rag_settings = RAGSettings.from_env()
                if rag_settings.pinecone_api_key and rag_settings.pinecone_index_name:
                    rag_service = RAGService(settings=rag_settings)
                    await rag_service.ingest_document(analysis_text, source=f"user_{user_id}")
                    logger.info(f"[{user_id}] Analysis ingested into Pinecone")
            except Exception as rag_error:
                logger.warning(f"[{user_id}] RAG ingestion failed: {rag_error}")
                # Don't fail onboarding if RAG fails

        logger.info(f"User onboarded: {request.email}, Segment: {analysis_result.get('segment')}")

        return OnboardResponse(
            success=True,
            user_id=user_id,
            email=request.email,
            segment=analysis_result.get("segment", "Unknown"),
            risk_level=analysis_result.get("risk_level", {"label": "Unknown", "color": "gray"}),
            suggested_monthly_investment=analysis_result.get("suggested_monthly_investment", 0),
            investment_appetite=analysis_result.get("investment_appetite", "Unknown"),
            recommended_plan=analysis_result.get("recommended_plan", "No plan"),
            confidence=analysis_result.get("confidence", 0),
            kyc_status="verified" if request.kyc_verified else "pending",
            message="Onboarding completed successfully",
        )
    except Exception as e:
        logger.error(f"Onboarding failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Onboarding failed. Please try again.",
        )


@router.get("/auth/me")
async def get_current_user(access_token: str):
    """
    Get current user profile from access token.

    In production, decode JWT and fetch user from database.
    """
    try:
        # Mock: extract user_id from token
        if not access_token or not access_token.startswith("user_"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        user_id = access_token.split(":")[0] if ":" in access_token else access_token

        # Find user by ID (simplified for demo)
        for email, user in users_db.items():
            if user.get("user_id") == user_id:
                return {
                    "user_id": user["user_id"],
                    "email": user["email"],
                    "first_name": user.get("first_name"),
                    "last_name": user.get("last_name"),
                    "kyc_verified": user.get("kyc_verified", False),
                    "segment": user.get("segment"),
                }

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current user failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not fetch user profile",
        )


@router.post("/auth/logout")
async def logout():
    """
    Logout user and invalidate session.

    In production, this would invalidate the JWT token in a token store.
    For demo purposes, it just returns success.
    """
    try:
        logger.info("User logged out")
        return {"success": True, "message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )
