# Householder Policy Index

`SKILL.md` is the canonical entry point. These modules contain the detailed rules.

- `task-contract.md` — task classification, lanes, authorization, required agents, terminal state.
- `execution-safety.md` — assessment firewall, review capability, environment recovery, failed gates, restart/resume, reasoning escalation.
- `durable-outcomes.md` — complete stateful P1 transaction proof and authoritative identity.
- `deep-bug-analysis.md` — trace-first root-cause proof and runtime-path verification.
- `e2e-evidence.md` — E2E stages, real-path evidence, timeouts, reliability, harness stabilization.
- `review-and-verdicts.md` — Reviewer/Breaker/QA responsibilities, exact tokens, handoffs, terminal verdicts.
- `commit-readiness.md` — readiness packet, fingerprints, commit and host-publication gates.
- `github-workflow-acceptance.md` — clean-runner, host-publication, and live GitHub Actions requirements.

Precedence:

1. `SKILL.md`
2. applicable policy modules
3. task-specific campaign skill
4. role-specific agent files
5. local prompt/task contract

A lower-precedence file may narrow authority but may not broaden or override canonical rules.
