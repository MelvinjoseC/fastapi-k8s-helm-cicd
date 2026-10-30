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

An enterprise-grade, production-hardened microservice ecosystem designed to demonstrate an end-to-end DevOps and platform engineering workflow: a containerized **FastAPI** service with Clean Architecture (Routers, Services, Repositories), database schema migrations via **Alembic**, multi-environment deployments via **Kustomize** and **Helm 3**, declarative GitOps via **Argo CD ApplicationSet**, zero-downtime rolling deployments, multi-layer security policies, circuit breaker resilience, and distributed observability with **Prometheus**, **Grafana**, and **OpenTelemetry**.

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
  │  - Router/Svc  │              │  - Router/Svc  │              │  - Router/Svc  │
  │  - RateLimiter │              │  - RateLimiter │              │  - RateLimiter │
  │  - CircuitBrkr │              │  - CircuitBrkr │              │  - CircuitBrkr │
  │  - OTel Tracer │              │  - OTel Tracer │              │  - OTel Tracer │
  └─────┬──────────┘              └─────┬──────────┘              └─────┬──────────┘
        │                                │                                │
        └────────────────────────────────┴────────────────────────────────┘
                     │                                           │
         ┌───────────▼───────────┐                   ┌───────────▼───────────┐
         │ Redis Cache           │                   │ PostgreSQL            │
         │ - Sliding window rate │                   │ - StatefulSet / PVC   │
         │ - Circuit Breaker     │                   │ - Alembic Migrations  │
         │ - Cache-aside / jitter│                   │ - Audit Columns & Idx │
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
| **API Application** | Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2 | Layered Clean Architecture (Routers, Services, Repositories) |
| **Data & Cache** | PostgreSQL 16, Redis 7, Alembic | ACID relational storage, Circuit Breaker cache-aside with stampede protection |
| **Containerization** | Docker, Multi-stage builds, dumb-init, non-root (UID 10001) | Hardened runtime image compliant with CIS Docker benchmarks |
| **Kubernetes** | Deployments, HPA, PDB, NetworkPolicy, LimitRange, ResourceQuota | High availability, zero-downtime rolling updates, strict isolation |
| **Config & Release** | Kustomize (base + dev/staging/prod) & Helm 3 | Declarative overlays, JSON schema validation, pre-upgrade hooks, startupProbe |
| **GitOps** | Argo CD & ApplicationSet | Declarative fleet continuous delivery with self-healing reconciliation |
| **CI/CD** | GitHub Actions, Ruff, Mypy, Bandit, Trivy, CodeQL, kind | End-to-end automated pipelines with real in-cluster smoke tests & schema drift check |
| **Observability** | Prometheus, OpenTelemetry, Jaeger, Grafana | Custom business metrics, SLO burn rate alerts, distributed tracing |
| **Quality & Tests** | Pytest (38+ tests), Pytest-Cov (>90% coverage), Load Generator, Benchmarking | Comprehensive integration, pagination, bulk operations, resilience, and stress tests |

---

## 📁 Repository Structure

