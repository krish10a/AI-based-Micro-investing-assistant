"""User profile management routes."""

import logging
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from models.schemas import UserProfileResponse, UserProfileUpdate
from models.db_models import User, FinancialProfile
from database import get_db
from auth import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/users/me", response_model=UserProfileResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_active_user)):
    """Get current user profile."""
    financial_profile = current_user.financial_profile
    
    return UserProfileResponse(
        user_id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        phone=current_user.phone,
        date_of_birth=current_user.date_of_birth,
        address=current_user.address,
        kyc_verified=current_user.kyc_verified or False,
        segment=financial_profile.user_segment if financial_profile else None,
        risk_tolerance=financial_profile.risk_tolerance if financial_profile else None,
        created_at=current_user.created_at.isoformat() if current_user.created_at else "",
    )


@router.put("/users/me", response_model=UserProfileResponse)
async def update_current_user_profile(
    update_data: UserProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user profile."""
    update_dict = update_data.model_dump(exclude_unset=True)
    
    # Financial profile fields
    financial_fields = ["risk_tolerance"]
    
    for key, value in update_dict.items():
        if key in financial_fields:
            if current_user.financial_profile:
                setattr(current_user.financial_profile, key, value)
        else:
            if hasattr(current_user, key):
                setattr(current_user, key, value)
    
    db.commit()
    db.refresh(current_user)
    
    financial_profile = current_user.financial_profile
    
    return UserProfileResponse(
        user_id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        phone=current_user.phone,
        date_of_birth=current_user.date_of_birth,
        address=current_user.address,
        kyc_verified=current_user.kyc_verified or False,
        segment=financial_profile.user_segment if financial_profile else None,
        risk_tolerance=financial_profile.risk_tolerance if financial_profile else None,
        created_at=current_user.created_at.isoformat() if current_user.created_at else "",
    )


@router.get("/users/onboarding/status")
async def get_onboarding_status(current_user: User = Depends(get_current_active_user)):
    """Get current user onboarding status."""
    return {"is_onboarded": current_user.is_onboarded}


@router.get("/users/{user_id}", response_model=UserProfileResponse)
async def get_user_profile(user_id: str, db: Session = Depends(get_db)):
    """Get user profile by user ID."""
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID '{user_id}' not found")
        
    financial_profile = user.financial_profile
    
    return UserProfileResponse(
        user_id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        date_of_birth=user.date_of_birth,
        address=user.address,
        kyc_verified=user.kyc_verified or False,
        segment=financial_profile.user_segment if financial_profile else None,
        risk_tolerance=financial_profile.risk_tolerance if financial_profile else None,
        created_at=user.created_at.isoformat() if user.created_at else "",
    )


@router.put("/users/{user_id}", response_model=UserProfileResponse)
async def update_user_profile(user_id: str, update_data: UserProfileUpdate, db: Session = Depends(get_db)):
    """Update user profile by user ID."""
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID '{user_id}' not found")
        
    update_dict = update_data.model_dump(exclude_unset=True)
    
    financial_fields = ["risk_tolerance"]
    
    for key, value in update_dict.items():
        if key in financial_fields:
            if user.financial_profile:
                setattr(user.financial_profile, key, value)
        else:
            if hasattr(user, key):
                setattr(user, key, value)
    
    db.commit()
    db.refresh(user)
    
    financial_profile = user.financial_profile
    
    return UserProfileResponse(
        user_id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        date_of_birth=user.date_of_birth,
        address=user.address,
        kyc_verified=user.kyc_verified or False,
        segment=financial_profile.user_segment if financial_profile else None,
        risk_tolerance=financial_profile.risk_tolerance if financial_profile else None,
        created_at=user.created_at.isoformat() if user.created_at else "",
    )


@router.delete("/users/{user_id}")
async def delete_user_account(user_id: str, db: Session = Depends(get_db)):
    """Delete user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID '{user_id}' not found")
        
    user.is_active = False
    db.commit()
    
    return {
        "message": "Account deleted successfully",
        "user_id": user_id,
        "deleted_at": datetime.utcnow().isoformat(),
        "notice": "Data will be permanently removed after 30 days",
    }
