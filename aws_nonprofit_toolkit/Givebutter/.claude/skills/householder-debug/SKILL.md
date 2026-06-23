---
name: householder-debug
description: Orchestrates a disciplined Householder / DonorTrust bug-fix loop using the implementer and reviewer agents.
allowed-tools: Read, Grep, Glob, Bash, Task
---

# Householder Debug Skill

Use this skill for Householder / DonorTrust bug fixes, review-screen issues, autosave issues, validation issues, approval/export issues, and small scoped implementation changes.

## Role ownership

### Orchestrator

- Owns sequencing, gates, evidence collection, review-level selection, Product UX Gatekeeper routing/reporting, and commit/push authorization enforcement.

### Implementer

- Owns the smallest safe fix, test-first discipline, targeted evidence, and ready-for-review handoff.

### Reviewer

- Owns diff/test/evidence correctness, scope control, required verification, and the final review verdict.

### Breaker

- Owns adversarial QA, invariant hunting, edge cases, misleading UI state, and P0/P1 workflow failures.
- Breaker is required for high-risk implementation tasks when the current change touches or materially affects validation review, inline editing/autosave, approval/export gating, decision modals, audit integrity, raw-data immutability, recently fixed P0/P1 paths, or browser-visible state consistency that could affect reviewer decisions. Breaker is not required for every adjacent or historical concern unless a concrete current-change invariant risk appears.
- Breaker is optional for docs-only, test-only, workflow-only, commit-prep, and push-only tasks unless the human explicitly asks, the Reviewer flags a concrete invariant concern, or the task touches a recently problematic bug class where adversarial review is useful.

### Product UX Gatekeeper

- Owns product/UX ambiguity only, including human product decision authority.
- Does not review code correctness.

## Review packet

Before review handoff, the Orchestrator must collect a Review Packet containing:

- task type
- review level
- changed files
- intended behavior
- non-goals
- exact diff anchors for changed functions, helpers, and tests
- test/evidence commands and results
- known caveats
- proven claims
- claims not being made
- Product UX Gatekeeper status:
  - ambiguity present? yes/no
  - invoked? yes/no
  - if not invoked, reason
  - human product decision needed? yes/no

The Review Packet is the shared review contract. Reviewers and Breakers should use its anchors before broadening scope.

## Product UX Gatekeeper routing heuristic

Invoke the Product UX Gatekeeper when the task or prompt contains product-choice language such as:

- should we
- how should
- what should happen
- best UX
- would it be better

Also invoke it when:

- multiple reasonable user-visible workflows exist
- the change affects what reviewers can see, decide, approve, defer, override, export, or navigate
- the change affects visible controls, status semantics, warnings, blockers, notes requirements, approval/export confirmation, or decision semantics
- implementing the task requires choosing between remove, disable, hide, label unavailable, or fully implement

Do not invoke it when:

- the human has already explicitly specified the expected behavior
- the task is purely mechanical docs-only or test-only work and does not change reviewer-visible behavior
- the task is commit-prep only or push-only
- the question is code correctness rather than product behavior

The Orchestrator must still report:

- Product ambiguity present? yes/no
- Product UX Gatekeeper invoked? yes/no
- if not invoked, reason
- human product decision needed? yes/no

## Workflow violation handling

A workflow violation blocks auto-commit and auto-push until the violation is resolved or explicitly waived by the human.

The Orchestrator must report workflow violations to the human and let the human decide whether to continue, revert, fix forward, or create a separate task.

Examples of workflow violations include:

- unauthorized push
- missing required evidence
- unexpected files
- bypassed gates

The Reviewer may still judge code correctness, but the workflow is not clean until the violation is resolved or explicitly waived by the human.

## Efficient orchestration rule

Efficiency means using the smallest sufficient workflow, not skipping required gates.

Orchestrator must optimize for less wasted work by:

- choosing the minimum review level that fits the risk,
- avoiding unnecessary agents,
- avoiding broad repo archaeology,
- avoiding duplicate Reviewer/Breaker work,
- accepting valid current evidence instead of rerunning expensive tests without a reason,
- keeping reports concise and evidence-based.

