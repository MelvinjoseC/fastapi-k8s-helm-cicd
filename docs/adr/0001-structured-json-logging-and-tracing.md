# ADR 0001: Structured JSON Logging & Distributed Tracing

## Status
Accepted

## Context
In production Kubernetes environments, services emit high volumes of log data collected by log forwarders (e.g. FluentBit, Vector, Promtail) into aggregation engines (Loki, Elasticsearch, Datadog). Plain unstructured string logs require fragile regex parsers and hinder automated querying. Furthermore, distributed microservices require end-to-end request tracing to diagnose cross-service latency bottlenecks.

## Decision
1. **JSON Formatting**: Standardized application logs into single-line structured JSON records containing `timestamp` (ISO 8601 UTC), `level`, `logger`, `message`, and context variables.
2. **Correlation ID**: Implemented ASGI middleware extracting or generating a unique `X-Request-ID` and propagating it via `ContextVar` to all log records and downstream response headers.
3. **OpenTelemetry Tracing**: Added OpenTelemetry SDK auto-instrumentation for FastAPI and HTTP handlers exporting traces via OTLP gRPC.

## Consequences
- **Positive**: Seamless integration with modern observability stacks; single query lookup across distributed logs via `correlation_id`.
- **Negative**: Slight overhead in serialization, mitigated by lightweight in-memory JSON formatter and asynchronous OTLP batch processor.