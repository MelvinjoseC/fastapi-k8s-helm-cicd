# ADR 0002: Database Migrations with Alembic & Kubernetes Jobs

## Status
Accepted

## Context
Running `Base.metadata.create_all()` inside application pod startup creates severe race conditions when scaling horizontal replicas in Kubernetes. Multiple pods simultaneously executing DDL operations leads to table locks, transaction deadlocks, and corrupted migration states.

## Decision
1. **Alembic Framework**: Adopt Alembic for version-controlled, reversible schema migrations.
2. **Decoupled Execution**: Migrate away from in-app startup DDL to a dedicated standalone migration script (`app/migrate.py`).
3. **Deployment Lifecycle**:
   - In Kubernetes: Execute migrations via a pre-deployment batch `Job` (`k8s/base/migration-job.yaml`).
   - In Helm: Execute migrations using a `pre-install,pre-upgrade` Helm hook Job (`job-migration.yaml`) with cleanup policy `before-hook-creation,hook-succeeded`.

## Consequences
- **Positive**: Zero DDL race conditions during pod scale-up; automated, declarative schema upgrades on every rollout.
- **Negative**: Adds a sequential dependency before pods can start traffic serving. Mitigated by exponential backoff connectivity checks and lightweight migration scripts.