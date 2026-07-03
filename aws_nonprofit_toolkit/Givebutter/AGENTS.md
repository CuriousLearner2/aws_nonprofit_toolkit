# Householder / DonorTrust Codex Instructions

Before any implementation, test-only hardening, workflow/CI automation, product/invariant hardening, or auto-commit-capable task:

1. Read `.claude/skills/householder-debug/SKILL.md` as canonical workflow policy.
2. Instantiate the task contract required by `SKILL.md`.
3. Run session review-capability preflight:
   - spawn custom Codex subagent `reviewer` and confirm it is callable,
   - spawn custom Codex subagent `breaker` and confirm it is callable.

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
