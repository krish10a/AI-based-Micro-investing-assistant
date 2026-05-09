"""User profile management routes."""

import logging
from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import JSONResponse
from typing import Any, Dict

from models.schemas import UserProfileResponse, UserProfileUpdate
from routes.auth import users_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/users/me")
async def get_current_user_profile(request: Request):
    """Get current user profile."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid token")
    
    token = auth_header.split(" ")[1]
    user_id = token.split(":")[0] if ":" in token else token
    
    user = None
    for email, data in users_db.items():
        if data.get("user_id") == user_id:
            user = data
            break
            
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
    return UserProfileResponse(
        user_id=user["user_id"],
        email=user["email"],
        first_name=user.get("first_name"),
        last_name=user.get("last_name"),
        phone=user.get("phone"),
        date_of_birth=user.get("date_of_birth"),
        address=user.get("address"),
        kyc_verified=user.get("kyc_verified", False),
        segment=user.get("segment"),
        risk_tolerance=user.get("risk_tolerance"),
        created_at=user.get("created_at"),
    )


@router.put("/users/me")
async def update_current_user_profile(request: Request, update_data: UserProfileUpdate):
    """Update current user profile."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid token")
        
    token = auth_header.split(" ")[1]
    user_id = token.split(":")[0] if ":" in token else token
    
    user_email = None
    for email, data in users_db.items():
        if data.get("user_id") == user_id:
            user_email = email
            break
            
    if not user_email:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        if value is not None:
            users_db[user_email][key] = value

    from datetime import datetime
    users_db[user_email]["updated_at"] = datetime.utcnow().isoformat()
    
    user = users_db[user_email]
    
    return UserProfileResponse(
        user_id=user["user_id"],
        email=user["email"],
        first_name=user.get("first_name"),
        last_name=user.get("last_name"),
        phone=user.get("phone"),
        date_of_birth=user.get("date_of_birth"),
        address=user.get("address"),
        kyc_verified=user.get("kyc_verified", False),
        segment=user.get("segment"),
        risk_tolerance=user.get("risk_tolerance"),
        created_at=user.get("created_at"),
    )


@router.get("/users/onboarding/status")
async def get_onboarding_status(request: Request):
    """Get current user onboarding status."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid token")
        
    token = auth_header.split(" ")[1]
    user_id = token.split(":")[0] if ":" in token else token
    
    user = None
    for email, data in users_db.items():
        if data.get("user_id") == user_id:
            user = data
            break
            
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
    is_onboarded = "financial_profile" in user
    return {"is_onboarded": is_onboarded}


@router.get("/users/{user_id}")
async def get_user_profile(user_id: str):
    """
    Get user profile by user ID.

    Returns user profile information including KYC status, segment, and risk tolerance.
    """
    try:
        # Find user by user_id
        user = None
        for email, data in users_db.items():
            if data.get("user_id") == user_id:
                user = data
                break

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID '{user_id}' not found",
            )

        return UserProfileResponse(
            user_id=user["user_id"],
            email=user["email"],
            first_name=user.get("first_name"),
            last_name=user.get("last_name"),
            phone=user.get("phone"),
            date_of_birth=user.get("date_of_birth"),
            address=user.get("address"),
            kyc_verified=user.get("kyc_verified", False),
            segment=user.get("segment"),
            risk_tolerance=user.get("risk_tolerance"),
            created_at=user.get("created_at"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve user profile",
        )


@router.put("/users/{user_id}")
async def update_user_profile(user_id: str, update_data: UserProfileUpdate):
    """
    Update user profile.

    Args:
        user_id: User ID to update
        update_data: Fields to update (first_name, last_name, phone, address, risk_tolerance)

    Returns:
        Updated user profile
    """
    try:
        # Find user by user_id
        user_email = None
        for email, data in users_db.items():
            if data.get("user_id") == user_id:
                user_email = email
                break

        if not user_email:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID '{user_id}' not found",
            )

        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            if value is not None:
                users_db[user_email][key] = value

        # Update timestamp
        from datetime import datetime
        users_db[user_email]["updated_at"] = datetime.utcnow().isoformat()

        user = users_db[user_email]

        logger.info(f"Updated profile for user: {user_id}")

        return UserProfileResponse(
            user_id=user["user_id"],
            email=user["email"],
            first_name=user.get("first_name"),
            last_name=user.get("last_name"),
            phone=user.get("phone"),
            date_of_birth=user.get("date_of_birth"),
            address=user.get("address"),
            kyc_verified=user.get("kyc_verified", False),
            segment=user.get("segment"),
            risk_tolerance=user.get("risk_tolerance"),
            created_at=user.get("created_at"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update user profile",
        )


@router.delete("/users/{user_id}")
async def delete_user_account(user_id: str):
    """
    Delete user account.

    This is a soft delete - marks the account as deleted.
    In production, implement proper data retention policies.

    Args:
        user_id: User ID to delete

    Returns:
        Success message
    """
    try:
        # Find user by user_id
        user_email = None
        for email, data in users_db.items():
            if data.get("user_id") == user_id:
                user_email = email
                break

        if not user_email:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID '{user_id}' not found",
            )

        # Soft delete - mark as deleted
        from datetime import datetime
        users_db[user_email]["deleted"] = True
        users_db[user_email]["deleted_at"] = datetime.utcnow().isoformat()
        users_db[user_email]["status"] = "deleted"

        logger.info(f"Deleted user account: {user_id}")

        return {
            "message": "Account deleted successfully",
            "user_id": user_id,
            "deleted_at": users_db[user_email]["deleted_at"],
            "notice": "Data will be permanently removed after 30 days",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete user account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete user account",
        )
