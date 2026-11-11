"""Tests for FastAPI enterprise endpoints and security posture."""
import unittest
from fastapi.testclient import TestClient

from creatorscore.api.app import create_app
from creatorscore.db import connect
from creatorscore.sample_data import seed_all


class TestFastAPIEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = connect()
        seed_all(cls.conn)
        cls.app = create_app(db_target=":memory:")
        # Seed the app's in-memory db
        seed_all(connect(":memory:"))
        cls.client = TestClient(cls.app)

    def test_healthz_and_readyz(self):
        res = self.client.get("/healthz")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["database"], "connected")

        # Readyz
        res_ready = self.client.get("/readyz")
        self.assertEqual(res_ready.status_code, 200)
        self.assertEqual(res_ready.json()["status"], "ready")

    def test_security_headers_and_tracing(self):
        res = self.client.get("/healthz")
        self.assertEqual(res.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(res.headers.get("X-Frame-Options"), "DENY")
        self.assertIn("X-Request-ID", res.headers)
        self.assertIn("X-Process-Time-Ms", res.headers)
        self.assertIn("default-src 'none'", res.headers.get("Content-Security-Policy", ""))

    def test_metrics_endpoint(self):
        # Trigger requests first
        self.client.get("/healthz")
        res = self.client.get("/metrics")
        self.assertEqual(res.status_code, 200)
        text = res.text
        self.assertIn("creatorscore_http_requests_total", text)
        self.assertIn("creatorscore_predictions_total", text)
        self.assertIn("creatorscore_anomalies_detected_total", text)

    def test_models_status_endpoint(self):
        res = self.client.get("/api/v1/models/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["system_status"], "operational")
        self.assertEqual(len(data["models_loaded"]), 4)

    def test_analyze_comments_endpoint(self):
        payload = {
            "comments": [
                "Great cinematography and direction!",
                "Great cinematography and direction!",
                "Loved the editing pacing in this video.",
                "Subscribed for more awesome content.",
            ]
        }
        res = self.client.post("/api/v1/analyze/comments", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["evaluable"])
        self.assertIn("bot_probability", data)

    def test_analyze_drift_endpoint(self):
        payload = {
            "baseline_values": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "target_values": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "bins": 3,
        }
        res = self.client.post("/api/v1/analyze/drift", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["evaluable"])
        self.assertEqual(data["drift_level"], "negligible")


if __name__ == "__main__":
    unittest.main()
