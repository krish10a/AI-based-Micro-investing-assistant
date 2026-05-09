"""Bulletproof NVIDIA NIM service with multi-model fallback system."""

import logging
import time
from typing import Dict, Any, Optional, List, Tuple
import httpx
from config.settings import settings
from config.nim import (
    NIM_MODEL_POOL,
    NIMModelConfig,
    ModelHealthTracker,
    get_model_health_tracker
)

logger = logging.getLogger(__name__)


class NIMFallbackService:
    """
    Multi-model NIM service with automatic fallback on failure.

    Features:
    - Automatic model switching on 401/500 errors
    - Health tracking per model
    - Priority-based model selection
    - Graceful degradation to rule-based fallback
    """

    def __init__(self):
        # HARDCODED KEY FOR DIAGNOSTICS - VERIFIED WORKING VIA POWERSHELL
        self.api_key = settings.nvidia_nim_api_key
        self.health_tracker = get_model_health_tracker(NIM_MODEL_POOL)
        self.model_configs = {m.model_id: m for m in NIM_MODEL_POOL}

        # Fallback configuration
        self.max_total_retries = 5
        self.base_timeout = 30

        logger.info(f"NIM Fallback Service initialized with {len(NIM_MODEL_POOL)} models")
        logger.info(f"API Key Prefix: {self.api_key[:10]}...")
        logger.info(f"Base URL: {settings.nvidia_nim_base_url}")
        logger.info(f"Primary model: {settings.nim_model}")
        logger.info(f"Model pool: {[m.model_id for m in NIM_MODEL_POOL]}")

    def _build_system_prompt(self) -> str:
        """Build the system prompt for NIM with premium formatting."""
        return """You are an elite AI Wealth Strategist for a micro-investing platform. Your goal is to transform structured financial data into a sophisticated, highly readable 'Wealth Narrative'.

STYLE & TONE:
- Professional, analytical, yet accessible.
- Use 'Wealth Strategy' terminology (e.g., 'Capital Allocation', 'Financial Runway', 'Growth Velocity').
- Be punchy and structured.

FORMATTING RULES:
1. Use **Bold** for all currency amounts and percentages.
2. Use clear section headers with emojis.
3. Use a structured bullet-point layout for strategies.
4. Keep the total length under 200 words.

CONTENT CONSTRAINTS:
1. NEVER change a number provided in the source data.
2. NEVER invent new metrics.
3. ALWAYS emphasize the 'Why' behind the specific asset allocation.
4. If confidence is low, be transparent but constructive."""

    def _build_prompt(
        self,
        segment: str,
        plan: str,
        investment: float,
        appetite: str,
        confidence: float,
        income: float,
        savings: float,
        savings_rate: float,
        allocations: List[Dict[str, Any]]
    ) -> str:
        """Build the user prompt for NIM."""
        # Build allocation text
        allocation_text = ""
        if allocations:
            allocation_text = "\n".join([
                f"- {a['goal_name']}: ₹{a['amount']:,.0f}/month ({a['percentage']*100:.0f}%)"
                for a in allocations[:5]
            ])

        # Confidence messaging
        confidence_msg = ""
        if confidence < 0.6:
            confidence_msg = f"\nCONFIDENCE NOTE: Your confidence score is {confidence*100:.1f}%, which is moderate. Consider providing more financial details for a more tailored plan."

        prompt = f"""Create a Strategic Wealth Narrative for the following profile:

📊 FINANCIAL SNAPSHOT:
- Segment: **{segment}**
- Monthly Income: **₹{income:,.0f}**
- Surplus for Investment: **₹{savings:,.0f}**
- Efficiency (Savings Rate): **{savings_rate*100:.1f}%**
- Recommendation: **{plan}**

🏗️ ALLOCATION STRATEGY:
{allocation_text if allocation_text else "Strategic diversification pending."}

{confidence_msg if confidence_msg else ""}

NARRATIVE STRUCTURE:
1. 💡 **The Insight**: Explain what being a '{segment}' means for their long-term growth.
2. 🎯 **Strategic Logic**: Give 2 specific reasons why this allocation fits their specific income/surplus profile.
3. 🚀 **Velocity Tip**: Provide one actionable tip to improve their financial health further.

Remember: Use **Bold** for every single number and percentage."""

        return prompt

    def _call_model(
        self,
        model_id: str,
        prompt: str
    ) -> Tuple[str, bool]:
        """
        Call a specific model and return (response, success).
        Uses direct httpx call to bypass any client-side authentication issues.
        """
        try:
            url = f"{settings.nvidia_nim_base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model_id,
                "messages": [
                    {"role": "user", "content": f"{self._build_system_prompt()}\n\n{prompt}"}
                ],
                "temperature": 0.7,
                "max_tokens": 512,
                "top_p": 0.9,
                "stream": False
            }

            with httpx.Client(timeout=self.base_timeout) as client:
                resp = client.post(url, headers=headers, json=payload)
                
                if resp.status_code == 200:
                    data = resp.json()
                    response = data["choices"][0]["message"]["content"].strip()
                    logger.info(f"NIM direct call successful: {model_id}")
                    return response, True
                else:
                    logger.error(f"NIM direct call failed for {model_id}: {resp.status_code} - {resp.text}")
                    self.health_tracker.record_failure(model_id, f"HTTP {resp.status_code}")
                    return "", False

        except Exception as e:
            error_msg = f"Unexpected error for {model_id}: {e}"
            logger.error(error_msg)
            self.health_tracker.record_failure(model_id, error_msg)
            return "", False

    def generate_explanation(
        self,
        recommendation: Dict[str, Any],
        user_profile: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate explanation with automatic multi-model fallback.
        """
        try:
            # Extract data from recommendation
            segment = recommendation.get("segment", "Unknown")
            plan = recommendation.get("recommended_plan", "")
            investment = recommendation.get("suggested_monthly_investment", 0)
            appetite = recommendation.get("investment_appetite", "")
            confidence = recommendation.get("confidence", 0)

            financial_metrics = recommendation.get("financial_summary_dict", {})
            income = financial_metrics.get("income", 0)
            savings = financial_metrics.get("savings", 0)
            savings_rate = savings / (income + 1e-9) if income > 0 else 0

            goal_allocation = recommendation.get("portfolio", {})
            allocations = goal_allocation.get("allocations", [])

            # Build prompt
            prompt = self._build_prompt(
                segment=segment,
                plan=plan,
                investment=investment,
                appetite=appetite,
                confidence=confidence,
                income=income,
                savings=savings,
                savings_rate=savings_rate,
                allocations=allocations
            )

            # Track which models we've tried
            tried_models = set()
            total_attempts = 0

            # Get initial model
            primary_model = settings.nim_model
            model_to_try = primary_model

            while total_attempts < self.max_total_retries:
                if model_to_try in tried_models:
                    healthy = self.health_tracker.get_healthy_models(NIM_MODEL_POOL)
                    next_model = None
                    for m in healthy:
                        if m.model_id not in tried_models:
                            next_model = m.model_id
                            break

                    if next_model is None:
                        for m in NIM_MODEL_POOL:
                            if m.model_id not in tried_models and m.is_active:
                                next_model = m.model_id
                                break

                    if next_model is None:
                        break  # No more models to try

                    model_to_try = next_model

                tried_models.add(model_to_try)
                total_attempts += 1

                logger.info(
                    f"NIM explanation attempt {total_attempts}/{self.max_total_retries} "
                    f"using model: {model_to_try}"
                )

                response, success = self._call_model(model_to_try, prompt)

                if success:
                    self.health_tracker.record_success(model_to_try)
                    return response

                # Get next fallback model
                next_model_config = self.health_tracker.get_next_fallback_model(
                    model_to_try,
                    NIM_MODEL_POOL
                )

                if next_model_config is None:
                    logger.warning("No more fallback models available")
                    break

                model_to_try = next_model_config.model_id

            # All models failed - return fallback explanation
            logger.warning("All NIM models failed, returning rule-based fallback")
            return self._generate_fallback_explanation(recommendation)

        except Exception as e:
            logger.error(f"NIM explanation failed: {e}", exc_info=True)
            return self._generate_fallback_explanation(recommendation)

    def _generate_fallback_explanation(
        self,
        recommendation: Dict[str, Any]
    ) -> str:
        """Generate a simple fallback explanation when all NIM models fail."""
        segment = recommendation.get("segment", "Unknown")
        investment = recommendation.get("suggested_monthly_investment", 0)
        plan = recommendation.get("recommended_plan", "")

        # Normalize segment names
        segment_normalized = segment.lower() if segment else ""

        explanations = {
            "financially stressed": f"Based on your financial profile, you're currently in the 'Financially Stressed' segment. This means your priority should be building stability before investing.\n\nRecommended first step: Focus on building an emergency fund of at least 1-2 months of expenses.",
            "cash-flow tight": f"You're in the 'Cash-Flow Tight' segment - you have some savings but want to be careful with risk. This is a good position to start micro-investing.\n\nRecommended first step: Consider starting with ₹{investment:,.0f} per month in a low-risk SIP.",
            "stable builder": f"You're a 'Stable Builder' - you have healthy savings and can handle moderate investment risk. This is a great position to build long-term wealth.\n\nRecommended first step: Start investing ₹{investment:,.0f} per month through a diversified SIP approach.",
            "high-surplus builder": f"You're a 'High-Surplus Builder' - you have excellent savings capacity and can pursue aggressive wealth building.\n\nRecommended first step: Deploy ₹{investment:,.0f} per month across equity funds and direct stocks.",
            "wealth accelerator": f"You're in the 'Wealth Accelerator' segment - you have exceptional savings capacity and should pursue multi-asset wealth building.\n\nRecommended first step: Immediately deploy ₹{investment:,.0f} per month into a diversified portfolio."
        }

        # Try normalized match
        for key, value in explanations.items():
            if key in segment_normalized or segment_normalized in key:
                return value

        return f"Based on your financial analysis, you fall into the '{segment}' category.\n\nRecommended action: {plan}\n\nKey takeaway: {'Focus on building an emergency fund first' if investment == 0 else f'Consider investing ₹{investment:,.0f} per month'}"

    def get_health_report(self) -> Dict[str, Any]:
        """Get health report for all models."""
        return {
            "models": self.health_tracker.get_health_report(),
            "pool": [m.model_id for m in NIM_MODEL_POOL],
            "primary_model": settings.nim_model
        }

    def chat_explanation(
        self,
        message: str,
        user_profile: Dict[str, Any]
    ) -> str:
        """Handle conversational follow-up questions with fallback."""
        try:
            prompt = f"User message: {message}\n\nUser's financial profile:\n{user_profile}\n\nRespond helpfully while staying within your role as a micro-investing guide."

            tried_models = set()
            total_attempts = 0
            model_to_try = settings.nim_model

            while total_attempts < self.max_total_retries:
                if model_to_try in tried_models:
                    healthy = self.health_tracker.get_healthy_models(NIM_MODEL_POOL)
                    next_model = None
                    for m in healthy:
                        if m.model_id not in tried_models:
                            next_model = m.model_id
                            break
                    if next_model is None:
                        break
                    model_to_try = next_model

                tried_models.add(model_to_try)
                total_attempts += 1

                response, success = self._call_model(model_to_try, prompt)
                if success:
                    self.health_tracker.record_success(model_to_try)
                    return response

                next_model_config = self.health_tracker.get_next_fallback_model(
                    model_to_try,
                    NIM_MODEL_POOL
                )
                if next_model_config is None:
                    break
                model_to_try = next_model_config.model_id

            return "I'm having trouble accessing my explanation service right now. Please try again later."

        except Exception as e:
            logger.error(f"NIM chat failed: {e}")
            return "I'm having trouble accessing my explanation service right now. Please try again later."
