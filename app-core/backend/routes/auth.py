"""Authentication routes for user registration and login."""

import logging
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Any

from database import get_db
from auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    get_current_active_user
)
from models.db_models import User
from models.schemas import FinancialOnlyOnboardRequest
from config.settings import settings
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


class UserRegister(BaseModel):
    """Request model for user registration."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password (min 8 characters)")
    full_name: str = Field(..., min_length=1, max_length=100, description="User full name")


class UserLogin(BaseModel):
    """Request model for user login."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class TokenResponse(BaseModel):
    """Response model for authentication token."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class UserResponse(BaseModel):
    """Response model for user data."""
    id: str
    email: str
    full_name: str | None
    is_active: bool
    created_at: str


class LoginRequest(BaseModel):
    """Login request model."""
    email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$", description="User email")
    password: str = Field(..., min_length=1, description="User password")


class LoginResponse(BaseModel):
    """Login response model."""
    success: bool
    access_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int = 3600
    user_id: Optional[str] = None
    message: Optional[str] = None
    user: Optional[dict] = None


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
    income: float = Field(..., ge=0)
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




def _generate_access_token(user_id: str) -> str:
    """Generate a mock JWT-like access token."""
    payload = f"{user_id}:{datetime.utcnow().isoformat()}:{secrets.token_hex(16)}"
    return secrets.token_urlsafe(32)


# =============================================================================
# Auth Routes
# =============================================================================


@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user.

    Args:
        email: User email address
        password: User password (min 8 characters)
        full_name: User full name

    Returns:
        Created user data
    """
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Create new user
        import uuid
        user = User(
            id=str(uuid.uuid4()),
            email=user_data.email,
            hashed_password=get_password_hash(user_data.password),
            full_name=user_data.full_name,
            is_active=True
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        logger.info(f"User registered: {user.email}")

        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


@router.post("/auth/login", response_model=LoginResponse)
async def login(login_data: LoginRequest):
    """
    Authenticate user with email and password.

    For demo purposes, auto-registers new users if they don't exist.

    Returns a JWT-like access token valid for 1 hour.
    """
    try:
        # Get database session
        from database import get_db
        from sqlalchemy.orm import Session

        db_gen = get_db()
        db: Session = next(db_gen)

        user = db.query(User).filter(User.email == login_data.email).first()

        # Auto-register new users for demo convenience
        if not user:
            import uuid
            logger.info(f"Auto-registering new user: {login_data.email}")
            user = User(
                id=str(uuid.uuid4()),
                email=login_data.email,
                hashed_password=get_password_hash(login_data.password),
                full_name=login_data.email.split("@")[0],  # Use email username as full name
                is_active=True,
                is_onboarded=False
            )
            db.add(user)
            db.commit()

        if not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )

        # Create access token
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user.id, "email": user.email},
            expires_delta=access_token_expires
        )

        logger.info(f"User logged in: {login_data.email}")

        return LoginResponse(
            success=True,
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            user_id=user.id,
            user={
                "id": user.id,
                "email": user.email,
                "first_name": user.full_name.split(" ")[0] if user.full_name else "",
                "last_name": " ".join(user.full_name.split(" ")[1:]) if user.full_name and len(user.full_name.split(" ")) > 1 else "",
                "is_onboarded": user.is_onboarded
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed",
        )


@router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    Get current user information.

    Returns:
        Current user data
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat()
    }




@router.post("/auth/guest", response_model=LoginResponse)
async def guest_login():
    """
    Create a guest user session.

    For demo purposes - creates a temporary user that can complete onboarding.
    """
    try:
        from database import get_db
        from sqlalchemy.orm import Session
        import uuid

        db_gen = get_db()
        db: Session = next(db_gen)

        # Generate unique guest user
        guest_id = str(uuid.uuid4())
        guest_email = f"guest_{guest_id[:8]}@guest.local"

        # Create guest user
        guest_user = User(
            id=guest_id,
            email=guest_email,
            hashed_password=get_password_hash("guest"),
            full_name="Guest User",
            is_active=True,
            is_onboarded=False
        )
        db.add(guest_user)
        db.commit()

        # Create access token
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": guest_user.id, "email": guest_user.email},
            expires_delta=access_token_expires
        )

        logger.info(f"Guest user created: {guest_email}")

        return LoginResponse(
            success=True,
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            user_id=guest_user.id,
            user={
                "id": guest_user.id,
                "email": guest_email,
                "first_name": "Guest",
                "last_name": "User",
                "is_onboarded": False
            }
        )
    except Exception as e:
        logger.error(f"Guest login failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Guest login failed",
        )


