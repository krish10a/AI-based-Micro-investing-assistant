"""SIP (Systematic Investment Plan) management routes."""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status, Query

from models.schemas import (
    SIPCreate,
    SIPUpdate,
    SIPPauseResume,
    SIPResponse,
    SIPListResponse,
    SIPStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory storage for SIPs
sips_storage: Dict[str, Dict[str, Any]] = {}
sip_counter = 0


def _calculate_projected_maturity(
    monthly_amount: float,
    duration_months: int,
    expected_return_rate: float,
) -> float:
    """Calculate projected maturity value using SIP formula."""
    if duration_months <= 0:
        return monthly_amount

    monthly_rate = expected_return_rate / 12 / 100 if expected_return_rate > 0 else 0

    if monthly_rate == 0:
        return monthly_amount * duration_months

    # SIP formula: FV = P * (((1 + r)^n - 1) / r) * (1 + r)
    factor = (((1 + monthly_rate) ** duration_months - 1) / monthly_rate) * (
        1 + monthly_rate
    )
    return monthly_amount * factor


@router.post("/sips", status_code=status.HTTP_201_CREATED)
async def create_sip(sip_data: SIPCreate):
    """
    Create a new SIP (Systematic Investment Plan).

    Args:
        user_id: User ID
        goal_id: Associated goal ID
        monthly_amount: Monthly investment amount
        start_date: Start date (YYYY-MM-DD)
        duration_months: Duration in months
        expected_return_rate: Expected annual return rate
        investment_type: Investment type (mutual_fund, etc.)

    Returns:
        Created SIP
    """
    global sip_counter

    try:
        sip_id = str(uuid.uuid4())
        sip_counter += 1

        now = datetime.utcnow().isoformat()

        # Calculate projected maturity
        projected_maturity = _calculate_projected_maturity(
            sip_data.monthly_amount,
            sip_data.duration_months,
            sip_data.expected_return_rate,
        )

        sip = {
            "id": sip_id,
            "user_id": sip_data.user_id,
            "goal_id": sip_data.goal_id,
            "monthly_amount": sip_data.monthly_amount,
            "start_date": sip_data.start_date,
            "duration_months": sip_data.duration_months,
            "expected_return_rate": sip_data.expected_return_rate,
            "investment_type": sip_data.investment_type,
            "status": SIPStatus.ACTIVE.value,
            "current_value": 0.0,
            "total_invested": 0.0,
            "months_elapsed": 0,
            "projected_maturity": projected_maturity,
            "metadata": sip_data.metadata or {},
            "created_at": now,
            "updated_at": now,
        }

        sips_storage[sip_id] = sip

        logger.info(f"Created SIP: {sip_id} for user {sip_data.user_id}")

        return SIPResponse(**sip)

    except Exception as e:
        logger.error(f"Failed to create SIP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create SIP",
        )


@router.get("/sips", response_model=SIPListResponse)
async def list_sips(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    goal_id: Optional[str] = Query(None, description="Filter by goal ID"),
    limit: int = Query(default=20, le=100, description="Number of results"),
    offset: int = Query(default=0, description="Offset for pagination"),
):
    """
    List SIPs with optional filters.

    Args:
        user_id: Filter by user ID
        status_filter: Filter by status (active, paused, completed, cancelled)
        goal_id: Filter by goal ID
        limit: Maximum number of results
        offset: Pagination offset

    Returns:
        Paginated list of SIPs with counts
    """
    try:
        sips = list(sips_storage.values())

        # Apply filters
        if user_id:
            sips = [s for s in sips if s["user_id"] == user_id]

        if status_filter:
            sips = [s for s in sips if s["status"] == status_filter]

        if goal_id:
            sips = [s for s in sips if s["goal_id"] == goal_id]

        # Sort by created_at descending
        sips.sort(key=lambda x: x["created_at"], reverse=True)

        # Pagination
        total_count = len(sips)
        paginated = sips[offset : offset + limit]

        # Count by status
        active_count = len([s for s in sips if s["status"] == SIPStatus.ACTIVE.value])
        paused_count = len([s for s in sips if s["status"] == SIPStatus.PAUSED.value])
        completed_count = len(
            [s for s in sips if s["status"] == SIPStatus.COMPLETED.value]
        )

        return SIPListResponse(
            sips=paginated,
            total_count=total_count,
            active_count=active_count,
            paused_count=paused_count,
            completed_count=completed_count,
        )

    except Exception as e:
        logger.error(f"Failed to list SIPs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve SIPs",
        )


@router.get("/sips/{sip_id}")
async def get_sip(sip_id: str):
    """
    Get a specific SIP by ID.

    Args:
        sip_id: SIP ID

    Returns:
        SIP details
    """
    try:
        sip = sips_storage.get(sip_id)

        if not sip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SIP with ID '{sip_id}' not found",
            )

        return SIPResponse(**sip)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get SIP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve SIP",
        )


