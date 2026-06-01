"""NVIDIA NIM multi-model configuration with fallback chain."""

from typing import List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class NIMModelConfig:
    """Configuration for a single NIM model."""
    model_id: str
    name: str
    priority: int  # Lower = higher priority
    max_retries: int = 3
    is_active: bool = True


# Primary model pool - ordered by priority
NIM_MODEL_POOL: List[NIMModelConfig] = [
    NIMModelConfig(
        model_id="meta/llama-3.1-8b-instruct",
        name="Llama 3.1 8B Instruct",
        priority=1
    ),
    NIMModelConfig(
        model_id="meta/llama-3.1-70b-instruct",
        name="Llama 3.1 70B Instruct",
        priority=2
    ),
    NIMModelConfig(
        model_id="mistralai/mistral-7b-instruct-v0.3",
        name="Mistral 7B Instruct v0.3",
        priority=3
    ),
    NIMModelConfig(
        model_id="mistralai/mixtral-8x7b-instruct-v0.1",
        name="Mixtral 8x7B Instruct v0.1",
        priority=4
    ),
    NIMModelConfig(
        model_id="nvidia/nemotron-4-340b-instruct",
        name="Nemotron 4 340B Instruct",
        priority=5
    ),
]


@dataclass
class ModelHealthStats:
    """Health statistics for a model."""
    model_id: str
    success_count: int = 0
    failure_count: int = 0
    last_error: str = ""
    last_error_time: float = 0
    consecutive_failures: int = 0

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 1.0

    @property
    def is_healthy(self) -> bool:
        # Mark model as unhealthy after 5 consecutive failures
        return self.consecutive_failures < 5


class ModelHealthTracker:
    """Tracks health statistics for all models in the pool."""

    def __init__(self, model_pool: List[NIMModelConfig]):
        self.stats: Dict[str, ModelHealthStats] = {
            model.model_id: ModelHealthStats(model_id=model.model_id)
            for model in model_pool
        }

    def record_success(self, model_id: str):
        """Record a successful API call."""
        if model_id in self.stats:
            self.stats[model_id].success_count += 1
            self.stats[model_id].consecutive_failures = 0
            self.stats[model_id].last_error = ""

    def record_failure(self, model_id: str, error: str):
        """Record a failed API call."""
        if model_id in self.stats:
            self.stats[model_id].failure_count += 1
            self.stats[model_id].consecutive_failures += 1
            self.stats[model_id].last_error = error
            self.stats[model_id].last_error_time = 0  # Use current time

    def get_healthy_models(self, pool: List[NIMModelConfig]) -> List[NIMModelConfig]:
        """Get list of currently healthy models, sorted by priority."""
        healthy = []
        for model in sorted(pool, key=lambda m: m.priority):
            if not model.is_active:
                continue
            stats = self.stats.get(model.model_id)
            if stats and stats.is_healthy:
                healthy.append(model)
        return healthy

    def get_next_fallback_model(
        self,
        current_model_id: str,
        pool: List[NIMModelConfig]
    ) -> NIMModelConfig | None:
        """Get the next best fallback model after current model fails."""
        healthy = self.get_healthy_models(pool)

        # Find current model's position
        current_idx = -1
        for i, model in enumerate(sorted(pool, key=lambda m: m.priority)):
            if model.model_id == current_model_id:
                current_idx = i
                break

        # Return next healthy model with higher priority number (lower priority)
        for model in healthy:
            if model.model_id != current_model_id:
                return model

        # No healthy models, return any available model
        for model in sorted(pool, key=lambda m: m.priority):
            if model.model_id != current_model_id and model.is_active:
                return model

        return None

    def get_health_report(self) -> Dict[str, Dict]:
        """Get health report for all models."""
        return {
            model_id: {
                "success_rate": stats.success_rate,
                "success_count": stats.success_count,
                "failure_count": stats.failure_count,
                "consecutive_failures": stats.consecutive_failures,
                "last_error": stats.last_error,
                "is_healthy": stats.is_healthy
            }
            for model_id, stats in self.stats.items()
        }


# Global health tracker instance
_model_health_tracker: ModelHealthTracker | None = None


def get_model_health_tracker(pool: List[NIMModelConfig] = NIM_MODEL_POOL) -> ModelHealthTracker:
    """Get or create the global model health tracker."""
    global _model_health_tracker
    if _model_health_tracker is None:
        _model_health_tracker = ModelHealthTracker(pool)
    return _model_health_tracker


def reset_model_health_tracker():
    """Reset the global model health tracker (for testing)."""
    global _model_health_tracker
    _model_health_tracker = None
