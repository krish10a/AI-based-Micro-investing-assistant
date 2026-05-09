"""Transaction management routes."""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status, Query

from models.schemas import (
    TransactionCreate,
    TransactionResponse,
    TransactionListResponse,
    TransactionType,
    TransactionStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory storage for transactions
transactions_storage: Dict[str, Dict[str, Any]] = {}
transaction_counter = 0


@router.post("/transactions", status_code=status.HTTP_201_CREATED)
async def create_transaction(transaction_data: TransactionCreate):
    """
    Create a new transaction.

    Args:
        user_id: User ID
        type: Transaction type (deposit, withdrawal, investment, goal_allocation)
        amount: Transaction amount
        category: Transaction category
        goal_id: Associated goal ID (optional)
        description: Transaction description (optional)

    Returns:
        Created transaction
    """
    global transaction_counter

    try:
        transaction_id = str(uuid.uuid4())
        transaction_counter += 1

        now = datetime.utcnow().isoformat()

        transaction = {
            "id": transaction_id,
            "user_id": transaction_data.user_id,
            "type": transaction_data.type.value,
            "amount": transaction_data.amount,
            "category": transaction_data.category,
            "goal_id": transaction_data.goal_id,
            "description": transaction_data.description,
            "status": TransactionStatus.COMPLETED.value,
            "metadata": transaction_data.metadata or {},
            "created_at": now,
            "updated_at": now,
        }

        transactions_storage[transaction_id] = transaction

        logger.info(f"Created transaction: {transaction_id} for user {transaction_data.user_id}")

        return TransactionResponse(**transaction)

    except Exception as e:
        logger.error(f"Failed to create transaction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create transaction",
        )


@router.get("/transactions", response_model=TransactionListResponse)
async def list_user_transactions(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    type_filter: Optional[str] = Query(None, description="Filter by transaction type"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(default=20, le=100, description="Number of results"),
    offset: int = Query(default=0, description="Offset for pagination"),
):
    """
    List transactions with optional filters.

    Args:
        user_id: Filter by user ID
        type_filter: Filter by transaction type
        status_filter: Filter by status
        limit: Maximum number of results
        offset: Pagination offset

    Returns:
        Paginated list of transactions
    """
    try:
        transactions = list(transactions_storage.values())

        # Apply filters
        if user_id:
            transactions = [t for t in transactions if t["user_id"] == user_id]

        if type_filter:
            transactions = [t for t in transactions if t["type"] == type_filter]

        if status_filter:
            transactions = [t for t in transactions if t["status"] == status_filter]

        # Sort by created_at descending
        transactions.sort(key=lambda x: x["created_at"], reverse=True)

        # Pagination
        total_count = len(transactions)
        paginated = transactions[offset : offset + limit]

        return TransactionListResponse(
            transactions=paginated,
            total_count=total_count,
            page=offset // limit + 1 if limit > 0 else 1,
            page_size=limit,
        )

    except Exception as e:
        logger.error(f"Failed to list transactions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve transactions",
        )


@router.get("/transactions/{transaction_id}")
async def get_transaction(transaction_id: str):
    """
    Get a specific transaction by ID.

    Args:
        transaction_id: Transaction ID

    Returns:
        Transaction details
    """
    try:
        transaction = transactions_storage.get(transaction_id)

        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction with ID '{transaction_id}' not found",
            )

        return TransactionResponse(**transaction)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get transaction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve transaction",
        )


@router.post("/transactions/{transaction_id}/cancel")
async def cancel_transaction(transaction_id: str):
    """
    Cancel a pending transaction.

    Args:
        transaction_id: Transaction ID to cancel

    Returns:
        Success message
    """
    try:
        transaction = transactions_storage.get(transaction_id)

        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction with ID '{transaction_id}' not found",
            )

        if transaction["status"] != TransactionStatus.PENDING.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel transaction with status '{transaction['status']}'",
            )

        transaction["status"] = TransactionStatus.CANCELLED.value
        transaction["updated_at"] = datetime.utcnow().isoformat()

        logger.info(f"Cancelled transaction: {transaction_id}")

        return {
            "message": "Transaction cancelled successfully",
            "transaction_id": transaction_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel transaction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not cancel transaction",
        )
