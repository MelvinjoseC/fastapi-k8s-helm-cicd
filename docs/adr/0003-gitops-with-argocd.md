# ADR 0003: Declarative GitOps Workflow with Argo CD

## Status
Accepted

## Context
Deploying manifests directly from CI runners using imperative `kubectl apply` commands introduces security concerns (runner requires high-privilege cluster credentials) and configuration drift (changes made out-of-band are not reconciled).

## Decision
1. **Git as Single Source of Truth**: Define target states in Git using Kustomize overlays (`dev`, `staging`, `prod`).
2. **Pull-based Reconciliation**: Introduce Argo CD Application CRDs (`argocd/application-*.yaml`) executing inside the target cluster.
3. **Automated vs. Gated Sync**:
   - `dev` and `staging`: Fully automated sync with pruning and self-healing.
   - `prod`: Automated self-healing with manual sync gate for controlled release changes.

## Consequences
- **Positive**: Eliminates cluster credential leakage in CI runners; continuous drift detection; instantaneous rollbacks via `git revert`.
- **Negative**: Requires running the Argo CD control plane within the Kubernetes infrastructure.