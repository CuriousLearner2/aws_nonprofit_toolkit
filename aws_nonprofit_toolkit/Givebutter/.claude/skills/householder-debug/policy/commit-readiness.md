# Commit Readiness and Host Publication

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
- `authorized_exceptions` records only genuine structured exceptions. `BASELINE_DEBT_VERIFIED` is not an exception; it is a first-class gate result for pre-existing broad-suite failures proven by baseline/current comparison. Free-form prose cannot authorize a failed gate.
- `canonical_gates_passed` and `scope_guard_passed` must truthfully reflect recorded results. A broad-suite gate may count as satisfied when its status is `BASELINE_DEBT_VERIFIED`; new failures or unverified failures remain blocking.
- `commit_authorized` may be `true` only when all required gates are satisfied by `PASS` or valid `BASELINE_DEBT_VERIFIED`, or when a separately supported structured exception is independently verified. New or unexplained failures fail closed.

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
- each canonical gate is either PASS or a valid `BASELINE_DEBT_VERIFIED` result for a pre-existing broad-suite failure;
- artifact, lane, and exact scope guards pass;
- fast pre-commit unit/integration gate passes;
- no unresolved product, schema, security, raw-data, audit, approval, export, persistence, or workflow issue;
- readiness packet validates;
- no unexpected files;
- no `--no-verify`;
- no amend unless explicitly authorized.

A successful commit is terminal unless an explicit autonomous P1 campaign contract says it is a checkpoint.

## Host Publication Gate

Requires exact prompt phrase:

```text
Happy-path auto-push: enabled
```

or other explicit current publication authorization.

For Householder's current local-development workflow, `push_authorized` is retained
for readiness-packet/schema compatibility but authorizes only creation of the
host-publisher handoff. Codex-side agents must not contact GitHub or execute remote
Git commands.

Remote publication is performed by the trusted host SSH publisher after local commit.
The host publisher must independently fetch, verify the expected remote baseline,
push the exact commit with an explicit lease, refetch, verify the target ref, and
verify `origin/main` is unchanged.

Publication is separate from commit, never inferred, and must not use force without
the publisher's explicit lease guard.


## Required roles

Readiness requires receipts only for roles required by the current task contract.

- Reviewer required → `VERDICT=ACCEPT` required.
- Reviewer cannot be disabled by empty, malformed, or unknown role configuration.
- Breaker required → `BREAKER=PASS` required.
- Breaker not required → no Breaker receipt required.
- QA required → `QA=PASS` required.
- QA not required → no QA receipt required.
- Empty/unknown required-role configuration fails closed.

## Baseline debt

A canonical broad-suite gate may be recorded as `BASELINE_DEBT_VERIFIED` only when:
- the exact same command/environment ran on an untouched baseline and current worktree;
- baseline SHA is recorded;
- current staged fingerprint is recorded;
- current introduces no new failing test identities;
- the comparison is machine-readable;
- Reviewer accepts the evidence.

This is a normal evidence state, not an exception.

## Commit gate behavior

The commit gate verifies existing valid evidence; it must not recreate already-valid evidence, require non-required role receipts, or block solely on verified pre-existing baseline failures.
