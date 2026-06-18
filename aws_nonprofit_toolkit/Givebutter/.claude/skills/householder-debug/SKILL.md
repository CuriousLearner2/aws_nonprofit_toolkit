---

name: householder-debug
description: Orchestrates a disciplined Householder / DonorTrust bug-fix loop using the implementer and reviewer agents.
allowed-tools: Read, Grep, Glob, Bash, Task
---

# Householder Debug Skill

Use this skill for Householder / DonorTrust bug fixes, review-screen issues, autosave issues, validation issues, approval/export issues, and small scoped implementation changes.

## Agent preflight

Before starting any implementation or review work, verify that the required custom agents are available.

Required agents:

* `implementer`
* `reviewer`

Use the agent names exactly as defined in the `name:` field of their `.claude/agents/*.md` frontmatter.

Expected agent files:

* `.claude/agents/implementer.md`
* `.claude/agents/reviewer.md`

Expected frontmatter:

```yaml
name: implementer
```

```yaml
name: reviewer
```

Required subagent invocations:

* Use `subagent_type: "implementer"` for implementation work.
* Use `subagent_type: "reviewer"` for review work.

Do not use `general-purpose` as a fallback for either role.

If either required custom agent is unavailable:

1. Stop immediately.
2. Do not start coding.
3. Do not use `general-purpose`.
4. Report which agent is missing or unavailable.
5. Check whether the corresponding agent file exists.
6. Check whether the frontmatter contains the correct `name:` value.
7. If the files were created or edited after this Claude Code session started, tell the human to restart Claude Code so the custom agents are loaded.

Only proceed when both custom agents are available.

## Required process

Use the custom Implementer and Reviewer agents for this task.

1. First, invoke the Implementer agent using `subagent_type: "implementer"` to handle the bug or requested change.
2. The Implementer must reproduce the issue before editing code.
3. The Implementer must add or update tests before or alongside the fix.
4. The Implementer must make the smallest safe change.
5. The Implementer must run targeted tests and report exact results.
6. Then invoke the Reviewer agent using `subagent_type: "reviewer"` to review the Implementer's report, git diff, and test evidence.
7. The Reviewer must remain read-only and must not edit files.
8. If the Reviewer returns `Request changes` or `Reject`, send only the specific review findings back to the Implementer.
9. Run at most two implementer/reviewer loops unless the human explicitly approves more.
10. Stop and summarize when the Reviewer returns `Accept` or `Accept with minor follow-up`.

## Role boundaries

The Implementer agent may edit files.

The Reviewer agent must be read-only.

The Reviewer may inspect:

* `git diff --stat`
* `git diff`
* `git status --short`
* relevant source files
* relevant test files
* targeted pytest results
* full test-suite results, when available

The Reviewer must not:

* edit files
* reformat files
* reset files
* stage files
* commit files
* alter migrations
* modify the working tree

If the Reviewer needs a change, it must return a review finding for the Implementer to address.

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

## Source-control safety

Before editing, the Implementer should inspect the working tree.

If there is branch confusion, untracked-file risk, migration-chain risk, or unexpected dirty working tree risk:

1. Stop.
2. Report the risk.
3. Do not proceed until the human approves the next step.

Do not commit unless the human explicitly asks for a commit.

## Review-screen / autosave invariant

For review-screen, inline-editing, autosave, validation, approval, and export work, enforce this invariant:

**No visible field-level Error may coexist with Review Status = No issues.**

Also verify:

* Issues column updates when row validation changes.
* Review Status updates when row validation changes.
* Approval warnings include rows with unresolved issues, follow-up, or defer decisions as required.
* Failed autosave values are not exported.
* Successful autosave values become effective reviewed values.
* RawImportRow.raw_csv_data remains unchanged.
* ReviewDecision / audit behavior remains append-only.
* Existing Needs follow-up Notes-required behavior still works.
* Existing Defer behavior still works.
* Existing Inspect modal behavior still works.
* Human reviewer disposition does not incorrectly hide current blocking system errors.
* System-derived statuses remain display-only unless explicitly reset by system recalculation.
* Reviewer dispositions remain reviewer metadata and do not mutate raw data.

## Browser test requirements

For review-screen, autosave, validation, approval, export, modal, or inline-editing work, browser tests must verify both visible state and control preservation.

A browser test is not sufficient if it only checks that the right text, badge, color, or message appears.

Browser tests must also verify that required controls remain usable after UI state changes.

For any affected row or workflow, verify as applicable:

* Required control still exists.
* Required control is visible.
* Required control is enabled.
* Expected options/actions remain available.
* Interaction still works after UI state changes.
* Event listeners still work after autosave success or error.
* The control is not replaced by a static badge, span, or text-only element unless that is explicitly intended.

Examples:

* If Review Status changes to `Blocking`, the Review Status dropdown/select must still exist and remain usable.
* If Issues update after autosave, the Inspect button must still exist and remain usable.
* If a modal opens, its required fields and buttons must remain focusable and actionable.
* If a row is re-rendered, expected row actions must still be present.

