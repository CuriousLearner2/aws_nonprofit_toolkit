---
name: householder-debug
description: Orchestrates a disciplined Householder / DonorTrust bug-fix loop using the implementer and reviewer agents.
allowed-tools: Read, Grep, Glob, Bash, Task
---

# Householder Debug Skill

This is the canonical workflow policy for the Householder / DonorTrust project. Agent files are role-specific summaries and must not override this file.

## Start Here / Priority Order

Apply rules in this order:

1. **Task contract first.** Classify task, lane, allowed files/actions, required agents, gates, and terminal state before meaningful work.
2. **Project invariants always win.** The system suggests. The reviewer decides. Raw data stays unchanged.
3. **Failed gates stop immediately.** No diagnosis, retry, split, second fix, Reviewer, Breaker, commit, or push without new human authorization.
4. **Required handoffs are actions.** Passing gates means invoke required Reviewer/Breaker; `Ready for Reviewer` is not terminal.
5. **Non-accept verdicts are terminal.** Reviewer `Request changes` / `Reject` and Breaker `P1/P0/FAIL` require a new human-authorized remediation task.
6. **Commit and push remain separate.** Auto-commit requires the exact phrase `Happy-path auto-commit: enabled`; push requires separate explicit authorization.

## RED RULES — ALWAYS OBEY

1. **Assessment-only:** Orchestrator performs it directly. No child agents, no edits, and stop at the assessment report.
2. **Any failed, hung, timed-out, interrupted, unusable/truncated, or exit-143 gate:** stop immediately. No diagnosis, retry, split, second fix, Reviewer, Breaker, commit, or push without human authorization.
3. **E2E gates require explicit wall-clock timeouts:** 90s single test, 180s full file, 90s per reliability iteration unless a stricter task-specific gate is declared. Multi-test pytest gates must use `-x` or `--maxfail=1`.
4. **Timeout equals failed gate.** Treat it exactly like a test failure and deliver a failed-gate stop report.
5. **Rewritten E2E tests require hard assertions.** No soft guards, no `if element: assert ...`, no print/networkidle-only success, no zombie tests, and no page-load-only replacement coverage.
6. **Reviewer handoff:** For implementation flows requiring review, Implementer stops at ready-for-review and Orchestrator invokes Reviewer after passing gates. Do not invoke Reviewer for assessment-only, push-only, or status-only tasks unless explicitly required.
7. **Terminal states stop:** assessment report, failed-gate report, cleanup completed, non-accept Reviewer verdict, Breaker P1/P0/FAIL, commit, and push. Do not auto-start the next task.
8. **Breaker is concrete-risk-based, not routine.** Invoke only for concrete P0/P1 invariant or process-integrity risk, when Lane D/product risk requires it, or when the human asks.

## Mandatory Task Contract

Before meaningful work, Orchestrator must instantiate this contract with explicit yes/no answers:

```text
Task contract:
- Task type: Assessment only / Implementation only / Commit preparation / Push only
- Pre-authorized lane: Assessment-only / test-only hardening / workflow/CI automation / product/invariant hardening / Push only / none
- Allowed actions:
- Forbidden actions:
- Files in scope:
- Product UX ambiguity present? yes/no
- Product UX Gatekeeper required? yes/no
- Reviewer required? yes/no
- Why Reviewer is/is not required:
- Breaker required? yes/no
- Why Breaker is/is not required:
- E2E involved? yes/no
- E2E timeout required? yes/no
- Gate command(s):
- Stop condition:
- Terminal state:
```

Rules:
- Do not proceed until the contract is written.
- If any field is uncertain, stop and ask or classify as assessment-only.
- If the task is assessment-only, push-only, or status-only, Reviewer must be `no` unless explicitly required by the human.
- If the task is an implementation flow requiring review, Reviewer must be `yes`, and Orchestrator must invoke Reviewer after passing gates.
- Lane classification must match an exact lane trigger phrase; do not infer a lane.

## Core Project Invariants

