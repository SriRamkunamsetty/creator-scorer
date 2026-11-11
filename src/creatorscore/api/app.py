"""Enterprise-grade FastAPI application for CreatorScore AI/ML & DevOps service."""
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from ..creators import score_creators
from ..db import connect, now_iso
from ..ml.anomaly_detector import CreatorAnomalyDetector
from ..ml.drift import DriftDetector
from ..ml.nlp_bot_detector import NLPBotDetector
from .schemas import (
    CommentAnalysisRequest,
    CommentAnalysisResponse,
    CreatorResponse,
    DriftAnalysisRequest,
    DriftAnalysisResponse,
    HealthResponse,
    ModelStatusResponse,
)

# Prometheus metrics counters in-memory
METRICS = {
    "http_requests_total": 0,
    "predictions_total": 0,
    "anomalies_detected_total": 0,
    "latency_seconds_sum": 0.0,
}


def create_app(db_target: Optional[str] = None) -> FastAPI:
    """Application factory for CreatorScore production service."""
    app = FastAPI(
        title="CreatorScore Enterprise API",
        version="1.0.0",
        description="Explainable cohort-relative creator quality scoring, NLP bot detection, and ML anomaly detection.",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    db_path = db_target or os.environ.get("DATABASE_URL", "creatorscore.db")

    # CORS configuration
    origins = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    # Middleware: Security headers & Request Tracing
    @app.middleware("http")
    async def security_and_tracing_middleware(request: Request, call_next):
        start_time = time.time()
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        METRICS["http_requests_total"] += 1

        response: Response = await call_next(request)

        duration = time.time() - start_time
        METRICS["latency_seconds_sum"] += duration

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{duration * 1000:.2f}"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return response

    def get_db():
        # Per-request connection for safety
        conn = connect(db_path, check_same_thread=False)
        try:
            yield conn
        finally:
            conn.close()

    @app.get("/healthz", response_model=HealthResponse, tags=["Observability"])
    async def health_check():
        """Kubernetes Liveness probe."""
        return {
            "status": "healthy",
            "version": "1.0.0",
            "database": "connected",
            "timestamp_utc": now_iso(),
        }

    @app.get("/readyz", response_model=HealthResponse, tags=["Observability"])
    async def readiness_check():
        """Kubernetes Readiness probe."""
        try:
            conn = connect(db_path, check_same_thread=False)
            conn.execute("SELECT 1").fetchone()
            conn.close()
            return {
                "status": "ready",
                "version": "1.0.0",
                "database": "verified",
                "timestamp_utc": now_iso(),
            }
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Database connectivity failed: {str(exc)}",
            )

    @app.get("/metrics", response_class=PlainTextResponse, tags=["Observability"])
    async def prometheus_metrics():
        """Prometheus metrics endpoint."""
        avg_latency = (
            METRICS["latency_seconds_sum"] / max(1, METRICS["http_requests_total"])
        )
        body = (
            "# HELP creatorscore_http_requests_total Total number of HTTP requests\n"
            "# TYPE creatorscore_http_requests_total counter\n"
            f"creatorscore_http_requests_total {METRICS['http_requests_total']}\n\n"
            "# HELP creatorscore_predictions_total Total creator ML scores computed\n"
            "# TYPE creatorscore_predictions_total counter\n"
            f"creatorscore_predictions_total {METRICS['predictions_total']}\n\n"
            "# HELP creatorscore_anomalies_detected_total Total ML anomalies detected\n"
            "# TYPE creatorscore_anomalies_detected_total counter\n"
            f"creatorscore_anomalies_detected_total {METRICS['anomalies_detected_total']}\n\n"
            "# HELP creatorscore_latency_seconds_avg Average request latency in seconds\n"
            "# TYPE creatorscore_latency_seconds_avg gauge\n"
            f"creatorscore_latency_seconds_avg {avg_latency:.4f}\n"
        )
        return body

    @app.get("/api/v1/creators", response_model=List[CreatorResponse], tags=["Scoring"])
    async def get_scored_creators(
        categories: Optional[str] = Query(None, description="Comma-separated category filters"),
        enable_ml: bool = Query(True, description="Enable ML anomaly and predictive ROI models"),
        db=Depends(get_db),
    ):
        """Retrieve cohort-scored creators, optionally augmented with AI/ML insights."""
        cats = tuple(c.strip() for c in categories.split(",") if c.strip()) if categories else ()
        results = score_creators(db, categories=cats, enable_ml=enable_ml)

        METRICS["predictions_total"] += len(results)
        if enable_ml:
            for r in results:
                if r.get("ml_insights", {}).get("anomaly", {}).get("is_anomaly"):
                    METRICS["anomalies_detected_total"] += 1

        return results

    @app.post("/api/v1/analyze/comments", response_model=CommentAnalysisResponse, tags=["AI & NLP"])
    async def analyze_comments(req: CommentAnalysisRequest):
        """Run NLP Shannon entropy, n-gram TF-IDF clustering, and bot probability analysis."""
        detector = NLPBotDetector(min_sample_size=3)
        res = detector.analyze_comments(req.comments)
        return res

    @app.post("/api/v1/analyze/drift", response_model=DriftAnalysisResponse, tags=["AI & NLP"])
    async def analyze_drift(req: DriftAnalysisRequest):
        """Compute Population Stability Index (PSI) and Kolmogorov-Smirnov test."""
        psi_res = DriftDetector.calculate_psi(req.baseline_values, req.target_values, bins=req.bins)
        ks_res = DriftDetector.kolmogorov_smirnov_2sample(req.baseline_values, req.target_values)
        return {
            "evaluable": psi_res.get("evaluable", False),
            "psi": psi_res.get("psi", 0.0),
            "drift_level": psi_res.get("drift_level", "unknown"),
            "recommended_action": psi_res.get("recommended_action", ""),
            "ks_statistic": ks_res.get("ks_statistic"),
        }

    @app.get("/api/v1/models/status", response_model=ModelStatusResponse, tags=["AI & NLP"])
    async def model_status():
        """Metadata for active machine learning components and monitoring."""
        return {
            "models_loaded": [
                "NLPBotDetector (Shannon Entropy + TF-IDF)",
                "CreatorAnomalyDetector (IsolationForest)",
                "PredictiveQualityScorer (Ridge Regression)",
                "DriftDetector (PSI + Kolmogorov-Smirnov)",
            ],
            "isolation_forest_contamination": 0.08,
            "features_monitored": CreatorAnomalyDetector.FEATURE_NAMES,
            "system_status": "operational",
        }

    return app
