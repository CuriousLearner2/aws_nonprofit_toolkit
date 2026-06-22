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

Rules:

- Use anchored review.
- Inspect changed product code and directly affected tests.
- Inspect adjacent code only when needed.
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

Rules:

- Use staged escalation.
- Stage 1: 3-4 minute risk triage.
- Stage 2: focused deep review of only the risk paths identified in Stage 1.
- Do not perform unbounded repo archaeology.
- Escalate beyond 12 minutes only with a specific blocker, suspected bug, or missing evidence.

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
