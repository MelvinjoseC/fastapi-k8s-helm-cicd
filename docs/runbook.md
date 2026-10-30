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

### 1.2 Alert: `TaskAPICircuitBreakerOpen`
- **Severity**: Critical (P1)
- **Symptom**: The circuit breaker for Redis caching has tripped open after consecutive communication failures.
- **Triage Steps**:
  1. Inspect Redis pod status and connectivity:
     ```bash
     kubectl get pods -n taskapi -l app=redis
     kubectl exec -it -n taskapi deployment/redis -- redis-cli ping
     ```
  2. Check memory consumption and connection count in Redis:
     ```bash
     kubectl exec -it -n taskapi deployment/redis -- redis-cli info memory
     ```
  3. Notice: While the circuit breaker is open, requests fail-soft to Postgres automatically without 500 errors.

### 1.3 Alert: `TaskAPIHighLatency` / `TaskAPIP99LatencySpike`
- **Severity**: Warning (P2)
- **Symptom**: p95 latency > 1s or p99 latency > 2s for 5+ minutes.
- **Triage Steps**:
  1. Check Redis cache hit ratio in Grafana dashboard (`taskapi-overview`).
  2. Inspect database active queries and slow table scans:
     ```bash
     kubectl exec -it -n taskapi statefulset/postgres -- psql -U taskapi -c "SELECT pid, now() - pg_stat_activity.query_start AS duration, query FROM pg_stat_activity WHERE (now() - pg_stat_activity.query_start) > interval '1 second';"
     ```
  3. Verify HPA autoscaling status:
     ```bash
     kubectl get hpa taskapi-hpa -n taskapi
     ```

---

## 2. Disaster Recovery & Backup Operations

### 2.1 Automated Database Backup
Take a timestamped JSON snapshot of all tasks:
```bash
python scripts/backup_restore.py backup --output backups/backup_manual.json
```

### 2.2 Database Restore
Restore tasks from a validated snapshot file:
```bash
python scripts/backup_restore.py restore --input backups/backup_manual.json --clear
```

### 2.3 Post-Deployment Health Verification
Run the automated verification suite to probe liveness, readiness, and telemetry endpoints:
```bash
python scripts/health_check.py --url https://taskapi.example.com --retries 5
```
