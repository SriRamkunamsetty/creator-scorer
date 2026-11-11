"""Multivariate anomaly detection for creator performance and engagement profiles."""
import math
from statistics import median
from typing import Any, Dict, List, Optional, Tuple


class CreatorAnomalyDetector:
    """Multivariate Isolation Forest & Robust Outlier Detection for creator metrics.

    Examines joint distribution of:
    - log(reach_ratio)
    - engagement_rate
    - consistency
    - follower_volatility
    - comment_to_like_ratio
    """

    FEATURE_NAMES = [
        "log_reach_ratio",
        "engagement_rate",
        "consistency",
        "follower_volatility",
        "comment_to_like_ratio",
    ]

    def __init__(self, contamination: float = 0.08, random_state: int = 42):
        self.contamination = contamination
        self.random_state = random_state
        self._model = None
        self._fitted = False

    @classmethod
    def extract_features(cls, creator_dict: Dict[str, Any]) -> List[float]:
        """Extract standardized numerical features from creator dict."""
        metrics = creator_dict.get("metrics", {})
        followers = max(1, creator_dict.get("followers", 1))
        median_views = metrics.get("median_views", 1.0)
        reach = metrics.get("reach_ratio", median_views / followers)
        er = metrics.get("engagement_rate", 0.0)
        consistency = metrics.get("consistency", 0.5)

        # Volatility from follower growth if available
        volatility = creator_dict.get("follower_volatility", 0.01)

        # Comments to likes ratio
        c_to_l = metrics.get("comment_to_like_ratio", 0.05)

        log_reach = math.log10(max(1e-5, reach))
        return [log_reach, er, consistency, volatility, c_to_l]

    def fit_predict(self, creators: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fit outlier detector on the cohort and predict anomaly scores."""
        if len(creators) < 4:
            # Insufficient cohort size for multivariate density estimation
            return [
                {
                    "is_anomaly": False,
                    "anomaly_score": 0.0,
                    "confidence": "low",
                    "top_contributing_feature": None,
                    "details": "Cohort size too small for statistical anomaly modeling",
                }
                for _ in creators
            ]

        feature_matrix = [self.extract_features(c) for c in creators]

        try:
            from sklearn.ensemble import IsolationForest
            import numpy as np

            X = np.array(feature_matrix)
            clf = IsolationForest(
                contamination=min(0.25, max(0.02, self.contamination)),
                random_state=self.random_state,
                n_estimators=30,
            )
            clf.fit(X)
            # decision_function gives negative for outliers, positive for inliers
            scores = clf.decision_function(X)
            preds = clf.predict(X)  # -1 for outlier, 1 for inlier
            use_sklearn = True
        except Exception:
            # Fallback to robust MAD-based multivariate distance if scikit-learn is unavailable
            use_sklearn = False
            scores = self._robust_multivariate_fallback(feature_matrix)
            preds = [-1 if s > 2.5 else 1 for s in scores]

        # Calculate per-feature cohort medians and MADs for explanation attribution
        cohort_stats = self._compute_cohort_stats(feature_matrix)

        results = []
        for i, c in enumerate(creators):
            row_features = feature_matrix[i]
            is_outlier = bool(preds[i] == -1)

            # Find top deviating feature
            top_feat, max_dev, feat_detail = self._attribute_deviation(row_features, cohort_stats)

            if use_sklearn:
                # Map raw IsolationForest score (typically -0.3 to 0.3) to 0.0..1.0 anomaly severity
                raw = float(scores[i])
                anomaly_severity = max(0.0, min(1.0, (0.15 - raw) / 0.35))
            else:
                dist = float(scores[i])
                anomaly_severity = max(0.0, min(1.0, dist / 4.0))

            results.append({
                "is_anomaly": bool(is_outlier and anomaly_severity >= 0.40),
                "anomaly_score": round(anomaly_severity, 3),
                "confidence": "high" if len(creators) >= 12 else "medium",
                "top_contributing_feature": top_feat if is_outlier else None,
                "details": feat_detail if is_outlier else "Normal performance distribution relative to cohort",
            })

        return results

    @staticmethod
    def _compute_cohort_stats(matrix: List[List[float]]) -> List[Tuple[float, float]]:
        stats = []
        n_features = len(matrix[0])
        for col_idx in range(n_features):
            vals = [row[col_idx] for row in matrix]
            med = median(vals)
            mad = max(1e-4, median(abs(v - med) for v in vals))
            stats.append((med, mad))
        return stats

    @classmethod
    def _attribute_deviation(
        cls, features: List[float], stats: List[Tuple[float, float]]
    ) -> Tuple[str, float, str]:
        max_z = 0.0
        top_name = cls.FEATURE_NAMES[0]
        direction = "abnormal"

        for idx, (val, (med, mad)) in enumerate(zip(features, stats)):
            robust_z = abs(val - med) / mad
            if robust_z > max_z:
                max_z = robust_z
                top_name = cls.FEATURE_NAMES[idx]
                direction = "lower than normal" if val < med else "higher than normal"

        detail = f"{top_name.replace('_', ' ').capitalize()} is {direction} ({max_z:.1f} MAD from cohort median)"
        return top_name, max_z, detail

    @staticmethod
    def _robust_multivariate_fallback(matrix: List[List[float]]) -> List[float]:
        n_features = len(matrix[0])
        col_stats = []
        for col_idx in range(n_features):
            vals = [row[col_idx] for row in matrix]
            med = median(vals)
            mad = max(1e-4, median(abs(v - med) for v in vals))
            col_stats.append((med, mad))

        distances = []
        for row in matrix:
            z_sq = sum(((row[c] - col_stats[c][0]) / col_stats[c][1]) ** 2 for c in range(n_features))
            distances.append(math.sqrt(z_sq / n_features))
        return distances
