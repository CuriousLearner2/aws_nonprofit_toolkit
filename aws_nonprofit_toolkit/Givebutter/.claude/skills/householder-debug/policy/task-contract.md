# Task Contract and Lanes

Before meaningful implementation or commit-capable work, Orchestrator must instantiate the minimum task contract:

```text
Task contract:
- Task type: Assessment only / Implementation only / Commit preparation / Push only
- Pre-authorized lane:
- Allowed actions:
- Forbidden actions:
- Files in scope:
- Reviewer required? yes/no
- Breaker required? yes/no + reason
- QA/UAT required? yes/no
- E2E involved? yes/no
- Focused/relevant tests:
- Broad canonical test command:
- Baseline comparison required? yes/no
- Ledger progression required? yes/no
- Durable-outcome contract required? yes/no
- Review diff fingerprint:
- Stop condition:
- Terminal state:
```

Rules:
- Reviewer is required for implementation changes.
- Breaker is concrete-risk-based, not routine.
- QA is required only when explicitly needed.
- Stateful P1 work requires durable-outcome fields and normally `Ledger progression required? yes`.
- Architecture pilots and explicitly opted-in bounded-recovery work use the heavy ES-08/ES-13 fields.
- Ordinary low/medium-risk scoped work normally sets `Ledger progression required? no`.
- `BASELINE_DEBT_VERIFIED` is allowed when a baseline/current comparison proves no new failing identities.

### Heavy-path extension

Only when `Ledger progression required? yes`, additionally declare:
- Ledger executable owner
- exact execution classification
- authoritative owner
- product file/diff budgets
- milestones and compatibility tripwires
- primary/repair batch counts
- focused-run counts
- review-cycle limit
- recovery/stop thresholds
- durable outcome identity/reload/retry/partial-failure fields as applicable

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

No edits or new commits. In the current Householder workflow, this lane prepares or
verifies the trusted host-publisher handoff only when explicitly authorized.
Codex-side agents do not fetch, pull, push, `ls-remote`, or otherwise contact GitHub.

## Focused-First Contract Rules

Execution semantics are owned by `policy/execution-safety.md`.

For ordinary scoped work, use the simplified path.

For tasks with `Ledger progression required? yes`, apply the relevant ES rules including ES-08, ES-10, ES-11, ES-12, ES-13, and ES-14.

Task contracts may narrow authority but may not broaden canonical safety rules.
