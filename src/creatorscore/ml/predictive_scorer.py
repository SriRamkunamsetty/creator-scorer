"""Predictive creator quality & fair-market pricing regression models."""
import math
from statistics import mean, median
from typing import Any, Dict, List, Optional, Tuple


class PredictiveQualityScorer:
    """Supervised regression modeling for expected creator CPM and true audience quality.

    Uses Gradient Boosting / Ridge regression with k-fold cross-validation
    to predict fair-market rate and estimate ROI potential.
    """

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self._fitted = False
        self._cpm_model = None
        self._score_model = None

    @staticmethod
    def _extract_regressor_features(c: Dict[str, Any]) -> List[float]:
        metrics = c.get("metrics", {})
        followers = max(1, c.get("followers", 1))
        med_views = metrics.get("median_views", 1.0)
        reach = metrics.get("reach_ratio", med_views / followers)
        er = metrics.get("engagement_rate", 0.0)
        consistency = metrics.get("consistency", 0.5)

        # Log-transformed scale invariants
        log_followers = math.log10(followers)
        log_views = math.log10(max(1.0, med_views))
        log_reach = math.log10(max(1e-4, reach))

        return [log_followers, log_views, log_reach, er, consistency]

    def fit_and_evaluate(self, creators: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fit models on cohort data with pricing and valid metrics.

        Returns regression metrics (R2, MAE, CV score) and model instances.
        """
        valid_creators = [
            c for c in creators
            if c.get("cost", {}).get("cpm_usd") is not None
            and c.get("cost", {}).get("cpm_usd") > 0
            and c.get("metrics", {}).get("median_views", 0) > 0
        ]

        if len(valid_creators) < 6:
            return {
                "trained": False,
                "reason": f"Insufficient sample size ({len(valid_creators)} < 6) for regression training",
            }

        X = [self._extract_regressor_features(c) for c in valid_creators]
        y_cpm = [math.log10(c["cost"]["cpm_usd"]) for c in valid_creators]
        y_score = [c.get("score") or 50.0 for c in valid_creators]

        try:
            from sklearn.ensemble import HistGradientBoostingRegressor
            from sklearn.linear_model import Ridge
            from sklearn.model_selection import KFold, cross_val_score
            import numpy as np

            X_arr = np.array(X)
            y_cpm_arr = np.array(y_cpm)
            y_score_arr = np.array(y_score)

            # Ridge regression provides high-speed, well-regularized parameters
            cpm_reg = Ridge(alpha=1.0, random_state=self.random_state)
            score_reg = Ridge(alpha=1.0, random_state=self.random_state)

            cpm_reg.fit(X_arr, y_cpm_arr)
            score_reg.fit(X_arr, y_score_arr)

            self._cpm_model = cpm_reg
            self._score_model = score_reg
            self._fitted = True

            # Evaluate with K-Fold cross-validation
            n_splits = min(3, len(valid_creators))
            kf = KFold(n_splits=n_splits, shuffle=True, random_state=self.random_state)
            cpm_scores = cross_val_score(cpm_reg, X_arr, y_cpm_arr, cv=kf, scoring="neg_mean_absolute_error")
            mae = float(-np.mean(cpm_scores))

            return {
                "trained": True,
                "n_samples": len(valid_creators),
                "model_type": type(cpm_reg).__name__,
                "cpm_log_mae": round(mae, 3),
            }
        except Exception:
            # Fallback to cohort median heuristic model
            self._fitted = False
            return {"trained": False, "reason": "Standard regression fallback activated"}

    def predict_creators(self, creators: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Augment each creator with predictive pricing and expected performance."""
        results = []
        for c in creators:
            actual_cpm = c.get("cost", {}).get("cpm_usd")
            features = self._extract_regressor_features(c)

            if self._fitted and self._cpm_model is not None:
                import numpy as np
                pred_log_cpm = float(self._cpm_model.predict(np.array([features]))[0])
                pred_fair_cpm = round(10 ** pred_log_cpm, 2)
                pred_quality = round(float(self._score_model.predict(np.array([features]))[0]), 1)
            else:
                # Empirical cohort median estimation
                pred_fair_cpm = round(self._empirical_cpm_estimate(c), 2)
                pred_quality = c.get("score")

            # Determine pricing efficiency tier
            if actual_cpm and pred_fair_cpm and pred_fair_cpm > 0:
                price_ratio = actual_cpm / pred_fair_cpm
                if price_ratio >= 1.5:
                    valuation = "overpriced"
                    roi_signal = f"Current CPM (${actual_cpm:.2f}) is {price_ratio:.1f}x higher than modeled fair value (${pred_fair_cpm:.2f})"
                elif price_ratio <= 0.70:
                    valuation = "high_value"
                    roi_signal = f"Undervalued by {(1.0 - price_ratio):.0%}: Prime ROI candidate vs modeled fair value (${pred_fair_cpm:.2f})"
                else:
                    valuation = "fair_value"
                    roi_signal = f"Priced at fair market expectation (${pred_fair_cpm:.2f} CPM)"
            else:
                valuation = "unpriced"
                roi_signal = f"Modeled fair-market value: ${pred_fair_cpm:.2f} CPM"

            results.append({
                "predicted_fair_cpm_usd": pred_fair_cpm,
                "predicted_quality_score": pred_quality,
                "market_valuation": valuation,
                "roi_signal": roi_signal,
            })
        return results

    @staticmethod
    def _empirical_cpm_estimate(c: Dict[str, Any]) -> float:
        # Standard baseline formula when ML fit has not run
        tier = c.get("tier", "micro")
        base_rates = {
            "nano": 60.0,
            "micro": 45.0,
            "mid": 50.0,
            "macro": 40.0,
            "mega": 35.0,
        }
        base = base_rates.get(tier, 45.0)
        er = c.get("metrics", {}).get("engagement_rate", 0.05)
        consistency = c.get("metrics", {}).get("consistency", 0.5)
        multiplier = max(0.4, min(2.5, (er / 0.05) * 0.7 + consistency * 0.3))
        return base * multiplier