Efficiency must never be used as a reason to skip or defer:

- Reviewer when implementation changed files and review is required,
- Breaker when required by risk or explicitly requested,
- Product UX Gatekeeper when product ambiguity exists,
- full-file five-run E2E when an E2E file changed materially,
- required verification commands,
- returning a Reviewer-requested fix to Reviewer for final verdict,
- commit when the task says to commit if clean and all gates pass,
- push only when explicitly authorized.

If a task says `Agent to use: Orchestrator`, Orchestrator remains responsible until the requested terminal state is reached:

- final assessment,
- Reviewer verdict,
- Reviewer + Breaker verdicts,
- committed if clean,
- or pushed if explicitly authorized.

Do not interpret human requests to “be efficient,” “move faster,” or “avoid too many agents” as permission to exit Orchestrator flow, self-implement outside the requested agent flow, skip required Reviewer/Breaker gates, skip required evidence, or stop at an intermediate handoff state.

## Review verdict meanings

- `Accept` — the change is correct, evidence is sufficient, and no blocking issue remains.
- `Accept with minor follow-up` — the change is safe to commit; the follow-up is non-blocking and can be handled separately.
- `Request changes` — the issue is fixable within the same task or a next authorized loop without changing the core product decision or approach.
- `Reject` — the approach is unsafe, wrong, overbroad, product-ambiguous, missing required evidence in a way that invalidates the task, or needs redesign/fresh task.

`Accept with minor follow-up` is not a clean happy path. Happy-path auto-commit eligibility remains `no` unless the Reviewer explicitly returns clean `Accept`.

## Breaker loop and escalation policy

At most two Implementer/Reviewer loops are allowed by default.

If two loops are exhausted and issues remain, the Orchestrator must stop and ask the human.

The Orchestrator must not silently start a third loop.

Stopping after two loops is not itself a workflow violation. It becomes a workflow violation only if the Orchestrator continues without human approval.

## Review levels

### Level 1 Fast Review

Use for:

- test-only changes
- docs-only changes
- workflow-only changes
- tiny low-risk changes with complete evidence

Target:

- Reviewer: about 90 seconds
- Breaker: about 90 seconds
- Combined if parallel: about 3-4 minutes

Rules:

- Delta review only.
- Inspect changed files and Review Packet anchors first.
- Do not inspect unrelated product code or historical tests unless a concrete concern appears.
- Do not rerun tests when supplied evidence is complete and consistent.

### Level 2 Standard Review

Use for:

- normal product/test changes in known areas
- Validation Review UI behavior
- autosave behavior
- row status logic
- modal behavior
- export blockers/warnings
- audit visibility
- small backend service changes with targeted tests

Target:

- Reviewer: about 2-3 minutes
- Breaker: about 3-4 minutes
- Combined if parallel: about 5-7 minutes

Required Level 2 Review Packet fields:

- changed files
- changed functions, helpers, and tests
- affected invariant category:
  - UI feedback
  - autosave/persistence
  - row status/issues
  - audit
  - approval/export
  - raw data
  - navigation/modal
- direct test evidence
- nearby tests affected
- explicit non-goals
- Product UX Gatekeeper status

Rules:

- Use anchored review.
- Inspect changed product code and directly affected tests first.
- Inspect adjacent directly-called code only when needed.
- Do not inspect unrelated historical tests by default.
- Do not rerun tests when supplied evidence is complete and consistent.
- Reviewer focuses on implementation correctness, scope control, test relevance, evidence validity, and maintainability as it affects the current diff's reviewability, code/test quality, scope, and risk. Reviewer should not request broad architecture cleanup or unrelated refactoring as part of maintainability review.
- Breaker focuses on named invariant failure modes, changed-path edge cases, stale async/UI state, raw-data/export/audit/persistence risk, and overclaimed coverage.
- Reviewer and Breaker should not duplicate each other's full review. Reviewer should not perform full adversarial QA unless Breaker is unavailable; Breaker should not re-review general maintainability unless it affects a failure mode.
- Escalate to Level 3 only if there is a concrete risk to raw data, audit, export, persistence, approval state, or misleading UI feedback.

