# Architecture & Design Decisions

## Overview

Task API is a small FastAPI CRUD service backed by Postgres, with Redis as
an optional read-through cache. It's deliberately scoped small so every
Kubernetes concept in the manifests is easy to trace back to a real,
runnable piece of code rather than being decorative.

```
                          ┌─────────────────────┐
                  HTTPS   │   Ingress (nginx)    │
            ───────────▶  │   TLS via cert-mgr   │
                          └──────────┬───────────┘
                                     │
                          ┌──────────▼───────────┐
                          │   Service: taskapi    │  (ClusterIP)
                          └──────────┬───────────┘
                                     │
                  ┌──────────────────┼──────────────────┐
                  │                  │                  │
            ┌─────▼─────┐     ┌─────▼─────┐      ┌─────▼─────┐
            │  Pod 1    │     │  Pod 2    │      │  Pod N    │   <- HPA scales 2-10
            │  FastAPI  │     │  FastAPI  │      │  FastAPI  │      on CPU/memory
            └─────┬─────┘     └─────┬─────┘      └─────┬─────┘
                  │                  │                  │
        ┌─────────┴──────────────────┴──────────────────┘
        │
   ┌────▼─────┐                              ┌──────────┐
   │  Redis    │ (cache, best-effort)         │ Postgres │ (StatefulSet + PVC)
   └───────────┘                              └──────────┘
```

## Why these choices

**FastAPI over Flask/Django** - native async support, automatic OpenAPI
docs, and Pydantic validation out of the box, which matters for a service
meant to be a clean example of modern Python API design.

**Cache treated as optional, not a dependency** - `cache.py` swallows
Redis connection errors and falls through to Postgres. This mirrors a
real production pattern: a cache outage should degrade latency, not
take the whole service down. The `/ready` endpoint reports cache state
separately (`"cache": "degraded"`) so it's observable without being a
blocker.

**Liveness vs. readiness vs. startup probes are intentionally separate**
- `/health` (liveness) has zero external calls. If it only checked
  the DB, a Postgres blip would cause Kubernetes to kill and restart
  every API pod simultaneously - the worst possible time to lose
  capacity.
- `/ready` (readiness) does check the DB, so Kubernetes pulls a pod out
  of the Service's load-balancing rotation the moment it can't actually
  serve a request, without restarting the container.
- A `startupProbe` gives slow-starting containers (e.g. during a cold
  start or migration) room to come up without that delay counting
  against the liveness probe's failure threshold.

**`maxUnavailable: 0` on the rolling update** - guarantees the Service
never has fewer than the desired replica count during a deploy, at the
cost of briefly running `replicas + 1` pods. For a stateless API this
trade-off is almost always worth it.

**NetworkPolicy is default-deny** - the API pod can only reach Postgres,
Redis, DNS, and the ingress controller. This is a deliberate, minimal
allow-list rather than relying on namespace isolation alone.

**Kustomize overlays + a parallel Helm chart** - real teams pick one,
but both are included here to demonstrate fluency in both. Kustomize is
used for the kind-based CI smoke test because it requires no install
step beyond `kubectl`; the Helm chart is wired into the CD pipeline as
the production deployment mechanism, since most orgs standardize on Helm
for release management (`helm rollback`, release history, etc.).

**Postgres runs as an in-cluster StatefulSet** - intentional for a
self-contained demo that runs the same way on a laptop's `kind` cluster
as on a real cluster. In an actual production environment, swapping
`DATABASE_URL` to point at a managed instance (RDS, Cloud SQL) is a
one-line change and the StatefulSet manifest would be dropped entirely -
that's the benefit of keeping config in env vars from day one.

**Secrets in this repo are placeholders** - committing real Kubernetes
Secrets to git is a common and serious mistake. The included
`secret.yaml`/Helm secret template exist so the project runs immediately
for a demo or CI smoke test; the README and inline comments call out
Sealed Secrets / External Secrets Operator as the production path.

## What I'd add with more time

- mTLS between services via a service mesh (Linkerd/Istio)
- OpenTelemetry tracing in addition to Prometheus metrics
- A staging environment + GitOps (Argo CD) instead of `kubectl`/`helm`
  driven directly from CI
- Database migrations via Alembic instead of `create_all()`
