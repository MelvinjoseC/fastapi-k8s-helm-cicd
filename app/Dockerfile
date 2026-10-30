# ---- Build stage: compile dependencies into an isolated prefix ----
FROM python:3.12-slim AS builder

WORKDIR /build

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user -r requirements.txt


# ---- Runtime stage: minimal distroless-like Debian base, non-root user ----
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="Task API" \
      org.opencontainers.image.description="Cloud-native FastAPI service for Kubernetes CI/CD" \
      org.opencontainers.image.source="https://github.com/MelvinjoseC/fastapi-k8s-helm-cicd" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version="1.1.0" \
      org.opencontainers.image.vendor="MelvinjoseC"

# Install dumb-init for PID 1 signal propagation and zombie reaping, plus runtime libpq
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl dumb-init \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 appgroup \
    && useradd --uid 10001 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy python packages from builder
COPY --from=builder /root/.local /home/appuser/.local
COPY . .

# Set ownership and switch to unprivileged user
RUN chown -R appuser:appgroup /app
USER appuser:appgroup

ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

ENTRYPOINT ["/usr/bin/dumb-init", "--"]

# Scaled workers per pod; Kubernetes handles horizontal scaling via HPA
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