The system suggests. The reviewer decides. Raw data stays unchanged.

Hard boundaries:
- No CRM/Givebutter API calls or writeback.
- No credentials, auth/RBAC changes, background jobs, bulk actions, or new export formats.
- No raw source-data mutation.
- No contact merge/delete, household_id assignment, cross-import matching, or master contacts/households.
- Preserve append-only audit behavior.
- Do not change schema/migrations unless explicitly authorized.
- Do not approve broad unrelated refactors.

## Laptop/Desktop Product Scope

The Householder / DonorTrust app is intended for web/laptop/desktop use only. Mobile and tablet viewport support are out of product scope unless the human explicitly authorizes them.

Agents must not recommend mobile/tablet viewport coverage as a default hardening task, and must not create mobile/tablet E2E coverage, responsive-design tasks, or responsive CSS/template work unless explicitly authorized. Standard browser-visible coverage should assume normal laptop/desktop browser use. This does not prevent fixing layout or usability issues that affect normal laptop/desktop browser use.

## Source of Truth

Repo-local workflow files are authoritative:

```text
.claude/skills/householder-debug/SKILL.md
.claude/agents/orchestrator.md
.claude/agents/implementer.md
.claude/agents/reviewer.md
.claude/agents/breaker.md
.claude/agents/product-ux-gatekeeper.md
```

Global files under `~/.claude/` are optional mirrors only. Do not modify workflow files during product implementation. Workflow-file edits are handled by ChatGPT unless the human explicitly authorizes a Claude workflow-configuration task.

## Pre-authorized Workflow Lanes

Lanes define maximum allowed scope and approval flow. They do not bypass gates, Reviewer, Breaker, lane scope, exact scope, or terminal-state rules.

**Lane A — Assessment only**
- Trigger: `Task type: Assessment only`
- No edits, no child agents, stop at assessment report.

**Lane B — Test-only hardening**
- Trigger: `Pre-authorized lane: test-only hardening`
- Allowed: explicit test files only.
- No product code, templates, routes, workflow files, CI scripts, or schema changes.
- Flow: implementation → gates → Reviewer → commit if clean and auto-commit enabled.

**Lane C — Workflow/CI automation**
- Trigger: `Pre-authorized lane: workflow/CI automation`
- Allowed: explicit `.claude/**`, `.github/**`, `scripts/ci/**`, and related tests only.
- No product code.
- Flow: implementation → gates → Reviewer → commit if clean and auto-commit enabled.

**Lane D — Product/invariant hardening**
- Trigger: `Pre-authorized lane: product/invariant hardening`
- Scope: explicit per task; may include product/test/docs.
- Product UX Gatekeeper required when visible behavior/semantics are ambiguous.
- Breaker required after Reviewer Accept for concrete P0/P1 invariant risk, export/audit/raw-data risk, or when declared in the task.
- Flow: implementation → gates → Reviewer → Breaker if required → commit if clean and auto-commit enabled.

**Lane E — Push only**
- Trigger: `Task type: Push only`
- No edits or new commits; push only if explicitly authorized.

Intentional tradeoff: `Happy-path auto-commit: enabled` is required for all lanes, including Lane B/C. This preserves safety over speed because test-only/workflow-only tasks can still create false confidence, evidence gaps, or process drift.

## Repository Automation Guardrails

Run guardrails in this order for implementation and commit-prep flows:

**A. Artifact Guard**
```bash
python scripts/ci/check_no_artifacts.py
```

**B. Lane Scope Guard**
```bash
python scripts/ci/check_lane_scope.py --lane <lane>
```
Lane mapping: `assessment`, `test-only`, `workflow-ci`, `product`, `push-only`. If it fails, stop and report; do not recategorize, clean up, or continue without human authorization.

**C. Scope Guard**
```bash
python scripts/ci/check_scope.py --allow <expected file> ...
```
Must list each expected changed file explicitly. Do not use broad patterns like `--allow tests/**`, `.claude/**`, or `**` unless explicitly authorized.

