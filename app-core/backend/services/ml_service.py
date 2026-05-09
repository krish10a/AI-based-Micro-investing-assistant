"""ML service wrapper for inference."""

import logging
from typing import Dict, Any

from models.ml_pipeline import MicroInvestmentAssistant
from utils.feature_engineering import build_features
from config.settings import settings

logger = logging.getLogger(__name__)


class MLService:
    """Service layer for ML inference."""

    def __init__(self):
        self.assistant = MicroInvestmentAssistant(artifacts_dir=settings.artifacts_dir)

    def analyze(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze user financial input and return recommendation.

        Args:
            user_input: Dict with income, expenses categories

        Returns:
            Structured recommendation dict
        """
        try:
            # Build features
            features, income, total_expenses, savings = build_features(user_input)

            # Get recommendation with income for rule overrides
            rec, segment_override, multiplier_override = self.assistant.recommend(
                features, savings, income
            )

            # Get confidence
            confidence = self.assistant.confidence(features)

            # Determine risk level with structured data
            if segment_override is not None and segment_override == min(
                self.assistant.segment_map.keys(),
                key=lambda c: self.assistant.segment_map[c]["multiplier"]
            ):
                risk_level = {"label": "LOW", "color": "success", "description": "Capital Preservation"}
            elif rec["investment_appetite"] in ["High", "Very High"]:
                risk_level = {"label": "HIGH", "color": "error", "description": "Growth Focused"}
            else:
                risk_level = {"label": "MEDIUM", "color": "warning", "description": "Balanced"}

            return {
                "cluster_id": rec["cluster_id"],
                "segment": rec["user_segment"],
                "recommended_plan": rec["recommended_plan"],
                "suggested_monthly_investment": rec["suggested_monthly_investment"],
                "investment_appetite": rec["investment_appetite"],
                "reason_codes": rec["reason_codes"],
                "confidence": round(confidence, 3),
                "risk_level": risk_level,
                "financial_summary": {
                    "income": income,
                    "total_expenses": total_expenses,
                    "savings": savings,
                    "savings_ratio": rec.get("savings_ratio", 0)
                },
                "warnings": rec["reason_codes"],
                "income_level": rec.get("income_level", "normal"),
                "allocation_details": rec.get("allocation_details", {})
            }

        except Exception as e:
            logger.error(f"ML inference failed: {e}")
            raise
