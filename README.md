# Task API — Cloud-Native Kubernetes & DevOps Showcase

[![CI](https://github.com/MelvinjoseC/fastapi-k8s-helm-cicd/actions/workflows/ci.yml/badge.svg)](https://github.com/MelvinjoseC/fastapi-k8s-helm-cicd/actions/workflows/ci.yml)
[![CodeQL](https://github.com/MelvinjoseC/fastapi-k8s-helm-cicd/actions/workflows/codeql.yml/badge.svg)](https://github.com/MelvinjoseC/fastapi-k8s-helm-cicd/actions/workflows/codeql.yml)
[![Helm Quality](https://github.com/MelvinjoseC/fastapi-k8s-helm-cicd/actions/workflows/helm-lint.yml/badge.svg)](https://github.com/MelvinjoseC/fastapi-k8s-helm-cicd/actions/workflows/helm-lint.yml)
![Python](https://img.shields.io/badge/python-3.12-blue)
![FastAPI](https://img.shields.io/badge/fastapi-0.111-009688)
![Kubernetes](https://img.shields.io/badge/kubernetes-1.30-326ce5)
![Helm](https://img.shields.io/badge/helm-3.14-0f1689)
![ArgoCD](https://img.shields.io/badge/GitOps-ArgoCD-orange)
![License](https://img.shields.io/badge/license-MIT-green)

An enterprise-grade, production-hardened microservice ecosystem designed to demonstrate an end-to-end DevOps and platform engineering workflow: a containerized **FastAPI** service, database schema migrations via **Alembic**, multi-environment deployments via **Kustomize** and **Helm 3**, declarative GitOps via **Argo CD**, zero-downtime rolling deployments, multi-layer security policies, and distributed observability with **Prometheus**, **Grafana**, and **OpenTelemetry**.

---

## 🏛️ Architecture Overview

```
                      ┌──────────────────────────────────────┐
                      │    Ingress Controller (nginx)        │
                      │    TLS via cert-manager              │
                      └──────────────────┬───────────────────┘
                                         │
                      ┌──────────────────▼───────────────────┐
                      │    Service: taskapi (ClusterIP)      │
                      └──────────────────┬───────────────────┘
                                         │
        ┌────────────────────────────────┼────────────────────────────────┐
        │                                │                                │
  ┌─────▼──────────┐              ┌─────▼──────────┐              ┌─────▼──────────┐
  │  Pod 1         │              │  Pod 2         │              │  Pod N         │
  │  - FastAPI App │              │  - FastAPI App │              │  - FastAPI App │
  │  - RateLimiter │              │  - RateLimiter │              │  - RateLimiter │
  │  - OTel Tracer │              │  - OTel Tracer │              │  - OTel Tracer │
  └─────┬──────────┘              └─────┬──────────┘              └─────┬──────────┘
        │                                │                                │
        └────────────────────────────────┴────────────────────────────────┘
                     │                                           │
         ┌───────────▼───────────┐                   ┌───────────▼───────────┐
         │ Redis Cache           │                   │ PostgreSQL            │
         │ - Sliding window rate │                   │ - StatefulSet / PVC   │
         │ - Cache-aside / jitter│                   │ - Alembic Migrations  │
         └───────────────────────┘                   └───────────────────────┘
                     │                                           │
                     ▼                                           ▼
         ┌───────────────────────────────────────────────────────────────────┐
         │ Observability: Prometheus Metrics, OTel Traces, Grafana Dashboard │
         └───────────────────────────────────────────────────────────────────┘
```

See [`docs/architecture.md`](docs/architecture.md) for design decisions, and [`docs/adr/`](docs/adr/) for Architecture Decision Records.

---

## 🛠️ Tech Stack & Tooling

| Domain | Tools & Frameworks | Description |
|---|---|---|
| **API Application** | Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2 | High-performance async REST API with rich domain modeling |
| **Data & Cache** | PostgreSQL 16, Redis 7, Alembic | ACID relational storage, resilient cache-aside, schema migrations |
| **Containerization** | Docker, Multi-stage builds, dumb-init, non-root (UID 10001) | Hardened runtime image compliant with CIS Docker benchmarks |
| **Kubernetes** | Deployments, HPA, PDB, NetworkPolicy, LimitRange, ResourceQuota | High availability, zero-downtime rolling updates, strict isolation |
| **Config & Release** | Kustomize (base + dev/staging/prod) & Helm 3 | Declarative overlays, JSON schema validation, pre-upgrade hooks |
| **GitOps** | Argo CD | Declarative continuous delivery with self-healing reconciliation |
| **CI/CD** | GitHub Actions, Ruff, Mypy, Bandit, Trivy, CodeQL, kind | End-to-end automated pipelines with real in-cluster smoke tests |
| **Observability** | Prometheus, OpenTelemetry, Jaeger, Grafana | Custom business metrics, SLO burn rate alerts, distributed tracing |
| **Quality & Tests** | Pytest, Pytest-Cov (>90% coverage), Load Generator | Comprehensive integration, pagination, security, and stress tests |

---

## 📁 Repository Structure

```
├── .github/
│   └── workflows/          # CI, CD, CodeQL, and Helm lint workflows
├── alembic.ini             # Database migration configuration
├── app/
│   ├── alembic/            # Version-controlled database schema migrations
│   ├── middleware/         # Security headers, correlation ID, request context
│   ├── tests/              # Comprehensive test suite (19 test cases)
│   ├── cache.py            # Resilient Redis cache-aside with jitter
│   ├── config.py           # Pydantic v2 Settings (12-factor methodology)
│   ├── database.py         # SQLAlchemy engine and connection pooling
│   ├── Dockerfile          # Multi-stage, dumb-init, non-root container build
│   ├── exceptions.py       # Domain exceptions and RFC 7807 error responses
│   ├── logging_config.py   # Structured JSON logger
│   ├── main.py             # FastAPI entrypoint and endpoint routes
│   ├── metrics.py          # Prometheus counters, gauges, histograms
│   ├── migrate.py          # Standalone migration runner with retry backoff
│   ├── models.py           # SQLAlchemy task entity with enums and soft delete
│   ├── rate_limiter.py     # Sliding-window rate limiter
│   ├── requirements.txt    # Production dependencies
│   ├── requirements-dev.txt# Linting, testing, and security dependencies
│   ├── schemas.py          # Pydantic request/response schemas and pagination
│   └── tracing.py          # OpenTelemetry distributed tracing setup
├── argocd/                 # Argo CD Application CRDs (dev, staging, prod)
├── docker-compose.yml      # Local stack (API, Postgres, Redis, Prometheus, Jaeger)
├── docs/
│   ├── adr/                # Architecture Decision Records (0001 - 0004)
│   ├── api.md              # REST API endpoint reference
│   ├── architecture.md     # In-depth architectural trade-offs
│   ├── openapi.json        # Exported static OpenAPI 3.1.0 specification
│   └── runbook.md          # Production incident response and operations runbook
├── helm/taskapi/           # Production Helm chart (schema, hooks, tests, templates)
├── k8s/                    # Raw Kubernetes manifests (base + dev/staging/prod overlays)
├── monitoring/             # Grafana dashboards, Prometheus alerting rules
├── scripts/                # Data seeding and concurrent load testing utilities
├── Makefile                # Developer workflow commands
├── pyproject.toml          # Ruff, Mypy, Pytest, and Coverage configurations
├── README.md               # Project documentation
└── SECURITY.md             # Security vulnerability disclosure policy
```

---

## ⚡ Quick Start — Local Development

### 1. Run via Docker Compose (Full Stack)
```bash
# Start API + PostgreSQL + Redis + Prometheus + Jaeger
make compose-obs
```
- API: `http://localhost:8000/docs`
- Prometheus UI: `http://localhost:9090`
- Jaeger Tracing UI: `http://localhost:16686`

### 2. Run Locally with Virtualenv
```bash
# Setup environment and dependencies
make install

# Run database migrations
make migrate

# Start development server with reload
make run
```

### 3. Seed Realistic Sample Data
```bash
make seed
```

### 4. Run Concurrent Load Test
```bash
# Stress-test API with 100 concurrent requests
make load-test
```

### 5. Run Test Suite with Coverage
```bash
make test-cov
```

---

## ☸️ Kubernetes & Helm Deployment

### 1. Kind Cluster Smoke Test
```bash
make kind-up
make k8s-deploy-dev
curl http://localhost:8080/health
make kind-down
```

### 2. Multi-Environment Kustomize Overlays
```bash
# Deploy to Development
kubectl apply -k k8s/overlays/dev

# Deploy to Staging
kubectl apply -k k8s/overlays/staging

# Deploy to Production
kubectl apply -k k8s/overlays/prod
```

### 3. Helm Chart Deployment
```bash
# Validate chart and values schema
helm lint helm/taskapi

# Install release with staging or production values
helm upgrade --install taskapi ./helm/taskapi \
  --namespace taskapi --create-namespace \
  -f helm/taskapi/values-prod.yaml

# Run built-in connection verification test
make helm-test
```

### 4. GitOps with Argo CD
```bash
kubectl apply -k argocd/
```

---

## 🛡️ Production & Resilience Highlights

- **Zero-Downtime Rolling Updates**: Configured with `maxSurge: 1`, `maxUnavailable: 0`.
- **Restricted Pod Security Standard**: Non-root UID `10001`, `seccompProfile: RuntimeDefault`, `readOnlyRootFilesystem: true`, dropping all capabilities.
- **Topology Spread Constraints & Anti-Affinity**: Pods are evenly distributed across availability zones and worker nodes.
- **Default-Deny Network Policies**: Explicit egress whitelisting for PostgreSQL, Redis, and kube-dns.
- **Alembic Helm Hooks**: Pre-upgrade Job hooks migrate the database before new pods receive traffic, eliminating DDL deadlocks.
- **Resilient Cache-Aside**: Soft degradation when Redis is down; traffic falls back to PostgreSQL without 500 errors.
- **SLO-Based Alerting**: Multi-window burn-rate alerts notify operators when the 99.9% error budget is being consumed too quickly.

---

## 📄 Documentation Links

- [Architecture & Design Decisions](docs/architecture.md)
- [REST API Reference](docs/api.md)
- [Production Operations Runbook](docs/runbook.md)
- [Security Policy](SECURITY.md)
- [ADR 0001: Structured JSON Logging & Distributed Tracing](docs/adr/0001-structured-json-logging-and-tracing.md)
- [ADR 0002: Database Migrations with Alembic](docs/adr/0002-database-migrations-with-alembic.md)
- [ADR 0003: Declarative GitOps Workflow with Argo CD](docs/adr/0003-gitops-with-argocd.md)
- [ADR 0004: Helm Schema Validation and Lifecycle Hooks](docs/adr/0004-helm-schema-validation-and-hooks.md)

---

## 📜 License

MIT License - see [LICENSE](LICENSE) for details.