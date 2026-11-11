"""Pydantic v2 schemas for request validation and API responses."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field("healthy", description="Application health status")
    version: str = Field("1.0.0", description="API version")
    database: str = Field("connected", description="Database connection state")
    timestamp_utc: str = Field(..., description="UTC ISO timestamp")


class CommentAnalysisRequest(BaseModel):
    comments: List[str] = Field(..., min_length=1, description="List of comments to evaluate for bot and astroturf activity")


class NLPSignal(BaseModel):
    name: str
    severity: str
    description: str


class NLPMetrics(BaseModel):
    total_comments_sampled: int
    shannon_entropy: float
    type_token_ratio: float
    mean_pairwise_similarity: float
    dense_cluster_ratio: float
    emoji_only_ratio: float


class CommentAnalysisResponse(BaseModel):
    evaluable: bool
    bot_probability: Optional[float] = None
    confidence: str
    metrics: Optional[NLPMetrics] = None
    signals: List[NLPSignal] = []
    details: Optional[str] = None


class DriftAnalysisRequest(BaseModel):
    baseline_values: List[float] = Field(..., min_length=5, description="Historical / reference baseline feature values")
    target_values: List[float] = Field(..., min_length=5, description="Recent / incoming feature values to compare")
    bins: int = Field(5, ge=2, le=20, description="Number of quantile bins for PSI computation")


class DriftAnalysisResponse(BaseModel):
    evaluable: bool
    psi: float
    drift_level: str
    recommended_action: str
    ks_statistic: Optional[float] = None


class MetricsBlock(BaseModel):
    median_views: float
    engagement_rate: float
    reach_ratio: float
    consistency: float


class PercentilesBlock(BaseModel):
    engagement: Optional[float] = None
    reach: Optional[float] = None
    cohort: str


class SignalDetail(BaseModel):
    signal: str
    triggered: bool
    detail: str


class RiskBlock(BaseModel):
    label: str
    score: Optional[float] = None
    signals: List[SignalDetail]
    disclaimer: str


class CostBlock(BaseModel):
    cpm_usd: Optional[float] = None
    cpe_usd: Optional[float] = None


class CreatorResponse(BaseModel):
    handle: str
    platform: str
    tier: str
    category: Optional[str] = None
    followers: int
    n_posts: int
    confidence: str
    metrics: MetricsBlock
    percentiles: PercentilesBlock
    risk: RiskBlock
    cost: CostBlock
    score: Optional[float] = None
    fit: bool
    note: Optional[str] = None
    ml_insights: Optional[Dict[str, Any]] = None


class ModelStatusResponse(BaseModel):
    models_loaded: List[str]
    isolation_forest_contamination: float
    features_monitored: List[str]
    system_status: str
