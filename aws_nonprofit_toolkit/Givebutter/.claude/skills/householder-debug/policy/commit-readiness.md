# Commit Readiness and Push

## Readiness Packet

Commit-capable tasks use ignored runtime evidence:

```text
.artifacts/commit-readiness.json
```

Required fields:

```text
schema_version
task_id
reviewer_verdict
breaker_verdict
qa_verdict
canonical_gates_passed
scope_guard_passed
commit_authorized
push_authorized
reviewed_head
reviewed_diff_sha256
reviewed_at
informational_notes
required_changes
gate_results
authorized_exceptions
```

Schema version `2` requires an explicit gate ledger:

- `gate_results` records every declared canonical gate and lane guard with its
  `gate_id`, `group`, `command`, `required`, `status`, `exit_code`, and
  optional `exception_id`.
- `authorized_exceptions` records only structured, machine-readable exception
  records. Free-form prose cannot authorize a failed gate.
- `canonical_gates_passed` and `scope_guard_passed` must truthfully reflect the
  recorded gate results. A failed gate must never be hidden behind a `true`
  summary boolean.
- `commit_authorized` may be `true` only when the recorded failures are either
  absent or explicitly authorized by a matching structured exception that is
  independently verified against the current staged diff by the lane-guard
  runner. The lane guard must independently verify the normal pass path as well
  as the expected conflict exit code for authorized mixed-scope exceptions;
  crashes and other nonstandard exits fail closed.

Exact passing verdicts:

- `VERDICT=ACCEPT`
- `BREAKER=PASS`
- `QA=PASS`

`required_changes` must be empty.

The independent task identity comes from `HOUSEHOLDER_TASK_ID` and must equal `task_id`.

## Staged Diff Fingerprint

Fingerprint the exact bytes of:

```bash
git diff --cached --binary --full-index --no-ext-diff HEAD
```

with SHA-256 from the Git repository root.

The packet must be ignored and unstaged.
Immediately before commit, verify:

- current HEAD equals `reviewed_head`;
- staged fingerprint equals `reviewed_diff_sha256`;
- staged files exactly match expected scope.

Any diff change after review requires fresh verdicts and a new packet.

## Commit Gate

Requires exact prompt phrase:

```text
Happy-path auto-commit: enabled
```

Also requires:

- exact passing verdicts for all required roles;
- canonical gates pass;
- artifact, lane, and exact scope guards pass;
- fast pre-commit unit/integration gate passes;
- no unresolved product, schema, security, raw-data, audit, approval, export, persistence, or workflow issue;
- readiness packet validates;
- no unexpected files;
- no `--no-verify`;
- no amend unless explicitly authorized.

A successful commit is terminal unless an explicit autonomous P1 campaign contract says it is a checkpoint.

## Push Gate

Requires exact prompt phrase:

```text
Happy-path auto-push: enabled
```

or other explicit current push authorization.

Push is separate from commit, never inferred, and must not use force unless explicitly authorized.
