---

name: householder-debug
description: Orchestrates a disciplined Householder / DonorTrust bug-fix loop using the implementer and reviewer agents.
allowed-tools: Read, Grep, Glob, Bash, Task
-------------------------------------------

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