@router.post("/auth/logout")
async def logout():
    """
    Logout current user.

    Note: This is a no-op on the server. The client should remove the token.
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


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(current_user: User = Depends(get_current_active_user)):
    """
    Refresh access token.

    Returns:
        New access token
    """
    try:
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": current_user.id, "email": current_user.email},
            expires_delta=access_token_expires
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "full_name": current_user.full_name,
                "is_active": current_user.is_active
            }
        }
    except Exception as e:
        logger.error(f"Token refresh failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed. Please login again."
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
async def onboard_user(
    request: OnboardRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Complete onboarding with identity verification and financial analysis.
    """
    try:
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

        # Calculate total expenses
        total_expenses = (request.rent + request.loan_repayment + request.insurance +
                         request.groceries + request.transport + request.eating_out +
                         request.entertainment + request.utilities + request.healthcare +
                         request.education + request.miscellaneous)
        surplus = request.income - total_expenses

        # Persist Financial Profile to Database
        from models.db_models import FinancialProfile
        import json
        import uuid

        # Check if profile exists, otherwise create
        financial_profile = db.query(FinancialProfile).filter(FinancialProfile.user_id == current_user.id).first()
        
        if not financial_profile:
            financial_profile = FinancialProfile(
                id=str(uuid.uuid4()),
                user_id=current_user.id
            )
            db.add(financial_profile)

        financial_profile.monthly_income = request.income
        financial_profile.monthly_expenses = total_expenses
        financial_profile.savings_rate = surplus / request.income if request.income > 0 else 0
        financial_profile.user_segment = analysis_result.get("segment")
        financial_profile.risk_tolerance = request.risk_tolerance
        financial_profile.investment_experience = request.investment_experience
        financial_profile.raw_data = json.dumps(financial_input)

        # Update user onboarding status
        current_user.is_onboarded = True
        current_user.full_name = f"{request.first_name} {request.last_name}"

        db.commit()

        # Format user analysis for RAG ingestion
        insights_text = "\n".join([f"- {insight.get('title', 'Insight')}: {insight.get('content', '')}"
                                  for insight in analysis_result.get('insights', [])])
        alerts_text = "\n".join([f"- {alert.get('title', 'Alert')}: {alert.get('content', '')}"
                                for alert in analysis_result.get('alerts', [])])

        analysis_text = f"""USER FINANCIAL PROFILE AND ANALYSIS REPORT
==========================================

User ID: {current_user.id}
Name: {current_user.full_name}
Email: {current_user.email}
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

        # RAG ingestion logic
        if RAG_AVAILABLE:
            try:
                rag_settings = RAGSettings.from_env()
                if rag_settings.pinecone_api_key and rag_settings.pinecone_index_name:
                    rag_service = RAGService(settings=rag_settings)
                    await rag_service.ingest_document(analysis_text, source=f"user_{current_user.id}")
                    logger.info(f"[{current_user.id}] Analysis ingested into Pinecone")
            except Exception as rag_error:
                logger.warning(f"[{current_user.id}] RAG ingestion failed: {rag_error}")

        logger.info(f"User onboarded: {current_user.email}, Segment: {analysis_result.get('segment')}")

        return OnboardResponse(
            success=True,
            user_id=current_user.id,
            email=current_user.email,
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


@router.post("/users/onboard-financial", response_model=OnboardResponse)
async def onboard_user_financial(
    request: FinancialOnlyOnboardRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Complete financial-only onboarding without personal information requirements.
    """
    try:
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

        # Calculate total expenses
        total_expenses = (request.rent + request.loan_repayment + request.insurance +
                         request.groceries + request.transport + request.eating_out +
                         request.entertainment + request.utilities + request.healthcare +
                         request.education + request.miscellaneous)
        surplus = request.income - total_expenses

        # Persist Financial Profile to Database
        from models.db_models import FinancialProfile
        import json
        import uuid

        # Check if profile exists, otherwise create
        financial_profile = db.query(FinancialProfile).filter(FinancialProfile.user_id == current_user.id).first()

        if not financial_profile:
            financial_profile = FinancialProfile(
                id=str(uuid.uuid4()),
                user_id=current_user.id
            )
            db.add(financial_profile)

        financial_profile.monthly_income = request.income
        financial_profile.monthly_expenses = total_expenses
        financial_profile.savings_rate = surplus / request.income if request.income > 0 else 0
        financial_profile.user_segment = analysis_result.get("segment")
        financial_profile.risk_tolerance = "moderate"  # Default value
        financial_profile.investment_experience = "beginner"  # Default value
        financial_profile.raw_data = json.dumps(financial_input)

        # Update user onboarding status
        current_user.is_onboarded = True

        db.commit()

        logger.info(f"User financial-only onboarded: {current_user.email}, Segment: {analysis_result.get('segment')}")

        return OnboardResponse(
            success=True,
            user_id=current_user.id,
            email=current_user.email,
            segment=analysis_result.get("segment", "Unknown"),
            risk_level=analysis_result.get("risk_level", {"label": "Unknown", "color": "gray"}),
            suggested_monthly_investment=analysis_result.get("suggested_monthly_investment", 0),
            investment_appetite=analysis_result.get("investment_appetite", "Unknown"),
            recommended_plan=analysis_result.get("recommended_plan", "No plan"),
            confidence=analysis_result.get("confidence", 0),
            kyc_status="verified",
            message="Financial-only onboarding completed successfully",
        )
    except Exception as e:
        logger.error(f"Financial-only onboarding failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Financial-only onboarding failed. Please try again.",
        )


@router.get("/users/analysis")
async def get_user_analysis(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve the persistent financial analysis for the current user.
    """
    try:
        from models.db_models import FinancialProfile
        import json

        financial_profile = db.query(FinancialProfile).filter(FinancialProfile.user_id == current_user.id).first()

        if not financial_profile or not financial_profile.raw_data:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"success": False, "message": "Financial profile not found. Please complete onboarding."}
            )

        # Parse the raw data
        financial_input = json.loads(financial_profile.raw_data)

        # Run analysis
        analysis_result = recommendation_service.analyze_user(financial_input, skip_gemini=True)

        return analysis_result

    except Exception as e:
        logger.error(f"Failed to fetch user analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve analysis data."
        )
