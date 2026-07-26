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

## Assessment

Assessment-only work does not edit, test a fix, invoke implementation agents, commit, or push.

## Project Bootstrap

```bash
GIVEBUTTER_DIR="/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter"
cd "$GIVEBUTTER_DIR"
export PATH="$GIVEBUTTER_DIR/.venv/bin:$PATH"
```

Use canonical policy for environment recovery, failed gates, E2E, review, readiness, workflow acceptance, commit, and push.