**D. Test Gate Wrapper**
```bash
python scripts/ci/test_gate.py --timeout N -- pytest <args>
```
Required for unit, integration, and targeted non-E2E pytest gates in implementation flows. Timeout exit code 124 is a failed gate.

**E. E2E Gate Wrapper**
```bash
python scripts/ci/e2e_gate.py --timeout N -- pytest <args>
```
Required for E2E gates. Multi-test E2E gates must use `-x` or `--maxfail=1`.

## Gate Rules

A declared gate is binary. It passes only when the declared command exits 0. If it exits nonzero, hangs, times out, exits 143, is interrupted, or produces unusable/truncated output, it failed unless the task was explicitly assessment-only or failures are proven pre-existing and unrelated with baseline evidence.

After a failed gate: stop command execution, do not inspect/grep/rerun/split/diagnose/repair/continue, do not invoke Reviewer/Breaker, and do not commit or push.

Failed-gate report:

```text
Failed Gate Stop Report
Declared gate:
Exact command:
Exit code / timeout:
Last observed output:
Passed/failed/skipped:
Modified files:
Gate accepted? no
Failed-first-fix triggered? yes/no
Reviewer allowed? no
Breaker allowed? no
Commit allowed? no
Push allowed? no
No further diagnosis performed because the gate failed.
Next human choices:
1. Revert current changes
2. Preserve unstaged changes and authorize rescope assessment
3. Authorize a new implementation/debug task
```

## E2E Proof-Step Rules

For E2E rewrites, migrations, selector/timing changes, browser fixture changes, or async-heavy UI work, use:

```text
Assessment → one-test proof → small batch → whole file → reliability evidence → Reviewer
```

Rules:
- Prove one representative test before modifying a whole E2E file.
- Do not re-plan/re-run passed stages unless evidence is stale, scope changed, a gate failed/flaked, or a new concrete risk appears.
- Every rewritten E2E test must use hard selector preconditions and hard assertions.
- Reliability loops must use explicit timeout, fail-fast, and stop on first failure.
- If product behavior cannot be proven deterministically, report product/test mismatch and stop instead of weakening the test.

## Required Handoff State Machine

```text
Implementer ready-for-review + gates passed
→ Orchestrator invokes Reviewer
→ Reviewer Accept?
   no: stop (Request changes/Reject is terminal)
   yes: Breaker required?
       no: commit if auto-commit eligible
       yes: Orchestrator invokes Breaker
           Breaker PASS/P2 follow-up only?
              no: stop (Breaker P1/P0/FAIL is terminal)
              yes: commit if auto-commit eligible
→ commit completed is terminal
```

Non-terminal status phrases:
- `Ready for Reviewer`
- `Ready for review`
- `Review Packet prepared`
- `Awaiting Reviewer verification`
- `Implementation complete`
- `Ready for Reviewer + Breaker verification`
- `Reviewer task started but verdict not reported`
- `Breaker required but not invoked`

If Reviewer is required and gates passed, invoke Reviewer. If Reviewer returns clean Accept and Breaker is required, invoke Breaker. These are required actions, not optional human approvals.

## Reviewer Request Changes / Reject Boundary

Reviewer `Request changes` and `Reject` are terminal states for the current task. They are not permission to return to Implementer, apply an obvious fix, expand scope, rerun gates, invoke Breaker, commit, or push.

Any remediation requires a new explicit human-authorized task. If remediation touches files outside the prior expected-file allowlist, the new human authorization must name the expanded files.

## Breaker P1/P0/FAIL Boundary

Breaker `P1 found`, `P0 found`, or `FAIL` blocks commit. Do not fix, rerun, or commit until the human explicitly authorizes a new remediation task. Breaker PASS or P2 follow-up only may proceed to commit if Reviewer accepted and commit gates are satisfied.

## Product UX Gatekeeper Triggers

