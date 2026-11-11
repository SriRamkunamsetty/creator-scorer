# CreatorScore Enterprise: AI/ML Creator Quality Scoring & Production Platform

[![CI Pipeline](https://github.com/SriRamkunamsetty/creator-scorer/actions/workflows/ci.yml/badge.svg)](https://github.com/SriRamkunamsetty/creator-scorer/actions/workflows/ci.yml)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](Dockerfile)
[![Kubernetes](https://img.shields.io/badge/kubernetes-production-326ce5.svg)](deploy/k8s/)
[![Helm](https://img.shields.io/badge/helm-chart_v1.0.0-0f1689.svg)](deploy/helm/creatorscore/)
[![Terraform](https://img.shields.io/badge/terraform-IaC-844fba.svg)](deploy/terraform/)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](pyproject.toml)

**Who is worth the fee?** A production-grade AI/ML platform and microservice that ranks social media creators against empirical cohort distributions, runs multivariate anomaly detection (Isolation Forest), performs NLP bot-network and astroturfing analysis (Shannon entropy + TF-IDF semantic clustering), predicts fair-market pricing (CPE/CPM), provides transparent Explainable AI (XAI) score attributions, and automatically monitors cohort drift (Population Stability Index).

---

## Architecture Overview

```
                         ┌──────────────────────────────────────────────────────────┐
                         │               KUBERNETES INGRESS / TLS                   │
                         └────────────────────────────┬─────────────────────────────┘
                                                      │
                                                      ▼
                         ┌──────────────────────────────────────────────────────────┐
                         │             FASTAPI ENTERPRISE ASGI SERVICE              │
                         │   • Rate Limiting    • Prometheus Metrics (/metrics)     │
                         │   • Security Headers • Request ID Tracing                │
                         └──────┬─────────────────────┬──────────────────────┬──────┘
                                │                     │                      │
       ┌────────────────────────┴───────┐             │           ┌──────────┴───────────────────────┐
       ▼                                ▼             ▼           ▼                                  ▼
┌──────────────┐                 ┌─────────────┐ ┌─────────┐ ┌──────────────────┐            ┌──────────────────┐
│  Classical   │                 │ Multivariate│ │Predictve│ │ NLP Bot Detector │            │  Drift Detector  │
│Cohort Scoring│                 │  Isolation  │ │  Ridge  │ │ • Shannon Entropy│            │ • Population     │
│  Percentiles │                 │   Forest    │ │Regressor│ │ • TF-IDF Cosine  │            │   Stability (PSI)│
│  • Micro     │                 │ • Reach Dev │ │ • Fair  │ │   Clustering     │            │ • Kolmogorov-    │
│  • Mid       │                 │ • ER Volat. │ │   CPM   │ │ • Token Diversity│            │   Smirnov (KS)   │
│  • Macro     │                 │ • Outliers  │ │ • ROI   │ │ • Emoji Density  │            │ • Alerting       │
└──────┬───────┘                 └──────┬──────┘ └────┬────┘ └────────┬─────────┘            └──────────────────┘
       │                                │             │               │
       └────────────────────────┬───────┴─────────────┴───────────────┘
                                │
                                ▼
                 ┌─────────────────────────────┐
                 │    EXPLAINABLE AI (XAI)     │
                 │   Feature Waterfall Score   │
                 │   Attribution Breakdown     │
                 └──────────────┬──────────────┘
                                │
       ┌────────────────────────┴───────────────────────┐
       ▼                                                ▼
┌──────────────────────────────┐        ┌───────────────────────────────┐
│     JSON REST API /v1        │        │     CONTAINER & DEVOPS        │
│ • /healthz  • /readyz        │        │ • Docker (Multi-stage nonroot)│
│ • /metrics  • /api/v1/score  │        │ • Docker Compose (PG+Redis)   │
│ • /api/v1/analyze/comments   │        │ • Helm Chart & K8s (HPA, PDB) │
│ • /api/v1/analyze/drift      │        │ • Terraform Cloud EKS+RDS     │
└──────────────────────────────┘        └───────────────────────────────┘
```

---

## Machine Learning & AI Capabilities

1. **Multivariate Anomaly Detection (`CreatorAnomalyDetector`)**:
   - Trains an **Isolation Forest** on multivariate feature vectors: $\log_{10}(\text{reach\_ratio})$, $\text{engagement\_rate}$, $\text{consistency}$, $\text{follower\_volatility}$, and $\text{comment\_to\_like\_ratio}$.
   - Pinpoints the exact feature responsible for outlier classification via robust MAD cohort attribution.

2. **NLP Semantic Bot & Astroturfing Detection (`NLPBotDetector`)**:
   - Calculates **Lexical Shannon Entropy** ($H(X) = -\sum P(w)\log_2 P(w)$) to measure vocabulary information density.
   - Performs **subword $n$-gram TF-IDF cosine similarity clustering** to identify automated bot comment networks.
   - Computes Type-Token Ratio (TTR) and emoji spam density to produce a calibrated **Bot Probability Score** ($0.0 - 1.0$).

3. **Predictive Fair-Market Pricing Regressor (`PredictiveQualityScorer`)**:
   - Supervised Ridge regression with $k$-fold cross-validation predicting expected fair-market CPM and CPE.
   - Categorizes creator pricing efficiency into **High ROI Candidate** ($< 0.7\times$ fair value), **Fair Value**, or **Overpriced** ($> 1.5\times$ fair value).

4. **Explainable AI (XAI) Feature Attribution (`ModelExplainer`)**:
   - Decomposes every score into an additive waterfall:
     $$\text{Score} = \text{Engagement Pts} + \text{Reach Pts} + \text{Consistency Pts} - \text{Risk Penalty} - \text{ML Anomaly Deduction} - \text{NLP Bot Deduction}$$

5. **Dataset & Distribution Drift Monitor (`DriftDetector`)**:
   - Calculates **Population Stability Index (PSI)** between training cohorts and incoming production traffic:
     $$PSI = \sum_{i} (T_i - B_i) \times \ln\left(\frac{T_i}{B_i}\right)$$
   - Runs two-sample **Kolmogorov-Smirnov (KS)** tests to alert when creator demographics or engagement distributions shift.

---

## Production DevOps & Cloud Infrastructure

### Docker & Docker Compose
- **Multi-stage, Non-root Container (`Dockerfile`)**:
  - Based on `python:3.12-slim` with dedicated user `appuser` (UID 10001).
  - Security-hardened: no root privileges, `tini` init process, health checks.
- **Microservices Stack (`docker-compose.yml`)**:
  - `creatorscore-api`: FastAPI production microservice
  - `postgres`: PostgreSQL 16 database with persistent volume and health check
  - `redis`: Redis 7 caching tier
  - `prometheus`: Prometheus v2.51 scraper for `/metrics`
  - `grafana`: Pre-configured Grafana monitoring dashboard

```bash
docker compose up -d
```

### Kubernetes (K8s) Production Manifests (`deploy/k8s/`)
- `namespace.yaml`: Isolated `creatorscore` namespace.
- `deployment.yaml`: 3 replicas with rolling updates, liveness/readiness/startup probes, resource limits, and non-root execution.
- `hpa.yaml`: Horizontal Pod Autoscaler scaling from 2 to 10 pods based on CPU (70%) and Memory (80%).
- `pdb.yaml`: Pod Disruption Budget ensuring high availability during node drains.
- `networkpolicy.yaml`: Zero-trust network segmentation.
- `ingress.yaml`: TLS ingress with cert-manager support and rate limiting.

### Helm Chart (`deploy/helm/creatorscore/`)
```bash
helm lint deploy/helm/creatorscore
helm upgrade --install creatorscore deploy/helm/creatorscore \
  --namespace creatorscore \
  --create-namespace \
  --values deploy/helm/creatorscore/values.yaml
```

### Terraform Infrastructure as Code (`deploy/terraform/`)
Provisions production AWS cloud infrastructure:
- Multi-AZ VPC with public and private subnets across 3 Availability Zones.
- Managed **AWS EKS Kubernetes Cluster** (v1.30) with separate compute and ML-inference node groups.
- High-Availability **AWS RDS PostgreSQL 16** with Multi-AZ replication and encryption at rest.
- S3 Bucket with AES-256 encryption for ML model artifacts and drift logs.

---

## Enterprise CI/CD Pipelines

GitHub Actions workflows located in `.github/workflows/`:
1. **`ci.yml` (Continuous Integration)**:
   - Ruff linting and Black formatting verification.
   - Bandit automated security and vulnerability analysis.
   - Multi-version matrix test suite (Python 3.10, 3.11, 3.12) with code coverage.
   - Docker container build and Trivy vulnerability scan.
   - Helm chart syntax and template linting.
2. **`cd.yml` (Continuous Deployment)**:
   - Automated semantic release builds.
   - Multi-arch container publish (`linux/amd64`, `linux/arm64`) to GitHub Container Registry (`ghcr.io`).
   - Rolling deployment to Kubernetes cluster using Helm.
3. **`ml_eval.yml` (ML Drift Benchmark)**:
   - Scheduled weekly audit monitoring population stability (PSI) and regression accuracy.

---

## Quick Start

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/SriRamkunamsetty/creator-scorer.git
cd creator-scorer

# Install with all enterprise ML & API dependencies
pip install -e ".[all]"
```

### 2. Run the Machine-Learning CLI
```bash
# Score creators with ML anomaly detection and fair pricing models
creatorscore score --demo --ml --top 10

# Output structured JSON with complete ML insights & XAI waterfall
creatorscore score --demo --ml --format json
```

### 3. Launch the Production FastAPI Service
```bash
# Start FastAPI ASGI server with Swagger UI at http://127.0.0.1:8000/docs
creatorscore serve --demo --api --port 8000
```

### 4. Run the Full Test Suite
```bash
python -m unittest discover -s tests -v
```

---

## REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/healthz` | Kubernetes liveness probe |
| `GET` | `/readyz` | Kubernetes readiness probe (verifies DB) |
| `GET` | `/metrics` | Prometheus metrics scrape target |
| `GET` | `/api/v1/creators` | List scored creators (with optional `enable_ml=true`) |
| `POST` | `/api/v1/analyze/comments` | NLP Shannon entropy & semantic bot cluster analysis |
| `POST` | `/api/v1/analyze/drift` | Population Stability Index (PSI) & KS drift computation |
| `GET` | `/api/v1/models/status` | ML model registry metadata and health status |

---

## Contributors

- **SriRamKunamsetty** ([@SriRamKunamsetty](https://github.com/SriRamKunamsetty)) - `mohansriramkunamsetty@gmail.com`