### Level 3 Deep Review

Use for:

- export correctness
- raw-data immutability
- audit integrity
- approval/rejection/defer state machines
- autosave/persistence architecture
- schema/data-model changes
- generated CSV behavior
- multi-file architectural changes

Target:

- about 10-12 minutes unless a concrete blocker requires more time

Required staged process:

Stage 1 — Risk triage, 3-4 minutes:

- identify the top 3-5 invariants at risk
- identify changed files touching those invariants
- identify the highest-risk code paths
- identify tests/evidence that claim to cover those paths
- identify missing, stale, or contradictory evidence
- decide whether the review can be downgraded to Level 2

Stage 2 — Focused deep review, 7-8 minutes:

- inspect only the risk paths identified in Stage 1 unless a concrete concern requires expansion
- verify the highest-risk invariants against the supplied evidence and changed code
- report blockers, caveats, and unverified items instead of producing long narrative summaries

Allowed Level 3 expansion:

- evidence is missing, stale, or contradictory
- a product/test claim exceeds what the diff proves
- raw data, export, audit, approval, persistence, or UI feedback could be wrong
- a concrete P0/P1 risk is identified

Prohibited Level 3 behavior:

- unbounded repo archaeology
- reading all related tests "just in case"
- rerunning full suites without a specific reason
- duplicating Reviewer and Breaker work
- continuing beyond the timebox without reporting what remains unverified

If the target timebox is exceeded, the agent must stop and report what was verified, what remains unverified, whether the uncertainty is a blocker/caveat/non-blocking follow-up, and whether escalation or a human decision is needed.

## Canonical shared policies

### Evidence Acceptance Rule

Reviewer and Breaker may accept supplied test evidence without rerunning tests when all of the following are true:

- exact commands are shown
- results include collected/passed counts
- evidence was produced after the latest diff
- affected files match task scope
- there are no failures, skips, or unexplained warnings
- five-run E2E evidence is full-file when required

They must request rerun or escalate when:

- evidence predates the final diff
- commands are missing
- selected tests were run when full-file evidence was required
- failures are dismissed as environmental without proof
- product code changed but only insufficient tests were run
- claims exceed what the tests prove

### Review Budget Rule

### Timebox stop/report rule

Efficiency means bounded, focused review; it does not mean open-ended inspection.

Reviewer and Breaker must self-stop when the selected review-level timebox is exceeded. They must not wait for the human to interrupt.

If the timebox is exceeded, immediately report:

- what was verified,
- what remains unverified,
- whether each unverified item is blocking, caveat, or non-blocking follow-up,
- whether a concrete current-change P0/P1 risk was found,
- whether review, commit, or push readiness is blocked.

Continuing beyond the timebox is allowed only when:

- a concrete current-change P0/P1 risk has already been found and the extra inspection is limited to that risk path, or
- the human explicitly authorizes deeper review.

A timebox overrun without a stop report is a workflow violation. The violation does not automatically mean the code is wrong, but the workflow is not clean until the agent produces the required stop report or the human explicitly waives the violation.

For Level 2:

- Reviewer target: about 2-3 minutes.
- Breaker target: about 3-4 minutes.
- Hard stop/report threshold: 6 minutes unless a concrete current-change P0/P1 risk has already been identified.

For Level 3:

- Stage 1 risk triage target: about 3-4 minutes.
- Stage 2 focused review target: about 7-8 minutes.
- Hard stop/report threshold: 12 minutes unless the human explicitly authorizes deeper review.


Reviewer and Breaker must start with the smallest sufficient review:

1. changed files
2. changed functions/tests
3. adjacent directly-called code
4. existing tests only if the new tests depend on them
5. broader repo search only if a concrete concern remains unresolved

If an agent exceeds the target timebox, it must stop and report:

- what was verified
- what remains unverified
- whether the remaining uncertainty is a blocker or caveat

### Cancel / no-op UI-state invariant

For cancel, Escape, close, dismiss, revert, defer-without-save, or other no-op behavior, tests must verify both:

