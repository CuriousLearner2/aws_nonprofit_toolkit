# Task Contract and Lanes

Before meaningful work, Orchestrator must instantiate:

```text
Task contract:
- Task type: Assessment only / Implementation only / Commit preparation / Push only
- Pre-authorized lane: assessment / test-only hardening / workflow/CI automation / product/invariant hardening / push only / none
- Allowed actions:
- Forbidden actions:
- Files in scope:
- Product UX ambiguity present? yes/no
- Product UX Gatekeeper required? yes/no
- Reviewer required? yes/no
- Why Reviewer is/is not required:
- Breaker required? yes/no
- Why Breaker is/is not required:
- QA/UAT required? yes/no
- QA mode: manual triage / runtime acceptance / none
- E2E involved? yes/no
- E2E proof stage:
- Canonical acceptance gates:
- Diagnostic commands:
- Diagnostic-failure classification authority:
- Test-Harness Stabilization enabled? yes/no
- Stabilization files and maximum iterations:
- Failed-First Repair Lane enabled? yes/no
- Failed-first repair budget:
- Durable-outcome contract required? yes/no
- Upstream user action:
- Required durable business outcome:
- Authoritative identity:
- Commit/transaction boundary:
- Response/serialization handoff:
- Reload/restart expectation:
- Relevant configuration matrix:
- Duplicate/retry/stale-response expectation:
- Partial-failure expectation:
- Exact cross-boundary acceptance test:
- Autonomous multi-item campaign enabled? yes/no
- Frozen P1 registry approved? yes/no
- Per-item commit checkpoint and finite campaign budgets:
- Happy-path auto-commit enabled? yes/no
- Push authorized? yes/no
- Stop condition:
- Terminal state:
```

Rules:

- Do not proceed until required fields are explicit.
- Do not infer a lane from intent; require the exact lane in the contract.
- Assessment-only, push-only, and status-only tasks normally do not require Reviewer.
- Product/invariant hardening requires Product UX Gatekeeper only when a real product choice remains.
- Breaker is concrete-risk-based, not routine.
- Stateful P1 work requires the durable-outcome fields.
- Stateless low-risk work must set `Durable-outcome contract required? no` with a reason.

## Lanes

### Assessment

No edits, child implementation agents, staging, commit, or push.

### Test-only hardening

Only explicit test files. No product, template, route, workflow, CI, or schema changes.

### Workflow/CI automation

Only explicit `.claude/**`, `.github/**`, `scripts/ci/**`, and related tests. No product code.

### Product/invariant hardening

Only explicitly authorized product/test/doc files. Product UX Gatekeeper is required when visible behavior or semantics are unresolved. Breaker is required for concrete P0/P1 invariant risk.

### Push only

No edits or new commits. Push only when explicitly authorized.
