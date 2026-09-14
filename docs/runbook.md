# Task API — Production Operations & Incident Runbook

This runbook provides actionable procedures for responding to high-priority operational alerts and managing production lifecycle operations for the Task API service.

---

## 1. Incident Response Procedures

### 1.1 Alert: `TaskAPIHighErrorRate` / `TaskAPISLOBurnRateFast`
- **Severity**: Critical (P1)
- **Symptom**: 5xx HTTP responses exceed 5% of total traffic or error budget is burning rapidly.
- **Triage Steps**:
  1. Inspect pod logs for unhandled exceptions:
     ```bash
     kubectl logs -n taskapi -l app=taskapi --tail=200 --prefix
     ```
  2. Verify database connection pool health:
     ```bash
     kubectl exec -it -n taskapi deployment/taskapi -- python -c "from database import check_db_health; print(check_db_health())"
     ```
  3. Verify PostgreSQL StatefulSet status:
     ```bash
     kubectl describe statefulset/postgres -n taskapi
     kubectl logs -n taskapi statefulset/postgres --tail=100
     ```
  4. If caused by a recent deployment, immediately initiate rollback:
     ```bash
     helm rollback taskapi -n taskapi
     # or if using Kustomize:
     kubectl rollout undo deployment/taskapi -n taskapi
     ```

### 1.2 Alert: `TaskAPIHighLatency`
- **Severity**: Warning (P2)
- **Symptom**: p95 request latency exceeds 1 second for 10 minutes.
- **Triage Steps**:
  1. Check Redis cache hit ratio in Grafana dashboard (`taskapi-overview`).
  2. Verify Redis responsiveness:
     ```bash
     kubectl exec -it -n taskapi deployment/redis -- redis-cli ping
     ```
  3. Inspect slow database queries and connection limits:
     ```bash
     kubectl exec -it -n taskapi statefulset/postgres -- psql -U taskapi -c "SELECT pid, now() - pg_stat_activity.query_start AS duration, query FROM pg_stat_activity WHERE (now() - pg_stat_activity.query_start) > interval '1 second';"
     ```
  4. Check if HPA is scaling appropriately:
     ```bash
     kubectl get hpa taskapi-hpa -n taskapi
     ```

### 1.3 Alert: `TaskAPIPodCrashLooping`
- **Severity**: Critical (P1)
- **Symptom**: Repeated pod restarts exceeding failure thresholds.
- **Triage Steps**:
  1. Check previous container termination reason:
     ```bash
     kubectl describe pod <pod-name> -n taskapi
     kubectl logs <pod-name> -n taskapi --previous
     ```
  2. Common causes:
     - **OOMKilled**: Memory limit too low. Adjust `resources.limits.memory`.
     - **Liveness Probe Failure**: Service taking too long to start or deadlocking. Verify startupProbe timing.
     - **Configuration/Secret Missing**: Ensure `taskapi-secret` and `taskapi-config` exist.

---

## 2. Standard Operational Procedures

### 2.1 Database Schema Migrations
Migrations run automatically via the Helm pre-upgrade hook. To execute manually:
```bash
# Direct in-pod or local run:
python app/migrate.py

# Check current migration revision:
alembic current
```

### 2.2 Manual Scale-Out
To scale replicas when bypassing HPA:
```bash
kubectl scale deployment/taskapi --replicas=8 -n taskapi
```

### 2.3 Evacuation / Cluster Maintenance
Drain node safely honoring PodDisruptionBudget:
```bash
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data
```