@router.put("/sips/{sip_id}")
async def update_sip(sip_id: str, update_data: SIPUpdate):
    """
    Update an existing SIP.

    Args:
        sip_id: SIP ID to update
        update_data: Fields to update (monthly_amount, expected_return_rate, status, metadata)

    Returns:
        Updated SIP
    """
    try:
        sip = sips_storage.get(sip_id)

        if not sip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SIP with ID '{sip_id}' not found",
            )

        update_dict = update_data.model_dump(exclude_unset=True)

        # Update fields
        for key, value in update_dict.items():
            if value is not None:
                if key == "status":
                    sip[key] = value.value  # Convert enum to string
                elif key == "metadata":
                    sip[key].update(value)
                else:
                    sip[key] = value

        # Recalculate projected maturity if amount or return rate changed
        if "monthly_amount" in update_dict or "expected_return_rate" in update_dict:
            sip["projected_maturity"] = _calculate_projected_maturity(
                sip["monthly_amount"],
                sip["duration_months"],
                sip["expected_return_rate"],
            )

        sip["updated_at"] = datetime.utcnow().isoformat()
        sips_storage[sip_id] = sip

        logger.info(f"Updated SIP: {sip_id}")

        return SIPResponse(**sip)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update SIP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update SIP",
        )


@router.post("/sips/{sip_id}/pause")
async def pause_sip(sip_id: str):
    """
    Pause an active SIP.

    Args:
        sip_id: SIP ID to pause

    Returns:
        Success message
    """
    try:
        sip = sips_storage.get(sip_id)

        if not sip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SIP with ID '{sip_id}' not found",
            )

        if sip["status"] != SIPStatus.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot pause SIP with status '{sip['status']}'",
            )

        sip["status"] = SIPStatus.PAUSED.value
        sip["updated_at"] = datetime.utcnow().isoformat()
        sips_storage[sip_id] = sip

        logger.info(f"Paused SIP: {sip_id}")

        return {
            "message": "SIP paused successfully",
            "sip_id": sip_id,
            "paused_at": sip["updated_at"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pause SIP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not pause SIP",
        )


@router.post("/sips/{sip_id}/resume")
async def resume_sip(sip_id: str):
    """
    Resume a paused SIP.

    Args:
        sip_id: SIP ID to resume

    Returns:
        Success message
    """
    try:
        sip = sips_storage.get(sip_id)

        if not sip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SIP with ID '{sip_id}' not found",
            )

        if sip["status"] != SIPStatus.PAUSED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot resume SIP with status '{sip['status']}'",
            )

        sip["status"] = SIPStatus.ACTIVE.value
        sip["updated_at"] = datetime.utcnow().isoformat()
        sips_storage[sip_id] = sip

        logger.info(f"Resumed SIP: {sip_id}")

        return {
            "message": "SIP resumed successfully",
            "sip_id": sip_id,
            "resumed_at": sip["updated_at"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume SIP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not resume SIP",
        )


@router.delete("/sips/{sip_id}")
async def cancel_sip(sip_id: str):
    """
    Cancel an SIP.

    Args:
        sip_id: SIP ID to cancel

    Returns:
        Success message
    """
    try:
        sip = sips_storage.get(sip_id)

        if not sip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"SIP with ID '{sip_id}' not found",
            )

        if sip["status"] in [SIPStatus.CANCELLED.value, SIPStatus.COMPLETED.value]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel SIP with status '{sip['status']}'",
            )

        sip["status"] = SIPStatus.CANCELLED.value
        sip["updated_at"] = datetime.utcnow().isoformat()
        sips_storage[sip_id] = sip

        logger.info(f"Cancelled SIP: {sip_id}")

        return {
            "message": "SIP cancelled successfully",
            "sip_id": sip_id,
            "cancelled_at": sip["updated_at"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel SIP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not cancel SIP",
        )
