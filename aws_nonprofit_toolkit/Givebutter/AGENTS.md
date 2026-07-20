# Householder / DonorTrust Codex Instructions

Before any implementation, test-only hardening, workflow/CI automation, product/invariant hardening, or auto-commit-capable task:

1. Read `.claude/skills/householder-debug/SKILL.md` as canonical workflow policy.
2. Instantiate the task contract required by `SKILL.md`.
3. Run session review-capability preflight:
   - spawn custom Codex subagent `reviewer` and confirm it is callable,
   - spawn custom Codex subagent `breaker` and confirm it is callable.

## Reasoning Escalation

Use the standard efficient reasoning setting for routine, well-understood work. Do not repeatedly guess when evidence is contradictory, ambiguous, cross-layer, or production-sensitive.

When escalation is warranted:
- preserve the worktree, failing tests, logs, and current evidence;
- first delegate the narrow difficult question to a stronger or unpinned subagent when available;
- if stronger main-task reasoning is still required, stop with the structured `REASONING ESCALATION REQUIRED` report defined in `SKILL.md`;
- do not edit production code while an unresolved escalation is pending;
- return to the standard efficient setting once the difficult question is resolved and the remaining work is mechanical.

Model names and UI controls are intentionally not hardcoded. The policy is capability-based and must remain valid as available models change.

Rules:
- If Reviewer is required and `reviewer` cannot be spawned, stop before editing.
- If Breaker is required or likely required and `breaker` cannot be spawned, stop before editing unless the task can safely proceed only through Reviewer and stop before Breaker.
- Do not treat `.claude/agents/reviewer.md` or `.claude/agents/breaker.md` existing on disk as proof that Reviewer/Breaker are callable.
- Do not substitute self-review or “Reviewer-style” review for the dedicated Reviewer subagent.
- Do not auto-commit when a required Reviewer/Breaker subagent is unavailable.
- Reviewer/Breaker may be waived only by explicit human authorization for that specific task.

For assessment-only, push-only, or status-only tasks:
- do not spawn Reviewer/Breaker unless explicitly required by the human or by `SKILL.md`;
- still read `SKILL.md` and obey the task contract.
