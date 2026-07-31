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
- Bounded recovery envelope enabled? yes/no
- Named repair batches and focused proofs:
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
- Execution classification: fast fix / engineering investigation / architecture pilot
- Execution-context map confirmed? yes/no
- Deterministic defect proof:
- Adjacent compatibility proof:
- Authoritative owner:
- Expected product files:
- Expected product diff size:
- Product file budget:
- Product diff budget:
- Milestones:
- Compatibility tripwires:
- Primary edit batches authorized:
- Implementation repair batches authorized:
- Test-harness repair batches authorized:
- Review repair batches authorized:
- Focused runs authorized:
- Maximum review cycles:
- Primary edit batches used:
- Implementation repair batches used:
- Test-harness repair batches used:
- Review repair batches used:
- Focused runs used:
- Review cycles used:
- Last focused run: not run / passed / failed
- Failure classification:
- Applicable repair batch remaining? yes/no
- Writes currently permitted? yes/no
- Characterization completed separately? yes/no/not required
- Production freeze point:
- Review diff fingerprint:
- Automatic continuation within bounds? yes/no
- Reassessment threshold:
- Deferred nonessential improvements:
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

## Focused-First Contract Rules

Execution semantics are owned by `policy/execution-safety.md`.

Required references:

- `ES-01` Assessment Firewall
- `ES-04` Environment-Only Recovery
- `ES-05` Failed-Gate Handling
- `ES-08` Edit-Batch, Repair-Batch, and Focused-Run Accounting
- `ES-09` Characterization Firewall
- `ES-10` Review Diff Freeze
- `ES-11` Focused-First Execution
- `ES-12` Compatibility Tripwires
- `ES-13` Budget Enforcement
- `ES-14` Recovery Envelope and Terminal Outcomes

Task contracts declare exact files, cumulative budgets, named primary/repair batches, focused runs, review cycles, role requirements, and stop conditions. They may narrow these rules but may not broaden them. ES-08 defines the meaning of repair batches and focused runs; execution semantics remain owned by `policy/execution-safety.md`.
