"""Comprehensive tests for CreatorScore AI/ML components."""
import unittest
from creatorscore.db import connect
from creatorscore.sample_data import seed_all
from creatorscore.creators import score_creators
from creatorscore.ml.nlp_bot_detector import NLPBotDetector
from creatorscore.ml.anomaly_detector import CreatorAnomalyDetector
from creatorscore.ml.predictive_scorer import PredictiveQualityScorer
from creatorscore.ml.explainability import ModelExplainer
from creatorscore.ml.drift import DriftDetector


class TestMLComponents(unittest.TestCase):
    def setUp(self):
        self.conn = connect()
        seed_all(self.conn)
        self.creators = score_creators(self.conn)

    def test_nlp_bot_detection_natural_vs_bot_farm(self):
        detector = NLPBotDetector(min_sample_size=4)

        # 1. Natural diverse comments
        natural_comments = [
            "The cinematography at 02:45 was absolutely breathtaking!",
            "I love how you explained the lighting contrast in this scene.",
            "Can you do a follow-up video detailing the sound design techniques?",
            "Subscribed! Really helpful advice for independent filmmakers.",
            "This perspective completely shifted how I view classic film editing.",
        ]
        nat_res = detector.analyze_comments(natural_comments)
        self.assertTrue(nat_res["evaluable"])
        self.assertLess(nat_res["bot_probability"], 0.25)
        self.assertEqual(len(nat_res["signals"]), 0)

        # 2. Simulated bot farm comments (astroturf network)
        bot_comments = [
            "Nice video follow me please",
            "Nice video follow me please",
            "Great video bro follow me back",
            "Nice video follow me please bro",
            "🔥🔥🔥🔥🔥🔥",
            "Nice video follow me please",
        ]
        bot_res = detector.analyze_comments(bot_comments)
        self.assertTrue(bot_res["evaluable"])
        self.assertGreaterEqual(bot_res["bot_probability"], 0.40)
        sig_names = [s["name"] for s in bot_res["signals"]]
        self.assertTrue(any(k in sig_names for k in ("semantic_redundancy", "low_lexical_entropy", "emoji_spam_density")))

    def test_nlp_insufficient_sample(self):
        detector = NLPBotDetector(min_sample_size=5)
        res = detector.analyze_comments(["One comment", "Second comment"])
        self.assertFalse(res["evaluable"])
        self.assertIsNone(res["bot_probability"])

    def test_multivariate_anomaly_detector(self):
        detector = CreatorAnomalyDetector()
        results = detector.fit_predict(self.creators)

        self.assertEqual(len(results), len(self.creators))
        # Creator 05 and Creator 17 are synthetic bad actors with collapsed reach and ER
        sc_map = {c["handle"]: results[i] for i, c in enumerate(self.creators)}
        self.assertTrue(sc_map["creator_05"]["is_anomaly"])
        self.assertGreater(sc_map["creator_05"]["anomaly_score"], 0.40)
        self.assertIn("Log reach ratio", sc_map["creator_05"]["details"])

    def test_predictive_quality_and_fair_pricing(self):
        scorer = PredictiveQualityScorer()
        train_res = scorer.fit_and_evaluate(self.creators)
        self.assertTrue(train_res["trained"])

        predictions = scorer.predict_creators(self.creators)
        self.assertEqual(len(predictions), len(self.creators))

        c05_idx = next(i for i, c in enumerate(self.creators) if c["handle"] == "creator_05")
        c05_pred = predictions[c05_idx]
        # Creator 05 has astronomical CPM ($2000+) vs synthetic followers, should be overpriced
        self.assertEqual(c05_pred["market_valuation"], "overpriced")
        self.assertGreater(c05_pred["predicted_fair_cpm_usd"], 0)

    def test_xai_model_explainer(self):
        creator = self.creators[0]
        explanation = ModelExplainer.explain_creator_score(
            creator,
            anomaly_info={"is_anomaly": False, "anomaly_score": 0.0},
            nlp_info={"evaluable": True, "bot_probability": 0.05},
        )
        self.assertTrue(explanation["explainable"])
        self.assertIn("waterfall", explanation)
        self.assertGreater(len(explanation["waterfall"]), 0)
        self.assertEqual(explanation["final_score"], creator["score"])

    def test_drift_detector_psi_and_ks(self):
        baseline = [10.0, 12.0, 14.0, 15.0, 18.0, 20.0, 22.0, 25.0, 28.0, 30.0]
        # Exact same distribution
        target_stable = [10.5, 11.8, 14.2, 15.1, 17.9, 19.8, 22.1, 24.9, 27.8, 30.2]
        res_stable = DriftDetector.calculate_psi(baseline, target_stable)
        self.assertTrue(res_stable["evaluable"])
        self.assertEqual(res_stable["drift_level"], "negligible")

        # Dramatically shifted distribution
        target_drifted = [80.0, 85.0, 90.0, 92.0, 95.0, 100.0, 110.0, 120.0]
        res_drift = DriftDetector.calculate_psi(baseline, target_drifted)
        self.assertTrue(res_drift["evaluable"])
        self.assertEqual(res_drift["drift_level"], "significant")

        # KS test
        ks_res = DriftDetector.kolmogorov_smirnov_2sample(baseline, target_drifted)
        self.assertTrue(ks_res["evaluable"])
        self.assertEqual(ks_res["distribution_divergence"], "high")


if __name__ == "__main__":
    unittest.main()
