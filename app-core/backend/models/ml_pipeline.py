"""ML pipeline for micro-investing segmentation - ported from notebook."""

import os
import json
import numpy as np
import joblib
from typing import Dict, Optional, Tuple, List, Any
from numpy import ndarray

from utils.feature_engineering import build_extended_features
from utils.financial_diagnosis import compute_financial_metrics, classify_financial_state, FinancialState
from utils.goal_allocation import compute_goal_based_allocation

# Rule-based thresholds
EXTREME_SURPLUS_THRESHOLD = 0.50
HIGH_INCOME_THRESHOLD = 500000
VERY_HIGH_SURPLUS_RATIO = 0.80


class MicroInvestmentAssistant:
    """ML inference class for user segmentation with financial intelligence."""

    def __init__(self, artifacts_dir: str = "./artifacts"):
        self.artifacts_dir = artifacts_dir
        self._load_artifacts()

    def _load_artifacts(self):
        """Load all ML artifacts at startup."""
        self.imputer = joblib.load(os.path.join(self.artifacts_dir, "imputer.pkl"))
        self.scaler = joblib.load(os.path.join(self.artifacts_dir, "robust_scaler.pkl"))
        self.kmeans = joblib.load(os.path.join(self.artifacts_dir, "kmeans_model.pkl"))

        with open(os.path.join(self.artifacts_dir, "segment_map.json")) as f:
            self.segment_map = json.load(f)
            self.segment_map = {int(k): v for k, v in self.segment_map.items()}

        with open(os.path.join(self.artifacts_dir, "feature_order.json")) as f:
            self.feature_order = json.load(f)

    def _preprocess(self, features: list[float]) -> ndarray:
        """Apply imputer and scaler to feature vector."""
        row = np.array([features])
        row_imp = self.imputer.transform(row)
        row_sc = self.scaler.transform(row_imp)
        return row_sc

    def _apply_rule_overrides(
        self,
        cluster_id: int,
        savings: float,
        income: float,
        savings_ratio: float,
        base_multiplier: float
    ) -> Tuple[Optional[Dict], List[str]]:
        """Apply rule-based overrides for extreme cases."""
        reasons = []
        override = None

        # EXTREME SURPLUS CASE
        if income >= HIGH_INCOME_THRESHOLD and savings_ratio >= EXTREME_SURPLUS_THRESHOLD:
            if savings_ratio >= VERY_HIGH_SURPLUS_RATIO:
                equity_allocation = 0.40
                direct_stocks = 0.20
                debt_liquid = 0.15
                gold = 0.10
                alternatives = 0.10
                skill_business = 0.05

                override = {
                    "name": "Wealth Accelerator",
                    "plan": f"40% Equity + 20% Direct Stocks + 15% Debt/Liquid + 10% Gold + 10% Alternatives + 5% Skill/Business",
                    "multiplier": min(0.85, savings_ratio - 0.10),
                    "investment_appetite": "Very High",
                    "allocation_details": {
                        "equity_40pct": f"Index funds (Nifty 50, Midcap) + Flexi-cap + US ETFs",
                        "direct_stocks_20pct": "High-growth sectors (AI, infra, energy, banking)",
                        "debt_liquid_15pct": "Liquid funds + Corporate bonds",
                        "gold_10pct": "Sovereign Gold Bonds or Gold ETFs",
                        "alternatives_10pct": "Crypto (BTC/ETH), smallcases, or startup equity",
                        "skill_business_5pct": "Courses, certifications, side business"
                    }
                }
                reasons.append(f"EXTREME SURPLUS: {savings_ratio*100:.1f}% savings ratio with {income:,.0f} income. Activating wealth accelerator mode.")
            else:
                override = {
                    "name": "Aggressive Growth",
                    "plan": "50% Equity SIP + 25% Direct Stocks + 15% Debt + 10% Gold/Alternatives",
                    "multiplier": min(0.70, savings_ratio - 0.05),
                    "investment_appetite": "High",
                    "allocation_details": {
                        "equity_50pct": "Large-cap + Mid-cap index funds + Sectoral funds",
                        "direct_stocks_25pct": "Quality growth stocks in your domain",
                        "debt_15pct": "Corporate bond funds + FD ladder",
                        "gold_alt_10pct": "Gold ETF + Small crypto allocation"
                    }
                }
                reasons.append(f"HIGH SURPLUS: {savings_ratio*100:.1f}% savings ratio. Optimizing for wealth compounding.")

        # MIDDLE CASE
        elif income >= HIGH_INCOME_THRESHOLD * 0.5 and savings_ratio >= 0.40:
            override = {
                "name": "Balanced Builder",
                "plan": "45% Equity + 30% Debt + 15% Gold/Alternatives + 10% Emergency Buffer",
                "multiplier": min(0.55, savings_ratio),
                "investment_appetite": "Medium-High",
                "allocation_details": {
                    "equity_45pct": "Balanced advantage funds + Index funds",
                    "debt_30pct": "Debt mutual funds + PPF",
                    "gold_alt_15pct": "Gold + International diversification",
                    "emergency_10pct": "Build 6-month emergency fund first"
                }
            }
            reasons.append(f"STRONG POSITION: {savings_ratio*100:.1f}% savings ratio with solid income.")

        return override, reasons

    def recommend(
        self, features: list[float], savings: float, income: float
    ) -> tuple[dict, Optional[int], Optional[float]]:
        """Generate recommendation with rule overrides and financial intelligence."""
        X_sc = self._preprocess(features)
        cluster_id = int(self.kmeans.predict(X_sc)[0])

        savings_ratio = savings / (income + 1e-9) if income > 0 else 0

        reasons = []
        multiplier_override = None
        segment_override = None

        # Safety guardrails for negative savings
        if savings <= 0 or savings_ratio < 0.10:
            if savings <= 0:
                reasons.append("CRITICAL: Negative/Zero savings. Forcing emergency fund mode.")
            else:
                reasons.append("WARNING: Savings ratio under 10%. Capping risk.")

            stressed_cluster = min(
                self.segment_map.keys(),
                key=lambda c: self.segment_map[c]["multiplier"]
            )
            segment_override = stressed_cluster
            multiplier_override = 0.0 if savings <= 0 else 0.1

        # Apply rule-based overrides
        if not segment_override:
            override, override_reasons = self._apply_rule_overrides(
                cluster_id, savings, income, savings_ratio,
                self.segment_map[cluster_id]["multiplier"]
            )
            if override:
                reasons.extend(override_reasons)
                seg_info = override
                multiplier = override["multiplier"]
            else:
                seg_info = self.segment_map[cluster_id].copy()
                multiplier = multiplier_override if multiplier_override is not None else seg_info["multiplier"]
        else:
            seg_info = self.segment_map[segment_override].copy()
            multiplier = multiplier_override if multiplier_override is not None else seg_info["multiplier"]

        cluster_used = segment_override if segment_override is not None else cluster_id
        suggested_investment = round(savings * multiplier, 2)

        # Adjust for high income
        if income >= HIGH_INCOME_THRESHOLD and suggested_investment < income * 0.3:
            suggested_investment = round(income * 0.4, 2)
            if not any("minimum" in r.lower() for r in reasons):
                reasons.append(f"Adjusted for high income: Minimum {suggested_investment:,.0f}/month recommended.")

        recommendation = {
            "cluster_id": cluster_used,
            "user_segment": seg_info["name"],
            "recommended_plan": seg_info["plan"],
            "suggested_monthly_investment": suggested_investment,
            "investment_appetite": seg_info["investment_appetite"],
            "reason_codes": reasons,
            "multiplier": multiplier,
            "savings_ratio": round(savings_ratio, 3),
            "income_level": "high" if income >= HIGH_INCOME_THRESHOLD else "normal",
            "allocation_details": seg_info.get("allocation_details", {})
        }

        return recommendation, segment_override, multiplier_override

    def confidence(self, features: list[float]) -> float:
        """Compute prediction confidence based on cluster distance."""
        X_sc = self._preprocess(features)
        dists = self.kmeans.transform(X_sc)[0]
        sorted_dists = np.sort(dists)

        if len(sorted_dists) < 2:
            return 0.5

        best = sorted_dists[0]
        second = sorted_dists[1]
        conf = second / (best + second + 1e-9)
        return float(np.clip(conf, 0.0, 1.0))

    def get_model_info(self) -> dict:
        """Return model metadata."""
        return {
            "model_name": "MicroInvestment KMeans Segmentation with Rule Overrides",
            "version": "2.0.0",
            "segment_labels": [
                self.segment_map[k]["name"] for k in sorted(self.segment_map.keys())
            ],
            "features": self.feature_order,
            "n_clusters": len(self.segment_map),
            "rule_overrides": [
                "Wealth Accelerator (extreme surplus)",
                "Aggressive Growth (high surplus)",
                "Balanced Builder (moderate surplus)"
            ]
        }
