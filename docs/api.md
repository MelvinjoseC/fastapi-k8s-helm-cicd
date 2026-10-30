# Task API — REST API Reference

The Task API is designed according to REST principles, returns JSON payloads, standard HTTP status codes, and RFC 7807 problem detail error responses.

---

## Authentication & Headers

| Header | Type | Description |
|---|---|---|
| `X-Request-ID` | String | Unique request UUID for distributed correlation across logs and traces. |
| `X-Process-Time-Ms` | Float | Server execution latency in milliseconds. |
| `X-RateLimit-Limit` | Integer | Maximum allowable requests within the rolling window. |
| `X-RateLimit-Remaining` | Integer | Requests remaining in the current window. |
| `X-API-Key` | String | API key authentication header (when `AUTH_ENABLED=true`). |
| `Authorization` | String | Standard `Bearer <token>` authorization header. |

---

## Endpoints

### 1. Health, Probes & Diagnostics
- `GET /health` or `GET /health/live`: Liveness probe (verifies process is up without external calls).
- `GET /ready` or `GET /health/ready`: Readiness probe (validates database query response and Redis connectivity).
- `GET /health/startup`: Startup probe for slow migrations and database bootstrap.
- `GET /health/system`: System diagnostics returning uptime, Python version, platform, and worker details.
- `GET /metrics`: Prometheus metric scrape exposition.

### 2. Task Management & Queries
- `POST /tasks`: Create a new task.
- `GET /tasks`: Retrieve list of tasks with filters:
  - `completed`: Filter by completion status (`true` / `false`).
  - `status`: Filter by status (`pending`, `in_progress`, `completed`, `cancelled`).
  - `priority`: Filter by priority (`low`, `medium`, `high`, `urgent`).
  - `assigned_to`: Filter by assignee email.
  - `q`: Search keyword across title and description.
  - `sort_by`: Field to sort (`created_at`, `due_date`, `priority`, `title`).
  - `sort_order`: Direction (`asc` or `desc`).
  - `include_deleted`: Include soft-deleted records.
- `GET /tasks/paginated`: Paginated response (`page`, `page_size`, `total`, `total_pages`).
- `GET /tasks/{task_id}`: Retrieve single task by ID.
- `PUT /tasks/{task_id}`: Update task properties.
- `DELETE /tasks/{task_id}`: Soft delete (or permanent delete with `?permanent=true`).
- `POST /tasks/{task_id}/restore`: Restore soft-deleted task.

### 3. Bulk & Batch Operations
- `POST /tasks/bulk`: Create up to 100 tasks in a single atomic transaction.
- `PATCH /tasks/bulk`: Batch update status or priority across multiple task IDs.
- `DELETE /tasks/bulk`: Batch delete multiple task IDs.

### 4. Reporting & Analytics
- `GET /tasks/analytics/summary`: Aggregate metrics including total tasks, active tasks, completion rate %, overdue count, and distributions by status and priority.
- `GET /tasks/export`: Export tasks in `json` or `csv` format with attachment headers.
