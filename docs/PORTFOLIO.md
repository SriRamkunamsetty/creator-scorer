# Portfolio notes

A creator-vetting tool that is explicit about what it cannot know: relative scores, heuristic flags, and a refusal rule for small cohorts.

## Bullets you can defend today (each is backed by the test suite or a screenshot in this repo)
- Built an explainable creator-scoring engine: cohort-relative percentiles, weighted heuristic authenticity signals, CPM/CPE, and a rule that withholds the score when fewer than 5 comparable creators exist.
- Engineered an AI/ML detection suite: Multivariate Isolation Forest for anomalous performance vectors, NLP Shannon Entropy and TF-IDF semantic clustering for astroturf bot detection, and an Explainable AI (XAI) waterfall attribution engine.
- Designed a predictive fair-market pricing model: Supervised regression with $k$-fold cross-validation estimating expected creator CPM/CPE and identifying high-ROI vs overpriced creators.
- Built a dataset and cohort drift monitoring pipeline using Population Stability Index (PSI) and two-sample Kolmogorov-Smirnov divergence tests to guard against model decay.
- Architected enterprise cloud infrastructure: Production Dockerfile (multi-stage, non-root `appuser`), full Docker Compose stack (FastAPI, PostgreSQL 16, Redis 7, Prometheus, Grafana), and production Kubernetes manifests & Helm chart with HPA autoscaling, PodDisruptionBudget, and zero-trust NetworkPolicy.
- Authored Terraform IaC provisioning high-availability AWS EKS Kubernetes (v1.30), Multi-AZ RDS PostgreSQL, VPC, and S3 model artifact storage.
- Implemented robust multi-stage CI/CD pipelines in GitHub Actions with Ruff/Black/Bandit security scanning, matrix test coverage across Python 3.10-3.12, container vulnerability scanning with Trivy, and multi-arch GHCR publication with rolling K8s deployment.

## Add these only after you have measured them yourself (do not publish a number you have not measured)
- Scored [N] real creators across [M] platforms; [K] flagged high risk, of which I verified [J] manually.
- Agreement between my manual vetting and the score ranking: [measure it].

## Interview questions this project prepares you for
**How do you score without industry benchmarks?**  
Percentiles within the imported cohort. It's relative by design, and the tool refuses to score a creator whose cohort has fewer than 5 members.

**Can this detect fake followers?**  
No. It surfaces heuristic signals from public numbers (follower jumps, weak reach, duplicate comments) and says they are not proof; a human decides.

**What was a bug you found in your own scoring?**  
The first risk rule flagged the lowest creator in every small cohort. Requiring both bottom decile and under a third of the median fixed it.
