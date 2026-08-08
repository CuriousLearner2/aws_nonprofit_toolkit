---
name: householder-debug
description: Orchestrates a disciplined Householder / DonorTrust bug-fix loop using the implementer and reviewer agents.
allowed-tools: Read, Grep, Glob, Bash, Task
---

# Householder Debug Skill

Use this skill for Householder / DonorTrust bug fixes, review-screen issues, autosave issues, validation issues, approval/export issues, and small scoped implementation changes.

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

For ordinary scoped implementation work:

1. Implementer reproduces the issue and identifies the smallest relevant code area.
2. Implementer adds or updates focused tests and makes the smallest safe change.
3. Run focused/relevant tests first.
4. Freeze the exact staged diff before review.
5. Invoke Reviewer once against that fingerprint.
6. If Reviewer returns `VERDICT=REQUEST_CHANGES` or `VERDICT=REJECT`, stop unless the human authorizes one focused repair/re-review.
7. Invoke Breaker only for concrete P0/P1 invariant or process-integrity risk.
8. Invoke QA/runtime acceptance only when the task contract explicitly requires it.
9. Readiness verifies the exact reviewed diff and already-collected evidence.
10. Create the local commit, then prepare the trusted host SSH publisher handoff.

Do not add role invocations, full-suite reruns, ledger transitions, or review cycles that do not change the safety decision.

If a canonical broad suite is already red on the untouched baseline, compare baseline and current with the same command/environment. If current introduces no new failing identities, record `BASELINE_DEBT_VERIFIED` and do not block solely on pre-existing failures.

## Current reviewer-disposition product rules

These rules supersede stale disposition expectations in older tests, fixtures, or workflow text:

- `Defer` is removed from the user-facing reviewer-disposition model.
- A clean row (`Validation status = No issues`) shows system `Accept as-is` without creating a `ReviewDecision` or human audit record.
- An issue-bearing row starts at `No disposition` unless a saved human disposition exists.
- Human `Accept as-is` on an issue-bearing row requires reviewer name plus non-empty `Reason / notes`; the underlying warning/error remains visible and preserved.
- `Needs follow-up` excludes the row from the current export but leaves it in the import batch for later work.
- `Reject row` excludes the row from the current export.
- Only an issue-bearing row still at `No disposition` blocks finalization.
- Clearing a saved human disposition restores system `Accept as-is` for a clean row and `No disposition` for an issue-bearing row.
- Review history is append-only.
- Raw source data remains unchanged.

## Execution Budget / Drift Control

For hardening tasks, avoid open-ended exploration.

Classify the work before proceeding:

* **Assessment only** — no edits, no commits, no pushes. Identify evidence, gaps, and the single recommended next task.
* **Implementation only** — one confirmed gap only; targeted tests first; no commits or pushes.
* **Commit preparation** — no re-investigation, no product reassessment, no five-run reruns unless explicitly requested or no prior evidence exists.
* **Push only** — no edits and no new commits.

Default drift-control rules:

* If more than 8 shell commands are needed before the first meaningful result, stop and report why.
* If a task starts to require broad rediscovery, product reassessment, schema changes, migration changes, or unrelated cleanup, stop and ask the human.
* If any required verification step cannot be completed, do not summarize the task as complete. Report the missing step as **BLOCKING**.
* Do not continue silently when the task scope expands.
* Prefer targeted tests first. Run full unit/integration only after targeted tests pass and the change appears correct.
* Keep reports terse: files changed, commands run, exact results, blockers, Reviewer verdict, ready/not ready.
* Do not use passing tests to justify unapproved product behavior.
* Do not rerun expensive tests in commit-prep if prior exact passing evidence exists and the human requested a fast commit-prep pass.

## Mandatory E2E five-run gate

If any Playwright/browser E2E file is created or materially changed, the affected E2E file must run five consecutive times before the work can be reported ready for review or ready for commit.

A material E2E change includes:

* Adding a new E2E test.
* Changing browser interactions.
* Changing assertions.
* Changing setup or fixtures used by browser tests.
* Changing waits, selectors, navigation, or timing behavior.
* Changing export, approval, modal, validation, review-screen, or workflow browser tests.