Invoke Product UX Gatekeeper when a real product/UX decision is unresolved. Deterministic triggers:
- new visible control,
- changed control label,
- changed status/warning/blocker semantics,
- approval/export behavior change,
- notes required vs optional,
- navigation after a reviewer decision,
- disabling/hiding/removing visible controls,
- Defer vs Skip or system state vs human disposition choices,
- confirmation/checkbox/modal behavior,
- any “should/how/best UX/would it be better” question.

Do not invoke Product UX Gatekeeper for mechanical implementation of an already-approved decision, code correctness, docs-only, test-only, commit-prep, or push-only work unless a concrete product ambiguity remains. Product UX approval does not bypass Reviewer, Breaker, commit, or push gates.

## Review Levels

**Level 1 Fast Review** — docs-only, workflow-only, test-only, or tiny low-risk changes with complete evidence. Delta review only.

**Level 2 Standard Review** — normal product/test changes, review-screen UI, autosave, modals, export warnings, audit visibility, and E2E infrastructure.

**Level 3 Deep Review** — export correctness, raw-data immutability, audit integrity, state machines, persistence architecture, schema/data-model, generated CSV, or multi-file architecture.

Reviewers/Breakers report verified items, unverified items, blockers, and readiness impact. Timebox language is guidance, not a reason to skip required checks.

## Role Ownership

- **Orchestrator:** task contract, lane selection, sequencing, gates, evidence, Product UX routing, Reviewer/Breaker invocation, commit/push authorization.
- **Implementer:** smallest safe change, test-first discipline, targeted gates, ready-for-review handoff. No staging, commit, or push.
- **Reviewer:** implementation correctness, evidence validity, scope/lane verification, gate compliance, hard assertions, and auto-commit eligibility.
- **Breaker:** P0/P1 adversarial invariant risks: raw data mutation, audit append-only, export correctness, approval/export bypass, failed autosave leakage, misleading UI state, and overclaimed coverage that affects readiness.
- **Product UX Gatekeeper:** product/UX ambiguity decisions only. Human remains final product authority.

## Feature Development Prompt Pattern

Feature/product behavior work should normally use Orchestrator with `Pre-authorized lane: product/invariant hardening`.

Feature prompts should name exact expected files whenever possible and enforce lane scope, exact scope, bounded tests through `test_gate.py`/`e2e_gate.py`, Product UX Gatekeeper when triggers apply, Reviewer before commit, and Breaker after Reviewer Accept when P0/P1 risk exists.

Product changes must protect: **The system suggests. The reviewer decides. Raw data stays unchanged.**

## Commit Gate

Auto-commit is disabled unless the prompt includes exactly:

```text
Happy-path auto-commit: enabled
```

Commit only when all are true:
- Reviewer verdict is exactly `Accept`.
- Reviewer states `Happy-path auto-commit eligible? yes`.
- Breaker PASS/P2 follow-up only if Breaker was required.
- All required gates passed.
- Artifact guard passed.
- Lane scope guard passed with the declared lane.
- Scope guard passed with exact expected files.
- Fast pre-commit passed: `pytest tests/unit tests/integration -q --tb=short`.
- Staged files exactly match expected files.
- No unresolved product questions, schema concerns, failed-first-fix violation, or workflow violation.

Do not commit on `Accept with minor follow-up`, `Request changes`, `Reject`, Breaker P1/P0/FAIL, missing evidence, failed tests, unexpected files, or unresolved product questions.

## Push Gate

Auto-push is disabled unless the prompt includes exactly:

```text
Happy-path auto-push: enabled
```

`Ready to push? yes` is a status report, never permission. Push only in a push-only task or when the human explicitly authorizes it.

## Output Discipline

Keep reports short, structured, and evidence-based. Include readiness fields when relevant:

```text
Acceptance gate passed? yes/no
Failed-first-fix triggered? yes/no
Reviewer invoked? yes/no
Reviewer verdict:
Breaker invoked? yes/no
Breaker verdict:
Ready for Reviewer? yes/no
Ready for commit prep? yes/no
Ready to push? yes/no
```
