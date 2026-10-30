# ADR 0005: Service and Repository Architecture Pattern

## Status
Accepted

## Context
As the Task Management API scaled, HTTP route handlers contained database queries, validation logic, cache lookups, and Prometheus metric mutations directly. This coupled transport concerns with business and persistence logic, making unit testing difficult and leading to duplicated query logic across endpoints.

## Decision
We implemented a strict layered architectural pattern:
1. **Repository Layer (`app/repositories/`):** Encapsulates all SQLAlchemy queries, pagination, sorting, soft deletion, and aggregate queries. Implements `BaseRepository` generic interface.
2. **Service Layer (`app/services/`):** Coordinates domain business rules, cross-cutting cache invalidation, metric counters, and transactions.
3. **Router Layer (`app/routers/`):** Focuses solely on HTTP serialization, FastAPI dependency injection, query parsing, and response status codes.

## Consequences
### Positive
- Business logic is testable in unit isolation without booting a mock database or web client.
- Data access is centralized; index optimizations and SQL dialect adjustments affect only the repository.
- Reusable domain logic between standard CRUD, bulk operations, and background tasks.

### Negative
- Increases the number of files and abstractions for simple endpoints.
