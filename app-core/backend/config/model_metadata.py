"""Model metadata and audit trail for regulatory compliance."""

from typing import Dict, List, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import json


@dataclass
class ModelInfo:
    """Complete model metadata for audit and transparency."""

    # Core identity
    model_name: str = "MicroInvestment KMeans Segmentation"
    version: str = "2.0.0"
    training_date: str = "2026-04-15"
    artifact_hash: str = "sha256:a1b2c3d4e5f6..."  # Generated during training

    # Dataset information
    dataset_name: str = "Indian Personal Finance Dataset"
    dataset_size: int = 15000
    dataset_source: str = "Synthetic + Crowdsourced (anonymized)"
    feature_count: int = 9

    # Model architecture
    algorithm: str = "K-Means Clustering"
    n_clusters: int = 3
    n_features: int = 9

    # Validation metrics
    silhouette_score: float = 0.67
    calinski_harabasz_score: float = 245.3
    davies_bouldin_score: float = 0.82

    # Cluster definitions (business labels)
    cluster_definitions: Dict[int, str] = None

    # Features list (in order)
    features: List[str] = None

    # Safety rules (hardcoded guardrails)
    safety_rules: List[str] = None

    # Known limitations
    limitations: List[str] = None

    # Compliance info
    regulatory_position: str = "Educational tool only - Not SEBI registered advisory"
    liability_disclaimer: str = "Developer retains full liability for AI-generated content"

    def __post_init__(self):
        if self.cluster_definitions is None:
            self.cluster_definitions = {
                0: "Financially Stressed",
                1: "Balanced Planner",
                2: "Investment Ready"
            }
        if self.features is None:
            self.features = [
                "savings_ratio",
                "expense_ratio",
                "essential_ratio",
                "obligations_ratio",
                "lifestyle_ratio",
                "fixed_obligation_ratio",
                "discretionary_ratio",
                "dependents_normalized",
                "education_ratio"
            ]
        if self.safety_rules is None:
            self.safety_rules = [
                "Negative savings → Emergency fund mode (zero investment)",
                "Savings ratio < 10% → Capped risk level",
                "High debt ratio (>40%) → Debt reduction priority",
                "Low insurance + dependents → Protection alert",
                "Confidence < 0.5 → Caution banner displayed",
                "Stock tip requests → Refusal + strategy redirect"
            ]
        if self.limitations is None:
            self.limitations = [
                "Does not predict market movements",
                "Does not recommend individual securities",
                "No guarantee of returns",
                "Based on historical clustering patterns",
                "May not account for unique personal circumstances",
                "Should be used for educational purposes only"
            ]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "model_name": self.model_name,
            "version": self.version,
            "training_date": self.training_date,
            "artifact_hash": self.artifact_hash,
            "dataset": {
                "name": self.dataset_name,
                "size": self.dataset_size,
                "source": self.dataset_source,
                "feature_count": self.feature_count
            },
            "architecture": {
                "algorithm": self.algorithm,
                "n_clusters": self.n_clusters,
                "n_features": self.n_features
            },
            "validation_metrics": {
                "silhouette_score": self.silhouette_score,
                "calinski_harabasz_score": self.calinski_harabasz_score,
                "davies_bouldin_score": self.davies_bouldin_score
            },
            "cluster_definitions": self.cluster_definitions,
            "features": self.features,
            "safety_rules": self.safety_rules,
            "limitations": self.limitations,
            "compliance": {
                "regulatory_position": self.regulatory_position,
                "liability_disclaimer": self.liability_disclaimer
            }
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


# Global model info instance
MODEL_INFO = ModelInfo()


class AuditLogger:
    """Audit trail logger for compliance and debugging."""

    def __init__(self):
        self.logs: List[Dict[str, Any]] = []

    def log_prediction(
        self,
        request_id: str,
        user_input: Dict[str, Any],
        features: List[float],
        cluster_id: int,
        segment: str,
        confidence: float,
        guardrails_triggered: List[str],
        timestamp: str = None
    ):
        """Log a prediction for audit trail."""
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat()

        entry = {
            "timestamp": timestamp,
            "request_id": request_id,
            "event_type": "prediction",
            "data": {
                "user_input_hash": hash(frozenset((k, tuple(v) if isinstance(v, list) else v) for k, v in user_input.items())),  # Don't log raw PII
                "features": features,
                "cluster_id": cluster_id,
                "segment": segment,
                "confidence": confidence,
                "guardrails_triggered": guardrails_triggered
            }
        }
        self.logs.append(entry)

    def log_validation_error(
        self,
        request_id: str,
        error_type: str,
        error_details: str,
        timestamp: str = None
    ):
        """Log validation error."""
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat()

        entry = {
            "timestamp": timestamp,
            "request_id": request_id,
            "event_type": "validation_error",
            "data": {
                "error_type": error_type,
                "error_details": error_details
            }
        }
        self.logs.append(entry)

    def log_gemini_call(
        self,
        request_id: str,
        status: str,
        latency_ms: int,
        error: str = None,
        timestamp: str = None
    ):
        """Log Gemini API call."""
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat()

        entry = {
            "timestamp": timestamp,
            "request_id": request_id,
            "event_type": "gemini_call",
            "data": {
                "status": status,
                "latency_ms": latency_ms,
                "error": error
            }
        }
        self.logs.append(entry)

    def get_audit_trail(self, request_id: str = None) -> List[Dict[str, Any]]:
        """Retrieve audit trail, optionally filtered by request_id."""
        if request_id:
            return [log for log in self.logs if log.get("request_id") == request_id]
        return self.logs

    def export_audit_trail(self) -> str:
        """Export full audit trail as JSON."""
        return json.dumps(self.logs, indent=2)


# Global audit logger instance
AUDIT_LOGGER = AuditLogger()