1. Data invariant: the abandoned value/action is not persisted and does not create a decision, export, audit, approval, or raw-data side effect unless explicitly expected.
2. Feedback invariant: the UI does not show `Saved`, `Saving...`, success, completed, validation-cleared, or any other confirmation/status message that implies the canceled action succeeded.

For review-screen/autosave work, also verify stale async state cannot show success after a no-op because of blur handlers, debounced autosave, in-flight request resolution, modal close, or Escape-induced focus changes.

A cancel/no-op regression test is incomplete if it checks only persistence and not misleading visible feedback. Normal save behavior should remain positively tested: a real save may show success and must persist when expected.

### Five-run E2E gate

If any Playwright/browser E2E file is created or materially changed, the affected E2E file must run five consecutive times before the work can be reported ready for review or ready for commit.

A material E2E change includes:

- adding a new E2E test
- changing browser interactions
- changing assertions
- changing setup or fixtures used by browser tests
- changing waits, selectors, navigation, or timing behavior
- changing export, approval, modal, validation, review-screen, or workflow browser tests

The command must run the full affected E2E file. Do not use a `::test_name` selector for the five-run gate unless the human explicitly authorizes isolated-test evidence for the current task.



### Five-run E2E evidence format

When full-file five-run evidence is required, summary language such as `5/5 passed`, `five consecutive passes`, or `100% reliability` is not sufficient. The report must distinguish full-file runs from selected-test runs.

Required evidence fields:

- Full affected E2E file required? yes/no
- Affected E2E file:
- Exact command:
- Did the command include `::test_name`? yes/no
- Did the entire affected E2E file run? yes/no
- Run 1 result:
- Run 2 result:
- Run 3 result:
- Run 4 result:
- Run 5 result:
- Valid full-file five-run evidence? yes/no

If the command includes `::test_name`, the evidence is targeted-test evidence, not full-file evidence, unless the human explicitly authorized isolated-test evidence for the current task.

When full-file five-run evidence is required but only selected tests ran five times, the report must say:

```text
Full-file five-run evidence present? no
Targeted five-run only? yes
Ready for review/commit/push? no
Blocking issue: full affected E2E file five-run is missing
```

A task may not be reported ready for review, ready for commit, or ready to push when full-file five-run evidence is required but the canonical evidence fields do not prove that the entire affected E2E file ran five consecutive times.

### Raw-data and review-screen invariants

For review-screen, inline-editing, autosave, validation, approval, and export work, enforce this invariant:

**No visible field-level Error may coexist with Review Status = No issues.**

Also verify:

- Issues column updates when row validation changes
- Approval warnings include rows with unresolved issues, follow-up, or defer decisions as required
- Failed autosave values are not exported
- Successful autosave values become effective reviewed values
- RawImportRow.raw_csv_data remains unchanged
- ReviewDecision / audit behavior remains append-only
- Existing Needs follow-up Notes-required behavior still works
- Existing Defer behavior still works
- Existing Inspect modal behavior still works

### Product UX Gatekeeper reporting

Before any review handoff, the Orchestrator must report:

- ambiguity present? yes/no
- gatekeeper invoked? yes/no
- if not invoked, reason
- human product decision needed? yes/no

If product/UX ambiguity is present, the Orchestrator must route to the Product UX Gatekeeper before treating the task as decision-complete.

## Householder workflow source of truth

For this project, the repo-local Claude workflow files are the source of truth:

```text
.claude/agents/implementer.md
.claude/agents/reviewer.md
.claude/agents/orchestrator.md
.claude/agents/product-ux-gatekeeper.md
.claude/skills/householder-debug/SKILL.md
```

Global files under `~/.claude/agents/` may exist as optional mirrors, but Householder tasks should follow the repo-local workflow files.

Do not modify Claude workflow files during product work unless the human explicitly requests a Claude workflow configuration task.

## Required process

Use the Implementer and Reviewer agents for this task.

