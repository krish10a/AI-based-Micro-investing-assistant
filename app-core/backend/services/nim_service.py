"""NVIDIA NIM service wrapper - now with automatic multi-model fallback."""

import logging
from typing import Dict, Any, Optional

from services.nim_fallback_service import NIMFallbackService

logger = logging.getLogger(__name__)


class NIMService:
    """
    NIM service with automatic multi-model fallback.

    This is a thin wrapper around NIMFallbackService that maintains
    backward compatibility with existing code.
    """

    def __init__(self):
        self._fallback_service = NIMFallbackService()
        logger.info("NIMService initialized with multi-model fallback")

    def generate_explanation(
        self,
        recommendation: Dict[str, Any],
        user_profile: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate beginner-friendly explanation with automatic fallback.

        If the primary model fails, automatically tries:
        1. mistralai/mistral-medium-3.5-128b
        2. google/gemma-4-31b-it
        3. qwen/qwen3-next-80b-a3b-instruct
        4. meta/llama-3.1-405b-instruct

        If all models fail, returns rule-based fallback explanation.

        Args:
            recommendation: Complete analysis result with financial metrics
            user_profile: Optional additional user context

        Returns:
            Natural language explanation (never raises exception)
        """
        return self._fallback_service.generate_explanation(recommendation, user_profile)

    def chat_explanation(
        self,
        message: str,
        user_profile: Dict[str, Any]
    ) -> str:
        """Handle conversational follow-up questions."""
        try:
            # Use the fallback service for chat as well
            return self._fallback_service.chat_explanation(message, user_profile)

        except Exception as e:
            logger.error(f"NIM chat failed: {e}")
            return "I'm having trouble accessing my explanation service right now. Please try again, or refer to your main recommendation for guidance."

    def get_health_report(self) -> Dict[str, Any]:
        """Get health status of all models in the pool."""
        return self._fallback_service.get_health_report()
