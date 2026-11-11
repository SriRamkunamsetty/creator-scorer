# syntax=docker/dockerfile:1.4
# Stage 1: Build dependencies in isolated environment
FROM python:3.12-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY src/ src/

RUN pip install --upgrade pip setuptools wheel && \
    pip wheel --no-deps --wheel-dir /build/wheels -e .

# Stage 2: Minimal, hardened, non-root runtime container
FROM python:3.12-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    HOST=0.0.0.0 \
    DATABASE_URL=creatorscore.db

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root application user
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/false -m -d /home/appuser appuser

COPY --from=builder /build/wheels /wheels
COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir /wheels/* uvicorn[standard] fastapi scikit-learn numpy pydantic pydantic-settings && \
    pip install --no-cache-dir -e . && \
    rm -rf /wheels

# Ensure app directory permissions
RUN chown -R appuser:appgroup /app /home/appuser

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/healthz || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "uvicorn", "creatorscore.api.app:create_app", "--host", "0.0.0.0", "--port", "8000", "--factory"]
