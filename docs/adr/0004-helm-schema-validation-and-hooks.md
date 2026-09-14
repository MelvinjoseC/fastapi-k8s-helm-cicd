# ADR 0004: Helm Values Schema Validation and Lifecycle Hooks

## Status
Accepted

## Context
Misconfigured Helm values (such as malformed resource strings, invalid port numbers, or missing required keys) frequently fail silently during templating and only error out during Kubernetes API validation or mid-rollout pod creation.

## Decision
1. **Values Schema Validation**: Implemented `helm/taskapi/values.schema.json` compliant with JSON Schema Draft 7 to validate all inputs before chart rendering.
2. **Chart Testing & Test Hook**: Added `helm/taskapi/templates/tests/test-connection.yaml` executed via `helm test` to assert end-to-end pod connectivity post-deploy.
3. **Dedicated Staging Profile**: Added `values-staging.yaml` alongside `values.yaml` and `values-prod.yaml` for predictable multi-environment promotion.

## Consequences
- **Positive**: Erroneous configurations are rejected client-side before touching the cluster; deployment integrity is verifiable via standard Helm commands.
- **Negative**: Schema file requires maintenance when introducing new configurable parameters to `values.yaml`.