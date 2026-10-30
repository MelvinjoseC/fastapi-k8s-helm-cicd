# ADR 0006: Distributed Circuit Breaker and Cache Stampede Mitigation

## Status
Accepted

## Context
Redis provides response caching and token-bucket rate limiting. In distributed Kubernetes environments, intermittent network partitions or Redis restarts can cause requests to stall on socket timeouts, exhausting web worker pools and cascading into full API outages.

## Decision
We implemented the Circuit Breaker pattern with the following semantics:
1. **Three State Machine:** Transitions from `CLOSED` -> `OPEN` after 3 consecutive failures, and enters `HALF_OPEN` after a 15-second recovery window.
2. **Fail-Soft Degradation:** When the circuit is `OPEN`, cache calls return immediately without executing network calls, falling back straight to database execution.
3. **Probabilistic TTL Jitter:** Applied +/- 10% TTL jitter to prevent cache stampedes where keys expire simultaneously.
4. **Prometheus Telemetry:** Exposes `taskapi_circuit_breaker_state` gauge and alert thresholds in `monitoring/prometheus-rules.yaml`.

## Consequences
### Positive
- Prevents cascading pod crashes during Redis unavailability.
- Eliminates thread starvation and lowers p99 latency during network blips.

### Negative
- Increases database read load while circuit is open until Redis recovers.