This applies even if product code was not changed.

Required command pattern:

```bash
for i in 1 2 3 4 5; do
  echo "E2E RUN $i"
  pytest <affected_e2e_file> -v || exit 1
done
```

If five-run E2E is required but missing, the missing verification is **BLOCKING**.

## Failed first-fix stop policy

If the first attempted fix fails, do not continue silently.

Stop after the first failed targeted verification unless the human explicitly authorizes another implementation attempt.

A failed first fix is not a reason to broaden scope. It is a reason to report:

- failed test or command
- exact failure
- changed files
- whether the failure is the same or different
- whether partial edits remain
- recommended cleanup or next narrow diagnostic task

Do not continue into a second root-cause theory, selector redesign, fixture redesign, product behavior changes, broad test repair, or unrelated cleanup in the same task unless the human explicitly authorizes it.

If the human instructed that failed edits should be reverted, revert only those edits and report the clean state.

If failed edits remain, final status must be:

```text
Ready for commit? no
Ready for commit prep? no
```

and the failed verification must be marked **BLOCKING**.

## Project guardrails

* Do not commit directly to main.
* Do not mutate raw source data.
* Do not add Givebutter/CRM writeback.
* Do not add credentials.
* Do not add auth/RBAC changes.
* Do not add background jobs.
* Do not add bulk actions.
* Do not add new export formats.
* Do not perform broad refactors.
* Do not change Alembic migrations unless explicitly necessary and called out.
* Preserve append-only audit history.
* Preserve the principle: The system suggests. The reviewer decides. Raw data stays unchanged.

## Review-screen / autosave invariant

For review-screen, inline-editing, autosave, validation, approval, and export work, enforce these invariants:

**No visible field-level Error may coexist with Validation status = No issues.**

Also verify:

* Issues column updates when row validation changes.
* System validation status and human Reviewer disposition remain distinct.
* Issue-bearing `No disposition` blocks finalization.
* `Needs follow-up` and `Reject row` are excluded from the current export without blocking other resolved rows.
* Human `Accept as-is` preserves the underlying issue and requires reviewer name plus non-empty Reason / notes.
* `Defer` is absent from the user-facing disposition model.
* Failed autosave values are not exported.
* Successful autosave values become effective reviewed values.
* `RawImportRow.raw_csv_data` remains unchanged.
* `ReviewDecision` / audit behavior remains append-only.
* Existing Needs follow-up Notes-required behavior still works.
* Existing Record Details / review-history behavior still works.

## Mandatory review completion

For implementation tasks, **Ready for review** is not a terminal state.

After the Implementer finishes, the Orchestrator must collect independent evidence and invoke the Reviewer before the task can be considered complete, ready for commit, or ready for commit prep.

Do not summarize an implementation task as complete unless the Reviewer returns `VERDICT=ACCEPT`.

If Reviewer was not invoked, the final report must say:

```text
Reviewer verdict: NOT RUN — BLOCKING
Ready for commit? no
Ready for commit prep? no
```

The Implementer may report “Ready for reviewer,” but only the Reviewer verdict can make the change ready for commit prep.

## Final report format

At the end, report:

* **Original issue/request** — what was the problem or requested change
* **Implementer summary** — what the Implementer did
* **Reviewer verdict** — VERDICT=ACCEPT / VERDICT=REQUEST_CHANGES / VERDICT=REJECT / NOT RUN — BLOCKING
* **Files changed** — list of modified/created files
* **Tests added or updated** — which tests changed
* **Exact test commands run** — the pytest commands executed
* **Exact test results** — stdout/stderr from tests
* **E2E file materially changed?** — yes/no
* **Five-run E2E required?** — yes/no
* **Five-run E2E completed?** — yes/no/not required, with Run 1 through Run 5 results when required
* **Unresolved risks** — any gaps or concerns
* **Ready for commit?** — yes/no with justification; yes only after Reviewer returns `VERDICT=ACCEPT`

