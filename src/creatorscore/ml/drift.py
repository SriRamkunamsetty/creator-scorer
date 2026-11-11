"""Dataset & model drift monitoring using Population Stability Index (PSI) and Kolmogorov-Smirnov tests."""
import math
from typing import Any, Dict, List, Tuple


class DriftDetector:
    """Monitors dataset and cohort drift across time:

    - Population Stability Index (PSI)
    - Kolmogorov-Smirnov (KS) distributional divergence
    - Anomaly drift alerts
    """

    @staticmethod
    def calculate_psi(
        baseline: List[float], target: List[float], bins: int = 5
    ) -> Dict[str, Any]:
        """Compute Population Stability Index (PSI) between baseline and incoming cohort."""
        if len(baseline) < 5 or len(target) < 5:
            return {
                "evaluable": False,
                "psi": 0.0,
                "drift_level": "insufficient_data",
                "details": "Need at least 5 samples in both baseline and target cohorts",
            }

        # Calculate quantile bin edges on baseline
        sorted_base = sorted(baseline)
        edges = []
        for i in range(1, bins):
            idx = int(i * len(sorted_base) / bins)
            edges.append(sorted_base[idx])
        edges = sorted(list(set(edges)))  # deduplicate

        if not edges:
            return {"evaluable": False, "psi": 0.0, "drift_level": "none", "details": "Uniform data"}

        # Helper to assign counts to bins
        def get_bin_counts(data: List[float]) -> List[int]:
            counts = [0] * (len(edges) + 1)
            for x in data:
                placed = False
                for b_idx, edge in enumerate(edges):
                    if x <= edge:
                        counts[b_idx] += 1
                        placed = True
                        break
                if not placed:
                    counts[-1] += 1
            return counts

        base_counts = get_bin_counts(baseline)
        target_counts = get_bin_counts(target)

        # Convert to percentages with epsilon smoothing
        eps = 1e-4
        n_base = len(baseline)
        n_target = len(target)

        base_pcts = [(c / n_base) + eps for c in base_counts]
        target_pcts = [(c / n_target) + eps for c in target_counts]

        # Normalize
        base_sum = sum(base_pcts)
        target_sum = sum(target_pcts)
        base_pcts = [p / base_sum for p in base_pcts]
        target_pcts = [p / target_sum for p in target_pcts]

        # Calculate PSI
        psi_val = 0.0
        for b_p, t_p in zip(base_pcts, target_pcts):
            psi_val += (t_p - b_p) * math.log(t_p / b_p)

        psi_val = round(max(0.0, psi_val), 4)

        # Adjust thresholds for small samples to prevent finite-sample discretization noise
        is_small_sample = min(n_base, n_target) < 25
        negligible_limit = 0.20 if is_small_sample else 0.10
        significant_limit = 0.35 if is_small_sample else 0.25

        if psi_val < negligible_limit:
            drift_level = "negligible"
            action = "No action required: cohort distributions remain stable"
        elif psi_val < significant_limit:
            drift_level = "moderate"
            action = "Monitor closely: moderate shift observed in feature distributions"
        else:
            drift_level = "significant"
            action = "Alert: High drift detected! Recalibrate cohort thresholds and retrain ML models"

        return {
            "evaluable": True,
            "psi": psi_val,
            "drift_level": drift_level,
            "recommended_action": action,
            "bin_edges": edges,
        }

    @staticmethod
    def kolmogorov_smirnov_2sample(s1: List[float], s2: List[float]) -> Dict[str, Any]:
        """Calculates 2-sample KS statistic (maximum vertical distance between empirical CDFs)."""
        if not s1 or not s2:
            return {"ks_statistic": 0.0, "evaluable": False}

        all_vals = sorted(list(set(s1 + s2)))
        n1 = len(s1)
        n2 = len(s2)

        s1_sorted = sorted(s1)
        s2_sorted = sorted(s2)

        max_d = 0.0
        for val in all_vals:
            # Empirical CDF 1
            cdf1 = sum(x <= val for x in s1_sorted) / n1
            # Empirical CDF 2
            cdf2 = sum(x <= val for x in s2_sorted) / n2
            d = abs(cdf1 - cdf2)
            if d > max_d:
                max_d = d

        return {
            "evaluable": True,
            "ks_statistic": round(max_d, 4),
            "distribution_divergence": "high" if max_d >= 0.40 else "moderate" if max_d >= 0.20 else "low",
        }