1. First, ask the Implementer agent to handle the bug or requested change.
2. The Implementer must reproduce the issue before editing code.
3. The Implementer must add or update tests before or alongside the fix.
4. The Implementer must make the smallest safe change.
5. The Implementer must run targeted tests and report exact results.
6. Then ask the Reviewer agent to review the Implementer's report, git diff, and test evidence.
7. The Reviewer must remain read-only and must not edit files.
8. If the Reviewer returns `Request changes` or `Reject`, send only the specific review findings back to the Implementer.
9. Run at most two implementer/reviewer loops unless the human explicitly approves more.
10. Stop and summarize when the Reviewer returns `Accept` or `Accept with minor follow-up`.

## Mandatory review completion

For implementation tasks, **Ready for review** is not a terminal state.

After the Implementer finishes, the Orchestrator must collect independent evidence and invoke the Reviewer before the task can be considered complete, ready for commit, or ready for commit prep.

Do not summarize an implementation task as complete unless the Reviewer returns `Accept` or `Accept with minor follow-up`.

If Reviewer was not invoked, the final report must say:

```text
Reviewer verdict: NOT RUN — BLOCKING
Ready for commit? no
Ready for commit prep? no
```

The Implementer may report “Ready for reviewer,” but only the Reviewer verdict can make the change ready for commit prep.

## No intermediate handoff stopping rule

When a task is being run through the Orchestrator, intermediate handoff states are not terminal.

The Orchestrator must not respond to the human with only:

- `ready for reviewer`
- `ready for Reviewer sign-off`
- `awaiting Reviewer`
- `pending Reviewer response`
- `ready for Breaker`
- `awaiting Breaker`
- `pending Breaker response`

If the task requires Reviewer or Breaker review, the Orchestrator must invoke the required agent before responding to the human, unless one of the explicit stop exceptions below applies.

After a Reviewer returns `Request changes`:

1. The Orchestrator may send only the specific Reviewer finding back to the Implementer.
2. After the Implementer fixes the issue, the Orchestrator must collect updated evidence.
3. The Orchestrator must return the result to the Reviewer for a final verdict.
4. The Orchestrator must not stop at `ready for Reviewer sign-off`.
5. The Orchestrator must not ask the human to manually request Reviewer unless a human decision is actually required.

If Breaker is required for the task, the Orchestrator must invoke Breaker after Reviewer `Accept` unless Breaker was explicitly waived by the human.

The Orchestrator may report an intermediate handoff state only when:

- the task was explicitly Implementer-only,
- a required agent is unavailable,
- a required verification step is blocked,
- a human product/UX decision is required,
- the two-loop limit has been reached,
- the human explicitly asked to stop before review,
- or the human explicitly asked for status only.

## Happy-path auto-commit policy

Happy-path auto-commit is opt-in per task.

The workflow may automatically commit after Reviewer Accept only when the human explicitly includes:

```
Happy-path auto-commit: enabled
```

Without that phrase, stop after Reviewer Accept and report ready for commit prep.

Happy-path auto-commit never includes push unless the human explicitly includes:

```
Happy-path auto-push: enabled
```

Do not use happy-path auto-commit for:

* schema/migration changes,
* product/UX ambiguous changes,
* changes with any failing required test,
* changes involving secrets/credentials,
* changes involving unexpected files,
* changes where Reviewer did not return Accept or Accept with minor follow-up,
* changes where the human asked for assessment only, review only, commit prep only, or push only.

## Final report format

At the end, report:

* **Original issue/request** — what was the problem or requested change
* **Implementer summary** — what the Implementer did
* **Reviewer verdict** — Accept / Accept with minor follow-up / Request changes / Reject / NOT RUN — BLOCKING
* **Files changed** — list of modified/created files
* **Tests added or updated** — which tests changed
* **Exact test commands run** — the pytest commands executed
* **Exact test results** — stdout/stderr from tests
* **E2E file materially changed?** — yes/no
* **Five-run E2E required?** — yes/no
* **Five-run E2E completed?** — yes/no/not required, with exact full-file command and Run 1 through Run 5 results when required
* **Unresolved risks** — any gaps or concerns
* **Ready for commit?** — yes/no with justification; yes only after Reviewer returns Accept or Accept with minor follow-up
