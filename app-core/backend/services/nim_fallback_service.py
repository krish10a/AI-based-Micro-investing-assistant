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
            # Extract data from user_profile with fallback defaults
            segment = user_profile.get("user_segment", "Unknown")
            plan = user_profile.get("recommended_plan", "")
            
            goal_allocation = user_profile.get("portfolio", {})
            allocations = goal_allocation.get("allocations", [])
            investment = user_profile.get("suggested_monthly_investment", goal_allocation.get("total_monthly_investment", 0))
            
            appetite = user_profile.get("investment_appetite", "")
            confidence = user_profile.get("confidence", 0)

            financial_metrics = user_profile.get("financial_summary_dict", {})
            income = financial_metrics.get("income", user_profile.get("income", user_profile.get("monthly_income", 0)))
            savings = financial_metrics.get("savings", user_profile.get("savings", user_profile.get("monthly_savings", 0)))
            savings_rate = financial_metrics.get("savings_rate", user_profile.get("savings_rate", 0))
            if savings_rate == 0 and income > 0:
                expenses = financial_metrics.get("total_expenses", user_profile.get("expenses", user_profile.get("monthly_expenses", 0)))
                savings_rate = (income - expenses) / income if income > 0 else 0

            # Build base context prompt using the same method as generate_explanation for consistency
            base_context = self._build_prompt(
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

            prompt = f"FINANCIAL CONTEXT:\n{base_context}\n\n"
            
            rag_context = user_profile.get("rag_context")
            if rag_context:
                prompt += f"KNOWLEDGE BASE CONTEXT:\n{rag_context}\n\n"
                
            prompt += f"USER QUESTION:\n{message}\n\nPlease provide a helpful, direct response to the user's question using the financial context above. Do not repeat the entire wealth narrative, just answer the specific question."

            # Track which models we've tried
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
            return self._generate_rule_based_chat_response(message, user_profile if 'user_profile' in dir() else {})

    def _is_personal_data_query(self, message: str) -> bool:
        """Detect if the query needs user-specific financial data."""
        personal_keywords = [
            "my ", "i have", "i earn", "i spend", "i save", "i invest",
            "my income", "my expenses", "my savings", "my portfolio",
            "my plan", "my segment", "my score", "my health", "my strategy",
            "my allocation", "my goal", "my risk", "how much should i",
            "what should i", "am i", "can i", "will i", "forecast",
            "projection", "growth", "next year", "5 year", "10 year",
            "retire", "emergency fund", "sip amount", "invest how much",
        ]
        msg_lower = message.lower()
        return any(kw in msg_lower for kw in personal_keywords)

    def _generate_rule_based_chat_response(self, message: str, user_profile: Dict[str, Any]) -> str:
        """
        Smart rule-based fallback that answers using real user data for personal queries,
        and gives general educational answers for generic finance questions.
        """
        msg_lower = message.lower()

        # --- Generic finance education (no user data needed) ---
        if "what is sip" in msg_lower or "what's sip" in msg_lower or ("sip" in msg_lower and "what" in msg_lower):
            return (
                "**SIP (Systematic Investment Plan)** is a method to invest a fixed amount regularly "
                "(usually monthly) into mutual funds.\n\n"
                "📌 **Key Benefits:**\n"
                "- **Rupee Cost Averaging** – You buy more units when prices are low, fewer when high, "
                "reducing overall cost.\n"
                "- **Power of Compounding** – Returns on your returns grow exponentially over time.\n"
                "- **Disciplined Investing** – Auto-debit removes the temptation to time the market.\n\n"
                "💡 **Example:** ₹5,000/month at 12% annual return for 10 years = **₹11.6 Lakhs** "
                "(invested ₹6L, gains ₹5.6L).\n\n"
                "SIPs work best when started early and continued consistently through market ups and downs."
            )

        if "what is mutual fund" in msg_lower or "mutual fund" in msg_lower and "what" in msg_lower:
            return (
                "**Mutual Funds** are pooled investment vehicles managed by professional fund managers.\n\n"
                "📌 **Types:**\n"
                "- **Equity Funds** – Invest in stocks; high risk, high return (10–15% avg)\n"
                "- **Debt Funds** – Invest in bonds; low risk, stable return (6–8%)\n"
                "- **Hybrid Funds** – Mix of equity + debt; balanced risk/return\n"
                "- **Index Funds** – Track Nifty/Sensex; low cost, market returns\n\n"
                "💡 **For beginners:** Start with a **Nifty 50 Index Fund** via SIP — low cost, diversified, proven track record."
            )

        if "emergency fund" in msg_lower and ("what" in msg_lower or "why" in msg_lower):
            return (
                "**Emergency Fund** is 3–6 months of your living expenses kept in a liquid, safe account.\n\n"
                "📌 **Why it matters:**\n"
                "- Protects you from selling investments during a crisis (job loss, medical emergency)\n"
                "- Prevents high-interest debt (credit cards, personal loans)\n"
                "- Gives psychological peace to stay invested long-term\n\n"
                "💡 **Where to keep it:** High-yield savings account or Liquid Mutual Fund (better returns than savings, same liquidity)."
            )

        if "compound" in msg_lower or "compounding" in msg_lower:
            return (
                "**Compound Interest** is earning returns on your returns — the most powerful force in wealth building.\n\n"
                "📐 **Formula:** A = P × (1 + r)^n\n"
                "Where P = principal, r = annual rate, n = years\n\n"
                "💡 **Example:**\n"
                "- ₹10,000 at 12% for 10 years = **₹31,058** (3× your money)\n"
                "- ₹10,000 at 12% for 20 years = **₹96,463** (9.6× your money)\n\n"
                "The secret: **Start early.** Even 5 extra years doubles your final corpus."
            )

        # --- Personal data queries (use real user profile) ---
        if not self._is_personal_data_query(message):
            return (
                "I'm here to help with your investment strategy! You can ask me about:\n\n"
                "📊 **Your Portfolio:** growth forecast, allocation breakdown, SIP amounts\n"
                "💡 **Education:** what is SIP, mutual funds, compounding, emergency funds\n"
                "🎯 **Planning:** how much to invest, emergency fund goal, retirement planning\n\n"
                "What would you like to know?"
            )

        # Extract user financial data
        income = user_profile.get("monthly_income", user_profile.get("income", 0))
        expenses = user_profile.get("monthly_expenses", user_profile.get("expenses", 0))
        savings = income - expenses if income > 0 else user_profile.get("monthly_savings", 0)
        investment = user_profile.get("suggested_monthly_investment",
                      user_profile.get("portfolio", {}).get("total_monthly_investment", 0))
        segment = user_profile.get("user_segment", user_profile.get("segment", ""))
        health_score = user_profile.get("financial_health_score", 0)
        plan = user_profile.get("recommended_plan", "")
        risk_tolerance = user_profile.get("risk_tolerance", "moderate")
        allocations = user_profile.get("portfolio", {}).get("allocations", [])

        # Handle no data case
        if income == 0 and savings == 0:
            return (
                "I'd love to give you a personalized answer, but I don't have your financial data yet. "
                "Please complete your profile in the **Analysis** section so I can give you accurate, "
                "data-driven recommendations tailored to your situation."
            )

        # Growth forecast queries
        if any(kw in msg_lower for kw in ["forecast", "growth", "5 year", "10 year", "next", "future", "projection"]):
            if investment > 0:
                corpus_5y = investment * 12 * 5 * 1.08  # simplified 8% pa
                corpus_5y_12 = investment * ((1.01**60 - 1) / 0.01) * 1.01  # 12% pa monthly compounding
                corpus_10y = investment * ((1.01**120 - 1) / 0.01) * 1.01
                return (
                    f"📈 **Your 5-Year Growth Forecast** (based on ₹{investment:,.0f}/month SIP)\n\n"
                    f"| Horizon | Invested | Corpus (@12% p.a.) |\n"
                    f"|---------|----------|--------------------|\n"
                    f"| 5 Years | ₹{investment*60:,.0f} | **₹{corpus_5y_12:,.0f}** |\n"
                    f"| 10 Years| ₹{investment*120:,.0f} | **₹{corpus_10y:,.0f}** |\n\n"
                    f"🎯 **Your Segment:** {segment or 'Stable Builder'}\n"
                    f"💊 **Health Score:** {health_score}/100\n\n"
                    f"{'⚠️ Note: Your current savings surplus is ₹' + f'{savings:,.0f}' + '/month. ' if savings > 0 else ''}"
                    f"Consistency is key — avoid SIP breaks for best results."
                )
            else:
                return (
                    f"Your current financial profile shows **₹{savings:,.0f}** monthly surplus. "
                    f"However, you haven't set up a SIP yet. "
                    f"Based on your segment (**{segment or 'your profile'}**), I recommend starting with "
                    f"₹{max(500, int(savings * 0.3)):,.0f}/month and increasing it by 10% yearly.\n\n"
                    f"Complete your goals setup in the Analysis page to get a precise forecast."
                )

        # Health score queries
        if any(kw in msg_lower for kw in ["health score", "health", "score", "improve"]):
            rating = "Excellent" if health_score >= 80 else "Good" if health_score >= 60 else "Fair" if health_score >= 40 else "Needs Improvement"
            tips = []
            if savings / (income + 1e-9) < 0.2:
                tips.append("Reduce expenses to increase your savings rate above 20%")
            if investment < savings * 0.5:
                tips.append(f"Invest at least ₹{int(savings * 0.5):,.0f}/month (50% of your surplus)")
            tips.append("Build/maintain a 6-month emergency fund")
            return (
                f"📊 **Your Financial Health Score: {health_score}/100 — {rating}**\n\n"
                f"💰 Monthly Income: ₹{income:,.0f}\n"
                f"💸 Monthly Expenses: ₹{expenses:,.0f}\n"
                f"💚 Surplus: ₹{savings:,.0f} ({savings/(income+1e-9)*100:.0f}% savings rate)\n\n"
                f"🔧 **To Improve Your Score:**\n" +
                "\n".join(f"- {tip}" for tip in tips)
            )

        # Allocation breakdown
        if any(kw in msg_lower for kw in ["allocation", "where", "invest", "portfolio breakdown", "how much"]):
            if allocations:
                alloc_text = "\n".join([
                    f"- **{a['goal_name']}**: ₹{a['amount']:,.0f}/month ({a.get('percentage', 0)*100:.0f}%)"
                    for a in allocations[:6]
                ])
                return (
                    f"🎯 **Your AI-Recommended Allocation** (₹{investment:,.0f}/month total)\n\n"
                    f"{alloc_text}\n\n"
                    f"📌 **Strategy:** {plan or 'Diversified growth approach'}\n"
                    f"⚖️ **Risk Profile:** {risk_tolerance.title()}"
                )
            elif savings > 0:
                return (
                    f"Based on your ₹{savings:,.0f} monthly surplus and **{segment or 'your financial profile'}**, "
                    f"here's a suggested starting allocation:\n\n"
                    f"- **Emergency Fund** (until 6 months built): ₹{int(savings * 0.4):,.0f}/month\n"
                    f"- **Nifty 50 Index Fund SIP**: ₹{int(savings * 0.35):,.0f}/month\n"
                    f"- **Debt Fund / PPF**: ₹{int(savings * 0.25):,.0f}/month\n\n"
                    f"Visit the Analysis page to get a fully personalized AI-generated plan."
                )

        # SIP amount queries
        if any(kw in msg_lower for kw in ["sip", "how much should i invest", "invest monthly"]):
            return (
                f"💡 **Your Recommended SIP Amount: ₹{investment:,.0f}/month**\n\n"
                f"This is based on your:\n"
                f"- Monthly Income: ₹{income:,.0f}\n"
                f"- Monthly Surplus: ₹{savings:,.0f}\n"
                f"- Financial Segment: {segment or 'Stable Builder'}\n"
                f"- Risk Tolerance: {risk_tolerance.title()}\n\n"
                f"{'📈 **Strategy:** ' + plan if plan else ''}\n\n"
                f"As a rule of thumb, invest **at least 20%** of your income. "
                f"Your current surplus allows up to ₹{int(savings * 0.8):,.0f}/month while keeping a buffer."
            )

        # Generic personal query fallback using their real data
        return (
            f"Based on your financial profile:\n\n"
            f"📊 **Your Snapshot:**\n"
            f"- Income: ₹{income:,.0f}/month\n"
            f"- Expenses: ₹{expenses:,.0f}/month\n"
            f"- Surplus: ₹{savings:,.0f}/month\n"
            f"- Segment: **{segment or 'Being analyzed'}**\n"
            f"- Health Score: **{health_score}/100**\n"
            f"- Recommended SIP: **₹{investment:,.0f}/month**\n\n"
            f"{'📌 ' + plan if plan else 'Complete your profile in Analysis for a full personalized plan.'}\n\n"
            f"Feel free to ask a more specific question — e.g., 'What is my 5-year growth forecast?' or 'How should I allocate my savings?'"
        )
