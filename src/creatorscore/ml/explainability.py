"""Explainable AI (XAI) feature attribution and score decomposition."""
from typing import Any, Dict, List, Optional


class ModelExplainer:
    """Provides transparent, feature-level attribution and waterfall decomposition

    for every creator score and risk assessment.
    """

    @staticmethod
    def explain_creator_score(
        creator: Dict[str, Any],
        anomaly_info: Optional[Dict[str, Any]] = None,
        nlp_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate waterfall attribution explaining exact points added and deducted."""
        percentiles = creator.get("percentiles", {})
        metrics = creator.get("metrics", {})
        risk = creator.get("risk", {})

        er_pct = percentiles.get("engagement")
        reach_pct = percentiles.get("reach")
        consistency = metrics.get("consistency", 0.0)
        risk_score = risk.get("score") or 0.0

        if er_pct is None or reach_pct is None:
            return {
                "explainable": False,
                "reason": "Score withheld due to small cohort size",
                "waterfall": [],
                "primary_driver": "insufficient_cohort_data",
            }

        # Calculate positive components (0-100 scale)
        er_points = round(0.40 * er_pct, 1)
        reach_points = round(0.30 * reach_pct, 1)
        consistency_points = round(0.30 * consistency * 100.0, 1)
        raw_quality = er_points + reach_points + consistency_points

        # Calculate heuristic risk deduction
        risk_penalty_pct = 0.50 * risk_score
        risk_points_deducted = round(raw_quality * risk_penalty_pct, 1)

        # ML Anomaly contribution
        anomaly_deducted = 0.0
        if anomaly_info and anomaly_info.get("is_anomaly"):
            anomaly_deducted = round(raw_quality * 0.15 * anomaly_info.get("anomaly_score", 0.5), 1)

        # NLP Bot contribution
        nlp_deducted = 0.0
        if nlp_info and nlp_info.get("evaluable"):
            bot_prob = nlp_info.get("bot_probability", 0.0)
            if bot_prob >= 0.40:
                nlp_deducted = round(raw_quality * 0.20 * bot_prob, 1)

        final_score = max(0.0, round(raw_quality - risk_points_deducted - anomaly_deducted - nlp_deducted, 1))

        # Waterfall steps
        waterfall = [
            {
                "step": "Engagement Percentile",
                "impact": f"+{er_points}",
                "detail": f"{er_pct:.0f}th percentile within {percentiles.get('cohort')}",
            },
            {
                "step": "Reach Percentile",
                "impact": f"+{reach_points}",
                "detail": f"{reach_pct:.0f}th percentile within {percentiles.get('cohort')}",
            },
            {
                "step": "Consistency Factor",
                "impact": f"+{consistency_points}",
                "detail": f"{consistency:.0%} of posts within 0.5x-2x median views",
            },
        ]

        if risk_points_deducted > 0:
            waterfall.append({
                "step": "Authenticity Risk Penalty",
                "impact": f"-{risk_points_deducted}",
                "detail": f"Heuristic risk score {risk_score:.2f} ({risk.get('label')})",
            })

        if anomaly_deducted > 0:
            waterfall.append({
                "step": "Multivariate ML Anomaly Penalty",
                "impact": f"-{anomaly_deducted}",
                "detail": anomaly_info.get("details", "Isolation Forest outlier detected"),
            })

        if nlp_deducted > 0:
            waterfall.append({
                "step": "NLP Bot Comment Penalty",
                "impact": f"-{nlp_deducted}",
                "detail": f"NLP bot probability: {nlp_info.get('bot_probability', 0.0):.1%}",
            })

        # Identify primary positive and negative driver
        positive_drivers = [
            ("Engagement", er_points),
            ("Reach", reach_points),
            ("Consistency", consistency_points),
        ]
        top_pos = max(positive_drivers, key=lambda x: x[1])[0]

        neg_drivers = [
            ("Heuristic Risk", risk_points_deducted),
            ("ML Anomaly", anomaly_deducted),
            ("NLP Bot Signals", nlp_deducted),
        ]
        top_neg = max(neg_drivers, key=lambda x: x[1])
        primary_neg = top_neg[0] if top_neg[1] > 0 else "None"

        return {
            "explainable": True,
            "raw_quality": round(raw_quality, 1),
            "final_score": final_score,
            "waterfall": waterfall,
            "primary_positive_driver": top_pos,
            "primary_negative_driver": primary_neg,
            "total_deductions": round(risk_points_deducted + anomaly_deducted + nlp_deducted, 1),
        }