```
├── .github/
│   └── workflows/          # CI, CD, CodeQL, and Helm lint workflows
├── alembic.ini             # Database migration configuration
├── app/
│   ├── alembic/            # Version-controlled database schema migrations (001-003)
│   ├── middleware/         # Security headers, correlation ID, XSS sanitization
│   ├── repositories/       # Generic BaseRepository & TaskRepository persistence layer
│   ├── routers/            # Modular APIRouters (tasks, health, diagnostics)
│   ├── services/           # TaskService coordinating transactions, cache, and metrics
│   ├── tests/              # Comprehensive test suite (38 test cases across all layers)
│   ├── auth.py             # API Key & Bearer token authentication with RBAC
│   ├── cache.py            # Resilient Redis cache-aside with Circuit Breaker
│   ├── config.py           # Pydantic v2 Settings (12-factor methodology)
│   ├── database.py         # SQLAlchemy engine and connection pooling
│   ├── Dockerfile          # Multi-stage, dumb-init, non-root container build
│   ├── exceptions.py       # Domain exceptions and RFC 7807 problem responses
│   ├── logging_config.py   # Structured JSON logger with async contextvars
│   ├── main.py             # FastAPI entrypoint and application bootstrap
│   ├── metrics.py          # Prometheus counters, gauges, histograms
│   ├── migrate.py          # Standalone migration runner with retry backoff
│   ├── models.py           # SQLAlchemy task entity with audit columns & soft delete
│   ├── rate_limiter.py     # Sliding-window rate limiter
│   ├── resilience.py       # Thread-safe Circuit Breaker pattern
│   ├── requirements.txt    # Production dependencies
│   ├── requirements-dev.txt# Linting, testing, and security dependencies
│   ├── schemas.py          # Pydantic request/response schemas, validation, bulk ops
│   └── tracing.py          # OpenTelemetry distributed tracing & SQLAlchemy hooks
├── argocd/                 # Argo CD Application & ApplicationSet CRDs
├── docker-compose.yml      # Local stack (API, Postgres, Redis, Prometheus, Jaeger)
├── docker-compose.override.yml.example # Live reload override template
├── docs/
│   ├── adr/                # Architecture Decision Records (0001 - 0006)
│   ├── api.md              # REST API endpoint reference
│   ├── architecture.md     # In-depth architectural trade-offs
│   ├── openapi.json        # Exported static OpenAPI 3.1.0 specification
│   └── runbook.md          # Production incident response and operations runbook
├── helm/taskapi/           # Production Helm chart (schema, hooks, tests, templates)
├── k8s/                    # Raw Kubernetes manifests (base + dev/staging/prod overlays)
├── monitoring/             # Grafana dashboards, Prometheus alerting rules
├── scripts/                # Benchmarking, automated health-checks, backups, seed data
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
- API Documentation: `http://localhost:8000/docs`
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

### 3. Seed Realistic Sample Data & Benchmarking
```bash
# Populate database with realistic task data
make seed

# Run performance benchmarking with latency percentiles
make benchmark

# Run automated deployment health verification
make health
```

### 4. Run Test Suite with Coverage
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

### 4. GitOps with Argo CD ApplicationSet
```bash
kubectl apply -k argocd/
```

---

## 🛡️ Production & Resilience Highlights

- **Clean Layered Architecture**: Routers, Services, and Repositories isolate transport from business and persistence logic.
- **Circuit Breaker Resilience**: Prevents cascading failures when Redis blips, automatically falling soft to PostgreSQL.
- **Zero-Downtime Rolling Updates**: Configured with `maxSurge: 1`, `maxUnavailable: 0`, and `preStop` sleep lifecycle hooks.
- **Restricted Pod Security Standard**: Non-root UID `10001`, `seccompProfile: RuntimeDefault`, `readOnlyRootFilesystem: true`, dropping all capabilities.
- **Topology Spread Constraints & Anti-Affinity**: Pods are evenly distributed across availability zones and worker nodes.
- **Default-Deny Network Policies**: Explicit egress whitelisting for PostgreSQL, Redis, and kube-dns.
- **Alembic Helm Pre-Upgrade Hooks**: Automatic database migrations before new pods receive traffic, eliminating DDL deadlocks.
- **SLO-Based Alerting**: Multi-window burn-rate alerts notify operators when the 99.9% error budget is being consumed too quickly.
- **OpenAPI Schema Drift Enforcement**: CI pipeline automatically verifies code-to-schema synchronization.

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
- [ADR 0005: Service and Repository Architecture Pattern](docs/adr/0005-service-and-repository-pattern.md)
- [ADR 0006: Distributed Circuit Breaker and Cache Stampede Mitigation](docs/adr/0006-circuit-breaker-and-resilience.md)

---

## 📜 License

MIT License - see [LICENSE](LICENSE) for details.
