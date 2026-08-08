# Householder / DonorTrust Codex Instructions

Before implementation, test, workflow/CI, product/invariant, or commit-capable work:

1. Read `.claude/skills/householder-debug/SKILL.md`.
2. Read every policy module required by its task-condition table.
3. Instantiate the mandatory task contract.
4. Verify Reviewer/Breaker subagent capability when required.
5. Bootstrap from the Givebutter directory and use its `.venv`.

## Stateful P1

Define and prove:

- upstream action;
- durable business outcome;
- authoritative identity;
- commit boundary;
- downstream handoff;
- reload behavior;
- configuration defaults;
- duplicate/retry/stale/partial-failure behavior;
- exact transaction-level test.

Do not accept UI text, HTTP success, queue-row creation, or isolated component tests as sufficient proof.
Do not use filename, label, timestamp, list position, or newest-first ordering as authoritative identity.

## Review Capability

Policy files existing on disk do not prove Reviewer/Breaker can be invoked.
Do not substitute self-review or auto-commit when required agents are unavailable.

## Current reviewer-disposition rules

The current product rules in `.claude/skills/householder-debug/SKILL.md` are authoritative.

In particular:

- `Defer` has been removed from the user-facing disposition model.
- Clean rows use a system `Accept as-is` disposition without creating a human review record.
- Issue-bearing rows start at `No disposition` unless a saved human disposition exists.
- Human `Accept as-is` preserves issues and requires reviewer name plus non-empty Reason / notes.
- `Needs follow-up` and `Reject row` remain in the batch but are excluded from the current export.
- Only issue-bearing `No disposition` blocks finalization.
- Raw data remains immutable and review history remains append-only.

Do not restore stale `Defer` behavior from older tests, fixtures, or workflow documents.

## Assessment

Assessment-only work does not edit, test a fix, invoke implementation agents, commit, or push.

## Project Bootstrap

```bash
GIVEBUTTER_DIR="/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter"
cd "$GIVEBUTTER_DIR"
export PATH="$GIVEBUTTER_DIR/.venv/bin:$PATH"
```

Use canonical policy for environment recovery, failed gates, E2E, review, readiness, workflow acceptance, commit, and push.

## Publication boundary

Codex-side agents must not contact GitHub from the sandboxed runtime: no fetch, pull, push, ls-remote, remote update, or equivalent remote Git command.
Validated local commits are published by the host-owned SSH publisher using an exact-SHA, lease-verified handoff.