Regression rule:

Do not update a table cell or row with destructive `innerHTML` replacement if that cell or row contains interactive controls, unless the full control is intentionally re-rendered with all expected options, event handlers, data attributes, and accessibility behavior restored.

Browser tests should fail if a visual update accidentally destroys an interactive control.

## Interactive control requirements

No visible enabled control may be nonfunctional.

If a button, dropdown, link, form control, or action appears enabled, browser tests must verify that it actually works.

For any visible enabled control, verify as applicable:

* The control exists.
* The control is visible.
* The control is enabled.
* The control has a defined action or handler.
* The control produces the expected state change, navigation, modal, submission, or validation result.
* The control does not silently do nothing.
* The control does not fail only in the browser while backend tests pass.

If a control is not implemented yet, it must not appear as an enabled working control. Instead, choose one of:

* hide it,
* disable it,
* label it clearly as unavailable,
* or implement it fully with tests.

Examples:

* If `Next Pair` and `Previous Pair` buttons are visible and enabled, they must navigate between duplicate pairs.
* If navigation is not implemented, those buttons must be disabled, hidden, or clearly marked unavailable.
* If `Approve with Overrides` is visible and enabled, it must complete the approval-with-overrides workflow or show a clear error.
* If `Record Decision` is visible and enabled, it must persist the reviewer decision or show a clear validation error.

Reviewer rule:

The Reviewer must reject changes that leave visible enabled controls with no working behavior, unless the control is explicitly disabled or clearly marked as unavailable.

## Product UX decision authority

Claude must not independently decide product UX when multiple reasonable workflows exist.

If a UX behavior is ambiguous, Claude must stop and ask the human before implementing.

Examples of ambiguous UX decisions:

* Whether Duplicates should use forced decision-queue progression or free Previous/Next browsing.
* Whether `Skip for now` is distinct from `Defer`.
* Whether unresolved duplicates block export or only warn.
* Whether approval with overrides should be allowed for a given issue type.
* Whether a visible control should be removed, disabled, labeled unavailable, or fully implemented.
* Whether notes are required, optional, or conditionally required.
* Whether status should reflect system state, human disposition, or both.

Claude may present options with tradeoffs, but must not choose the product behavior unless the human has already specified it.

Required pattern:

1. Identify the product ambiguity.
2. Present the smallest reasonable options.
3. Recommend one option if useful.
4. Stop and ask for the human's decision.
5. Only implement after the human chooses.

Do not convert a product question into an engineering assumption.

For visible controls:

* If a control appears enabled, it must work.
* If a control is not implemented, Claude must ask whether to hide it, disable it, label it unavailable, or implement it.
* Claude must not remove or replace a visible workflow control if that changes the intended reviewer workflow without human approval.

Reviewer rule:

The Reviewer must reject changes where Claude made an unapproved UX/product decision, even if tests pass.

## Implementation discipline

The Implementer must not start by editing code.

The Implementer must first report:

1. Expected behavior.
2. Smallest relevant code area.
3. Reproduction method.
4. Exact current failure.
5. Likely root cause.

Then the Implementer may make the smallest safe change.

The Implementer should prefer test-first changes. If the bug cannot be reproduced in a test, the Implementer must explain why and provide precise manual reproduction evidence before editing implementation code.

## Review discipline

The Reviewer must evaluate whether the change is correct, safe, and adequately tested.

The Reviewer must explicitly check:

* Does the fix address the original issue?
* Did the Implementer reproduce the bug before editing?
* Do tests prove behavior rather than implementation details?
* Is the diff minimal and scoped?
* Are raw source rows still immutable?
* Are failed autosave values prevented from leaking into export?
* Can approval still treat visibly invalid rows as clean?
* Are Issues and Review Status synchronized?
* Is audit history preserved?
* Were unrelated files changed?
* Were migrations changed unnecessarily?

* Do browser tests verify both visible state and control preservation?
* Do required controls remain present, visible, enabled, and usable after UI state changes?
* Do browser tests avoid accepting text-only/static replacements when the workflow requires continued interaction?
* Is every visible enabled control functional, or explicitly disabled/hidden/marked unavailable if not implemented?
* Did Claude avoid making unapproved UX/product decisions when multiple reasonable workflows existed?
Reviewer verdict must be one of:

* `Accept`
* `Accept with minor follow-up`
* `Request changes`
* `Reject`

Do not mark the task complete unless the Reviewer returns `Accept` or `Accept with minor follow-up`.

## Final report format

At the end, report:

* **Original issue/request** — what was the problem or requested change
* **Agent preflight** — confirm `implementer` and `reviewer` were available and used
* **Implementer summary** — what the Implementer did
* **Reviewer verdict** — Accept / Accept with minor follow-up / Request changes / Reject
* **Files changed** — list of modified/created files
* **Tests added or updated** — which tests changed
* **Exact test commands run** — the pytest commands executed
* **Exact test results** — stdout/stderr from tests
* **Unresolved risks** — any gaps or concerns
* **Ready for commit?** — yes/no with justification
