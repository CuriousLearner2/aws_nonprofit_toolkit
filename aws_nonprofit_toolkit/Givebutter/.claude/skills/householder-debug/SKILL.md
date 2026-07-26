---
name: householder-debug
description: Canonical workflow entry point for Householder / DonorTrust implementation, testing, review, commit, and push work.
allowed-tools: Read, Grep, Glob, Bash, Task
---

# Householder Debug Skill

This file is the canonical entry point. Detailed rules live in `policy/` modules.
Role files are role-specific summaries and must not override this skill or its modules.

## Priority Order

1. Write the task contract before meaningful work.
2. Preserve project invariants: the system suggests, the reviewer decides, raw data stays unchanged.
3. Assessment-only work stops at assessment.
4. Failed gates stop unless the exact authorized recovery rule applies.
5. Required Reviewer, Breaker, and QA handoffs are actions, not optional status.
6. Non-accept verdicts are terminal for the current task.
7. Commit and push require separate explicit authorization.
8. When a stateful P1 is involved, prove the complete durable transaction.

## Mandatory Policy Loading

Before meaningful work, read the policy modules required by the task:

| Task condition | Required modules |
|---|---|
| Every task | `policy/task-contract.md`, `policy/execution-safety.md` |
| Stateful P1 or persistence | `policy/durable-outcomes.md` |
| Cross-layer bug or ambiguous root cause | `policy/deep-bug-analysis.md` |
| Browser/E2E work | `policy/e2e-evidence.md` |
| Reviewer, Breaker, QA, or commit-capable work | `policy/review-and-verdicts.md` |
| Commit-capable work | `policy/commit-readiness.md` |
| `.github/workflows/**` changes | `policy/github-workflow-acceptance.md` |
| P1 acceptance campaign | `.claude/skills/p1-acceptance-campaign/SKILL.md` |

If a required module cannot be read, stop and report the missing policy file.

## Core Project Invariants

- No CRM/Givebutter API calls or writeback.
- No credentials, auth/RBAC changes, background jobs, bulk actions, or new export formats.
- No raw source-data mutation.
- No contact merge/delete, household assignment, cross-import matching, or master records.
- Preserve append-only audit behavior.
- No schema/migration changes unless explicitly authorized.
- No broad unrelated refactors.
- Product scope is laptop/desktop unless the human explicitly authorizes mobile/tablet work.

## Mandatory Task Contract

Use the exact contract in `policy/task-contract.md`.
Do not proceed until every required field is explicit.

## Required State Machine

```text
Task contract
→ implementation or assessment
→ canonical gates
→ Reviewer when required
→ Breaker when required
→ QA when required
→ readiness packet
→ commit when explicitly authorized
→ push when separately authorized
```

Terminal blockers include:

- assessment complete;
- failed gate without qualifying recovery;
- unresolved reasoning escalation;
- scope overflow or unexpected file;
- Reviewer not `VERDICT=ACCEPT`;
- Breaker not `BREAKER=PASS`;
- QA not `QA=PASS`;
- commit complete, unless an explicit autonomous P1 campaign exception applies;
- push complete.

## Exact Verdict Tokens

- Reviewer: `VERDICT=ACCEPT`, `VERDICT=REQUEST_CHANGES`, `VERDICT=REJECT`
- Breaker: `BREAKER=PASS`, `BREAKER=FAIL`
- QA: `QA=PASS`, `QA=FAIL`

Qualified or unknown verdicts are invalid.

## Authorization Phrases

Auto-commit requires the exact phrase:

```text
Happy-path auto-commit: enabled
```

Auto-push requires the exact phrase:

```text
Happy-path auto-push: enabled
```

Push is never inferred from commit success.

## Project Command Bootstrap

```bash
GIVEBUTTER_DIR="/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter"
cd "$GIVEBUTTER_DIR"
export PATH="$GIVEBUTTER_DIR/.venv/bin:$PATH"
command -v python
command -v pytest
python -c "import sys; print(sys.executable)"
```

Use `./.venv/bin/python` for project gates and guards unless a policy module explicitly authorizes another interpreter.

## Guard Order

```bash
./.venv/bin/python scripts/ci/check_no_artifacts.py
./.venv/bin/python scripts/ci/check_lane_scope.py --lane <lane>
./.venv/bin/python scripts/ci/check_scope.py --allow <exact file> ...
```

Use exact task-specific allow paths. Broad allowlists are not acceptable unless explicitly authorized.

## Canonical Gate Wrappers

Non-E2E:

```bash
./.venv/bin/python scripts/ci/test_gate.py --timeout N -- pytest <args>
```

E2E:

```bash
./.venv/bin/python scripts/ci/e2e_gate.py --timeout N -- pytest <args>
```

Multi-test E2E gates require `-x` or `--maxfail=1`.

## Output Discipline

Keep reports concise and include, when relevant:

```text
Acceptance gate passed? yes/no
Failed-first-fix triggered? yes/no
Reviewer invoked? yes/no
Reviewer verdict:
Breaker invoked? yes/no
Breaker verdict:
QA invoked? yes/no
QA verdict:
Ready for commit prep? yes/no
Ready to push? yes/no
```
