# Task API — REST API Reference

The Task API is designed according to REST principles, returns JSON payloads, standard HTTP status codes, and RFC 7807 error responses.

---

## Headers

| Header | Type | Description |
|---|---|---|
| `X-Request-ID` | String | Unique request UUID for distributed correlation across logs and traces. |
| `X-Process-Time-Ms` | Float | Server execution latency in milliseconds. |
| `X-RateLimit-Limit` | Integer | Maximum allowable requests within the rolling window. |
| `X-RateLimit-Remaining` | Integer | Requests remaining in the current window. |

---

## Endpoints

### 1. Health & Readiness
- `GET /health`: Liveness probe (no external dependency checks). Returns `{"status": "ok"}`.
- `GET /ready`: Readiness probe. Validates database connectivity and checks cache health.
- `GET /metrics`: Prometheus metric scrape exposition.

### 2. Task Management
- `POST /tasks`: Create a new task.
  - Body:
    ```json
    {
      "title": "Harden Kubernetes Cluster",
      "description": "Deploy NetworkPolicies and LimitRanges",
      "priority": "urgent",
      "tags": ["k8s", "security"],
      "due_date": "2026-12-31T23:59:59Z"
    }
    ```
- `GET /tasks`: Retrieve list of tasks.
  - Query Parameters:
    - `completed`: Filter by boolean completion status.
    - `status`: Filter by status (`pending`, `in_progress`, `completed`, `cancelled`).
    - `priority`: Filter by priority (`low`, `medium`, `high`, `urgent`).
    - `q`: Full-text search term in title or description.
    - `include_deleted`: Boolean flag to view soft-deleted tasks.
- `GET /tasks/paginated`: Retrieve paginated response:
  - Query Parameters: `page` (default 1), `page_size` (default 20, max 100).
- `GET /tasks/{task_id}`: Retrieve single task by integer ID.
- `PUT /tasks/{task_id}`: Partially or fully update task fields.
- `DELETE /tasks/{task_id}`: Soft delete task (or permanent delete with `?permanent=true`).
- `POST /tasks/{task_id}/restore`: Restore soft-deleted task.