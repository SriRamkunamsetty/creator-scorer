"""CreatorScore Machine Learning & AI package.

Provides:
- NLP comment bot detection & semantic clustering
- Multivariate Isolation Forest anomaly detection
- Predictive creator fair-rate & expected ROI scoring
- Explainable AI (XAI) feature attribution
- Population Stability Index (PSI) & Kolmogorov-Smirnov drift monitoring
"""

from .nlp_bot_detector import NLPBotDetector
from .anomaly_detector import CreatorAnomalyDetector
from .predictive_scorer import PredictiveQualityScorer
from .explainability import ModelExplainer
from .drift import DriftDetector

__all__ = [
    "NLPBotDetector",
    "CreatorAnomalyDetector",
    "PredictiveQualityScorer",
    "ModelExplainer",
    "DriftDetector",
]
