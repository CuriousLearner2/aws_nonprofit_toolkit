---
name: householder-debug
description: Orchestrates a disciplined Householder / DonorTrust bug-fix loop using the implementer and reviewer agents.
allowed-tools: Read, Grep, Glob, Bash, Task
---

# Householder Debug Skill

This is the canonical workflow policy for the Householder / DonorTrust project. Agent files are role-specific summaries and must not override this file.

## Start Here / Priority Order

Apply rules in this order:

1. **Task contract first.** Classify task, lane, allowed files/actions, required agents, gates, and terminal state before meaningful work. Assessment-only classification creates an implementation firewall: proving root cause does not authorize edits.
2. **Project invariants always win.** The system suggests. The reviewer decides. Raw data stays unchanged.
3. **Failed gates stop immediately unless an explicit Failed-First Repair Lane is enabled.** Without that opt-in, no diagnosis, retry, split, second fix, Reviewer, Breaker, commit, or push without new human authorization. With the lane enabled, exactly one narrow repair may occur only under the rules below.
4. **Required handoffs are actions.** Passing gates means invoke required Reviewer/Breaker; `Ready for Reviewer` is not terminal.
5. **Non-accept verdicts are terminal.** Reviewer `Request changes` / `Reject` and Breaker `P1/P0/FAIL` require a new human-authorized remediation task.
6. **Review capability first for implementation.** If Reviewer/Breaker are required, the session must be able to invoke them before implementation or auto-commit-capable work begins.
7. **Commit and push remain separate.** Auto-commit requires the exact phrase `Happy-path auto-commit: enabled`; push requires separate explicit authorization. Do not re-ask for permission to perform an action already authorized by the task contract.

During named Manual UAT / RC phases, use the QA / UAT Agent before implementation to triage findings and propose batches. The QA / UAT Agent is advisory only and does not replace Reviewer or Breaker.

## RED RULES — ALWAYS OBEY

1. **Assessment-only:** Orchestrator performs it directly. No child agents, no edits, and stop at the assessment report.
2. **Any failed, hung, timed-out, interrupted, unusable/truncated, or exit-143 gate:** stop immediately unless the task contract explicitly says `Failed-First Repair Lane: enabled` and the failure qualifies under that lane. Without that exact opt-in, no diagnosis, retry, split, second fix, Reviewer, Breaker, commit, or push without human authorization.
3. **E2E gates require explicit wall-clock timeouts:** 90s single test, 180s full file, 90s per reliability iteration unless a stricter task-specific gate is declared. Multi-test pytest gates must use `-x` or `--maxfail=1`.
4. **Project commands run from the Givebutter project directory using `./.venv/bin/python`.** Do not use bare `python` for project gates/guards unless the task contract or local workflow explicitly proves a different interpreter is required.
5. **Timeout equals failed gate.** Treat it exactly like a test failure and deliver a failed-gate stop report.
6. **Rewritten E2E tests require hard assertions.** No soft guards, no `if element: assert ...`, no print/networkidle-only success, no zombie tests, and no page-load-only replacement coverage.
7. **Reviewer handoff:** For implementation flows requiring review, Implementer stops at ready-for-review and Orchestrator invokes Reviewer after passing gates. Do not invoke Reviewer for assessment-only, push-only, or status-only tasks unless explicitly required.
8. **Terminal states stop:** assessment report, failed-gate report, cleanup completed, Reviewer `VERDICT=REQUEST_CHANGES` / `VERDICT=REJECT`, Breaker failure, commit, and push. A commit is non-terminal only under the explicit Autonomous Multi-Item P1 Campaign Exception below; otherwise do not auto-start the next task.
9. **Breaker is concrete-risk-based, not routine.** Invoke only for concrete P0/P1 invariant or process-integrity risk, when Lane D/product risk requires it, or when the human asks.

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
- Canonical acceptance gate(s):
- Diagnostic command(s), if any:
- Test-Harness Stabilization enabled? yes/no
- Test-harness stabilization files and maximum iterations:
- Gate command(s):
- Failed-First Repair Lane enabled? yes/no
- Failed-first repair budget: none / one per failed gate / max N across batch
- Stop condition:
- Terminal state:
```

Rules:
- Do not proceed until the contract is written.
- If any field is uncertain, stop and ask or classify as assessment-only.
- If the task is assessment-only, push-only, or status-only, Reviewer must be `no` unless explicitly required by the human.
- If the task is an implementation flow requiring review, Reviewer must be `yes`, and Orchestrator must invoke Reviewer after passing gates.
- Lane classification must match an exact lane trigger phrase; do not infer a lane.



## Session Review-Capability Preflight

Before any implementation, commit-capable, or Orchestrator-led review flow begins, Orchestrator must verify whether the current session can actually invoke the required review agents.

This is a tooling readiness check, not a product decision.

Required preflight for implementation and auto-commit-capable tasks:

```text
Reviewer invocation available? yes/no/unknown
Breaker invocation available? yes/no/unknown
Task/subagent mechanism available? yes/no/unknown
If unavailable, exact limitation:
```

Rules:
- The presence of `.claude/agents/reviewer.md` or `.claude/agents/breaker.md` on disk proves the policy files exist; it does **not** prove the current session can invoke those agents.
- If Reviewer is required but not callable in the current session, stop before implementation or commit-capable work and report the environment limitation.
- If Breaker is required or likely required for P0/P1/product-invariant risk but not callable, stop before implementation unless the task can safely proceed only through assessment or Reviewer and then stop before Breaker.
- Do not silently downgrade to self-review, Reviewer-style review, or Breaker-style review.
- Do not auto-commit when required Reviewer/Breaker invocation is unavailable.
- Reviewer or Breaker may be waived only by explicit human authorization for that specific task, after the unavailability is reported.
- Assessment-only tasks may proceed without Reviewer/Breaker invocation capability, because Reviewer and Breaker are not invoked unless explicitly required.

If the required review capability is unavailable, the correct terminal report is:

```text
Session review capability blocker.
Reviewer invocation available? no/unknown
Breaker invocation available? no/unknown
Required by task? yes/no
Implementation/commit allowed? no
Next human choices:
1. Restart/open a session with Reviewer/Breaker capability
2. Convert to assessment-only
3. Explicitly waive Reviewer/Breaker for this specific task
```

## Reasoning Escalation Policy

Use the standard efficient reasoning setting for routine work such as command execution, test runs, evidence ledgers, fixture classification, bounded test-only changes, scope audits, and ordinary handoffs.

Do not repeatedly guess under an insufficient reasoning setting. Escalation is required when any of these concrete triggers appears:

- evidence is contradictory, incomplete, or materially ambiguous;
- a test produces evidence of a likely production defect, contradictory product behavior, or a failure whose root cause cannot be confidently classified within the authorized test-only scope;
- root cause spans multiple production layers;
- current behavior differs unexpectedly from a clean baseline;
- the same gate fails twice with different plausible causes;
- concurrency, stale state, browser-event behavior, fallback behavior, or mode-specific behavior remains unresolved after one focused attempt;
- Reviewer and Breaker disagree on a material issue;
- a production-code repair is being designed for a non-trivial defect;
- raw-data integrity, append-only audit, approval correctness, export correctness, persistence, or security may be affected;
- a failure cannot be confidently classified.

### Escalation Procedure

1. Preserve the current worktree and all relevant evidence.
2. Do not weaken, skip, xfail, delete, or rewrite a valid failing test to avoid escalation.
3. Do not edit production code while the escalation is unresolved.
4. First delegate the narrow difficult question to a stronger or unpinned subagent when the session supports that.
5. If the stronger subagent resolves the issue confidently, record its evidence and continue under the existing task contract.
6. If stronger main-task reasoning is still required, stop with this exact report:

```text
REASONING ESCALATION REQUIRED

- Current phase:
- Unresolved question:
- Evidence collected:
- Competing explanations:
- Why the current reasoning setting is insufficient:
- Recommended stronger capability or setting:
- Exact next action after escalation:
- Production files currently modified? yes/no
- Current git status:
```

7. Do not continue implementation until the escalation is resolved or the human explicitly authorizes a different path.

### De-escalation Procedure

After the difficult question is resolved and the remaining work is mechanical, explicitly report:

```text
MEDIUM/EFFICIENT REASONING IS SUFFICIENT AGAIN

- Resolved question:
- Evidence supporting resolution:
- Remaining mechanical steps:
```

Then return to the standard efficient reasoning setting when the interface permits. Do not remain unnecessarily escalated for routine test execution, ledger maintenance, or already-understood implementation.

### Role Ownership

- **Orchestrator:** identifies escalation triggers, chooses stronger-subagent-first, stops for main-task escalation when needed, and records de-escalation.
- **Implementer:** must stop rather than guess when the authorized change depends on unresolved ambiguous evidence.
- **Reviewer:** may block acceptance when the reasoning level was insufficient to support the evidence or root-cause claim.
- **Breaker:** may flag P0/P1 risk when unresolved ambiguity, shallow analysis, or contradictory evidence could mislead the reviewer.
- **Product UX Gatekeeper:** handles product ambiguity only; it does not substitute for technical reasoning escalation.
- **QA / UAT:** may recommend escalation when a manual finding cannot be tied to the exact runtime path.

This policy is capability-based. Do not hardcode a specific model name or assume the main task can change its own setting automatically.

## Assessment-to-Implementation Firewall

Assessment-only tasks are terminal at the assessment report. Proving root cause, identifying an obvious fix, finding a low-risk patch, or knowing the exact tests to add does **not** authorize implementation.

In any task classified as `Assessment only`:

- do not edit files,
- do not write or update tests,
- do not stage, commit, amend, or push,
- do not invoke Implementer, Reviewer, or Breaker,
- do not run implementation gates for a proposed fix,
- do not continue from `root cause proven` into `fix applied`, even if the fix is small, obvious, and likely correct.

The correct terminal report is:

```text
Assessment complete.
Root cause proven? yes/no
Smallest recommended implementation task:
Expected files:
Suggested gates:
Human authorization required before any edit.
```

Forbidden assessment-only transitions:

```text
root cause proven → edit files
root cause proven → add tests
root cause proven → run fix gates
root cause proven → commit
```

If the human wants the fix, they must authorize a new implementation task or provide a current task contract that permits implementation. A technically correct unauthorized fix is still a workflow violation and must be treated as post-hoc review, not clean happy path.

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


## Project Command Location, Bootstrap, and Environment-Only Recovery

Unless a task contract or repo-local workflow file explicitly states otherwise, bootstrap the project command environment before gates, guards, pytest runs, or commits that invoke repository hooks:

```bash
GIVEBUTTER_DIR="/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter"
cd "$GIVEBUTTER_DIR"
export PATH="$GIVEBUTTER_DIR/.venv/bin:$PATH"
```

Use the project virtualenv interpreter:

```bash
./.venv/bin/python
```

Before commit-capable work, verify command resolution:

```bash
command -v python
command -v pytest
python -c "import sys; print(sys.executable)"
```

When the changed path imports `email_validator`, also verify:

```bash
python -c "import email_validator; print(email_validator.__version__)"
```

Both `python` and `pytest` must resolve inside `$GIVEBUTTER_DIR/.venv`.

Rules:
- Do not use bare `python` for project gates or guards.
- Do not construct the virtualenv path from `$PWD` until the working directory has been verified.
- Do not assume `./.venv/bin/python` exists from the Git repo root; first `cd` to the Givebutter project directory.
- Prefer the absolute Givebutter `.venv/bin` path for commit-hook bootstrap when the caller's working directory is uncertain.

### One-Time Environment-Only Recovery

A wrong-directory, wrong-`PATH`, wrong-interpreter, or wrong-`pytest` invocation may be corrected and retried once without new human authorization only when **all** of these conditions are proven:

1. The intended product/test gate did not begin meaningful test execution; failure occurred during command startup, import bootstrap, or pre-collection environment initialization.
2. Evidence identifies the wrong working directory, `python`, `pytest`, or `PATH` as the sole cause.
3. The required interpreter and dependency import succeed in the Givebutter `.venv`.
4. No repository file, hook, dependency, test, fixture, or product code is edited.
5. The only correction is `cd` to `$GIVEBUTTER_DIR` and/or prepending `$GIVEBUTTER_DIR/.venv/bin` to `PATH`.
6. The identical declared gate or commit command is retried.
7. No prior environment-only retry has been used for that gate or commit attempt.

Before retrying, record:

```text
Environment-only recovery:
- Original working directory:
- Original python:
- Original pytest:
- Proven environment cause:
- Givebutter venv verification:
- Files edited for recovery: none
- Retry count: 1 of 1
```

If the retry succeeds, continue under the original task contract and record the recovery in the final evidence. If it fails, the normal failed-gate rule applies immediately.

Environment-only recovery is **not allowed** for:

- assertion failures;
- collection/import failures under the verified Givebutter `.venv`;
- a dependency genuinely missing from the Givebutter `.venv`;
- a hook that hardcodes another interpreter or command;
- localhost/socket or sandbox restrictions;
- timeout, signal `-9`, exit `143`, interruption, hang, or uncertain process cleanup;
- schema, database, fixture, product, test, or workflow defects;
- any failure whose cause is ambiguous;
- any retry that would alter the command, files, dependencies, or hook.

This recovery rule distinguishes an intended gate failure from a case where the intended gate never ran in the declared project environment. It does not weaken the failed-gate terminal policy.

## Repository Automation Guardrails

Run guardrails in this order for implementation and commit-prep flows:

**A. Artifact Guard**
```bash
./.venv/bin/python scripts/ci/check_no_artifacts.py
```

**B. Lane Scope Guard**
```bash
./.venv/bin/python scripts/ci/check_lane_scope.py --lane <lane>
```
Lane mapping: `assessment`, `test-only`, `workflow-ci`, `product`, `push-only`. If it fails, stop and report; do not recategorize, clean up, or continue without human authorization.

**C. Scope Guard**
```bash
./.venv/bin/python scripts/ci/check_scope.py --allow <expected file> ...
```
Must list each expected changed file explicitly. Do not use broad patterns like `--allow tests/**`, `.claude/**`, or `**` unless explicitly authorized.

**D. Test Gate Wrapper**
```bash
./.venv/bin/python scripts/ci/test_gate.py --timeout N -- pytest <args>
```
Required for unit, integration, and targeted non-E2E pytest gates in implementation flows. Timeout exit code 124 is a failed gate.

**E. E2E Gate Wrapper**
```bash
./.venv/bin/python scripts/ci/e2e_gate.py --timeout N -- pytest <args>
```
Required for E2E gates. Multi-test E2E gates must use `-x` or `--maxfail=1`.

## GitHub Workflow Clean-Runner Policy

For changes under `.github/workflows/**`, the acceptance chain must prove a clean runner, not just a developer checkout:

- validate that the clean runner starts without an existing project `.venv`;
- create the Givebutter virtualenv at `$GITHUB_WORKSPACE/aws_nonprofit_toolkit/Givebutter/.venv`;
- use the exact Givebutter `.venv/bin/python` and `.venv/bin/pytest` paths for critical commands;
- append `$GIVEBUTTER_DIR/.venv/bin` to `$GITHUB_PATH` for later steps and verify command resolution explicitly before running the canonical gate;
- keep workflow-contract tests covering Python version, permissions, path resolution, and command-resolution assertions;
- treat a live GitHub Actions run for the final workflow commit as required evidence before production acceptance;
- when a new workflow commit is pushed, validate it with a new `workflow_dispatch` run from that commit rather than rerunning an older failed run.

## Interrupted Gate / Background Terminal Rule

If a gate is interrupted, times out, hangs, exits 143, or cannot be confirmed stopped/cleaned up, stop and report. Do not continue gates, invoke Reviewer, invoke Breaker, commit, or push in the same session unless the human explicitly authorizes a recovery task. Do not leave background terminals running after a gate. If process cleanup cannot be confirmed because the environment cannot enumerate processes, report that limitation and stop.

## Gate Rules

A declared gate is binary. It passes only when the declared command exits 0. If it exits nonzero, hangs, times out, exits 143, is interrupted, or produces unusable/truncated output, it failed unless the task was explicitly assessment-only or failures are proven pre-existing and unrelated with baseline evidence.

After a failed gate: stop command execution. If `Failed-First Repair Lane` is not explicitly enabled in the current task contract, do not inspect/grep/rerun/split/diagnose/repair/continue, do not invoke Reviewer/Breaker, and do not commit or push. If the lane is enabled, follow the bounded repair rules below exactly.

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


## Failed-First Repair Lane — Explicit Opt-In Only

Default rule: failed gates are terminal. This lane exists only when the current task contract contains the exact phrase:

```text
Failed-First Repair Lane: enabled
```

When enabled, Orchestrator/Implementer may perform one narrow failed-first repair attempt without new human authorization only if all of the following are true:

1. The failed assertion is local to the current authorized task or current batch item.
2. The likely repair is in files already authorized by the task contract.
3. The repair does not require backend behavior changes unless backend files were explicitly authorized.
4. The failure does not implicate schema, migrations, raw-data mutation, export semantics, audit semantics, review decision semantics, route logic, workflow state, or repository/service behavior.
5. The failure is classified before editing as exactly one low-risk category:
   - brittle test assertion,
   - wrong fixture expectation,
   - copy/case/punctuation mismatch,
   - missing stable test marker in an already-authorized template,
   - test expecting the wrong seeded value,
   - presentational template mismatch.
6. The agent can state the suspected cause and the single intended repair before editing.
7. The agent reruns only the failed focused gate after the repair.

Hard stop conditions. Stop immediately without repair when the failed gate suggests:

- backend route behavior changed unexpectedly,
- repository/service logic is implicated,
- schema/migration issue,
- raw-data mutation risk,
- export eligibility or file-content semantics changed,
- audit semantics changed,
- review/autosave/approval semantics changed,
- fixture/data shape mismatch requiring files not already authorized,
- more than one test file or page is unexpectedly affected,
- the repair would require a new product/UX decision,
- the first failed-first repair attempt already failed.

Repair limits:

- Maximum one failed-first repair attempt per failed gate unless the task contract sets a stricter lower budget.
- Maximum two failed-first repair attempts across any batched task unless the task contract sets a stricter lower budget.
- No broad diagnosis after failure; inspect only the assertion, the current diff, and the immediately relevant rendered/test context needed to classify the allowed repair.
- No additional files beyond the original authorized scope.
- No Reviewer/Breaker after a failed gate.
- No commit unless all originally required gates later pass and Reviewer returns exact `VERDICT=ACCEPT`.
- If the failed-first repair gate fails, stop immediately and report a Failed Gate Stop Report with `Failed-first-fix triggered? yes`.

For batched UX-only tasks:

- A failed gate may be repaired only within the currently failed batch item.
- Do not continue to the next batch gate until the failed item passes.
- Do not make new changes to later batch items while repairing the failed item.
- If Gate 2 fails, do not alter already-passing Task 1 files unless the failure directly proves Task 1 caused the problem and those files are still in scope.

A successful failed-first repair returns the workflow to the original declared gate sequence. It does not authorize extra tests, extra files, Reviewer bypass, commit bypass, or push.

## Deep Bug Analysis Rule

Use this rule for non-trivial bugs, cross-layer bugs, regressions, flakes, fallback/exception behavior, mode-specific behavior, or any defect that affects reviewer decisions, validation, normalization, approval, export, audit, raw/effective values, browser state, or workflow/process safety.

Do not jump from symptom → plausible cause → fix. First prove the causal chain:

```text
symptom → observed facts → competing hypotheses → discriminating evidence → proven failing layer → smallest fix
```

Before naming root cause or implementing a fix, answer:

1. What is the exact observed symptom?
2. What path, mode, and data shape produced it?
3. What are at least two plausible causes, unless the cause is already proven by direct evidence?
4. What evidence distinguishes those causes?
5. What exact files/functions/data prove the actual cause?
6. What layer owns the fix?
7. What is the smallest fix that addresses that layer?
8. What test proves the failing path, not merely a nearby rule?

### Cross-layer value and issue tracing

When a bug involves UI display, templates, row status, Issues text, validation, fixture mode, database mode, fallback paths, raw values, effective values, stale metadata, field/key mapping, approval/export readiness, or audit records, trace the exact value and issue object through every relevant layer.

Required trace questions:
- What exact value is stored?
- What exact value is rendered?
- Is the rendered value clipped/truncated, or is the stored value actually truncated?
- What exact value is passed into the validator/service?
- What exact key name is used at each layer?
- What key name does the receiving function expect?
- Is the issue freshly generated or stale persisted/fixture metadata?
- What exact issue object is produced, including field/source/severity/message?
- Why does the UI render the displayed field label/severity/message?
- Is the path database mode, fixture mode, fallback mode, or mixed?
- Does the same value behave differently across modes?

Required cautions:
- Do not infer root cause from UI symptom alone.
- Do not implement until the trace identifies the layer where value/status/issue changes.
- If trace evidence is unavailable, report `unknown` rather than guessing.
- `Looks clipped in UI` is not evidence of stored truncation.
- `Validator exists` is not evidence that the failing path invokes it.
- `Issue shown in UI` is not evidence that the issue was freshly generated.
- `E2E passed` is not evidence that the failing mode, fallback, data shape, or state transition was covered.

### Repo-specific grounding rule

Deep analysis must stay grounded in the actual repository.

- Do not invent file paths, class names, route names, frontend components, services, or test files.
- Ground likely files/functions with `Read`, `Grep`, or `Glob` before presenting them as repo-specific.
- If repo inspection is not allowed or the scenario is hypothetical, label file names as `conceptual/provisional` and provide the repo-discovery commands or patterns that would verify the real paths.
- Do not describe this Flask/Jinja app using generic React-style names such as `ExportPage`, `ValidationReview`, or `IssuesList` unless those exact symbols exist in the repo.
- Expected files for implementation must be based on inspected repo paths. If the failing layer is known only conceptually, the next task should be trace-first assessment, not implementation.
- Do not create new files merely because a conceptual name appeared in an assessment. First locate the existing architecture.


### Manually observed UI bug runtime verification rule

For manually observed browser/UI bugs, a plausible code or fixture defect is not enough. Agents must prove that the proposed fix targets the exact row, screen, mode, and runtime path that produced the observed symptom.

Before implementing or accepting a fix for a manually observed UI bug, answer:
- What exact displayed row/control/screen is being investigated, including transaction id/import id/record id when available?
- What exact runtime source produced it: fixture data, database row, saved decision, cached data, fallback path, or stale server/browser state?
- Is the current server/browser using the commit or file changes being assessed? If unknown, report `stale runtime unknown` rather than assuming.
- What exact issue/status/value object is delivered to the template or browser for that displayed row?
- Does the object contain the exact key that the template/JavaScript reads?
- Did the proposed fix change that same row/path/object, or only a nearby fixture/rule/helper?
- What route/template/unit/E2E evidence proves the observed symptom changed after the fix?

Required cautions:
- `Fixture file was fixed` is not evidence that the browser is using that fixture row.
- `A metadata defect exists` is not evidence that it caused the observed row.
- `Tests pass` is not evidence that the manual browser path was exercised.
- `Commit exists` is not evidence that the running server/browser is using it.
- `Nearby row fixed` is not evidence that the displayed row was fixed.

If the exact displayed row/path cannot be tied to the proposed fix, stop with a trace gap. The next task must be runtime trace or reproduction, not implementation.

This rule works together with the Fixture/data-layer UI verification rule below: when the proposed fix changes fixture, seed, import, cached, or other data-layer inputs for a manually observed UI symptom, prove both the exact displayed path and the before/after runtime behavior when feasible.


### Fixture/data-layer UI verification rule

When a fixture, seed data, import data, cached data, or other data-layer change is proposed to fix a manually observed UI/display bug, code inspection alone is not sufficient when the app can be run or the route/template path can be exercised.

Required sequence when feasible:
1. **Before the fix:** verify or reproduce the running UI/route/template path that shows the observed symptom, including the exact row/control/screen and runtime source.
2. **After the fix:** verify the same path again and show that the displayed symptom changed.

If running-browser verification is unavailable, the agent must use the closest direct proof that exercises the same runtime path, such as a route/template/unit test that builds the same view model for the same row/source. The report must explicitly state that browser verification was unavailable and must not claim the manual UI bug is fixed unless the chosen proof exercises the same path.

Examples of acceptable direct proof when browser verification is unavailable:
- a route integration test that exercises the same fixture/database row and asserts the rendered response or view model,
- a unit test that builds the same view model consumed by the template for the same row/source,
- a template/render assertion using the same issue/status object shape and keys,
- a narrow E2E/browser check of the same screen and row when browser verification is feasible.

Required cautions:
- Do not rely on fixture-file inspection alone for a visible UI bug.
- Do not ask the human to verify a change that the agent could verify locally in the running app or route/template path.
- Do not claim a manual UI bug is fixed until the same observed path is verified after the change, or the report clearly states that runtime verification was not possible.


### Shallow vs deep examples

- Shallow: UI shows `Phone invalid`, so the phone number is invalid.
  Deep: Trace stored value → rendered value → validation input → expected field key → generated issue object → template rendering.

- Shallow: A validation rule exists, so validation must be running.
  Deep: Prove the failing runtime path invokes that rule. Check database mode, fixture mode, fallback path, and exception handling.

- Shallow: Button is disabled, so export gating is correct.
  Deep: Verify all reviewer-facing signals agree: traffic light, status text, warning, checkbox, disabled state, backend blocker, and audit record.

- Shallow: E2E passed, so behavior is correct.
  Deep: Confirm the E2E covers the failing mode, data shape, state transition, and assertion. A database-mode E2E does not prove fixture-mode fallback.

- Shallow: Issue appears in UI, so it was freshly calculated.
  Deep: Determine whether the issue came from fresh recalculation, saved ReviewDecision, fixture metadata, stale persisted issue_type, or template default.

- Shallow: The screenshot shows a truncated value, so the data is truncated.
  Deep: Verify stored value separately. UI clipping is not data truncation.

- Shallow: Reviewer accepted, so no Breaker is needed.
  Deep: If the change affects approval/export/audit/raw-data/status consistency, determine whether concrete P0/P1 invariant risk remains.

- Shallow: A failed gate probably needs a quick fix.
  Deep: Failed gate is terminal unless `Failed-First Repair Lane: enabled` is present and the failure qualifies for the one narrow repair allowed by that lane. Otherwise do not diagnose or repair unless the human authorizes a new task.

Deep analysis is not a license for open-ended debugging. It is a bounded proof step. Once the failing layer is identified, implement the smallest fix and prove the failing path.

## E2E Proof-Step Rules

For E2E rewrites, migrations, selector/timing changes, browser fixture changes, or async-heavy UI work, use this stage sequence:

```text
Assessment → one-test proof → small batch → whole file → reliability evidence → Reviewer
```

### E2E proof-stage enforcement

The sequence is a gate, not background guidance. The task contract must declare the current E2E proof stage before implementation begins. Valid stages are:

- `assessment` — identify representative test, fixture/startup path, route, seeded data, selector, and one-test gate. No edits.
- `one-test proof` — modify only the minimum needed for one representative test and run that one-test gate.
- `small batch` — after one-test proof passes, migrate only the authorized 3–5 test batch and run that batch gate.
- `whole file` — after small batch passes, migrate only the authorized affected file and run the full-file gate.
- `reliability evidence` — after whole-file gate passes, run the declared reliability loop if required.

Rules:
- Orchestrator must name the current E2E proof stage in the task contract and Review Packet.
- Implementer may perform only the authorized current stage. Do not skip from assessment or one-test proof to whole-file migration unless the human explicitly authorized that broader stage in the current task contract.
- Passing one stage authorizes only the next declared stage; it does not authorize broad migration, reliability loops, Reviewer, Breaker, commit, or push unless those actions are already included in the task contract and required gates passed.
- Reviewer must request changes or reject when whole-file E2E work was done without required one-test/small-batch proof, when the proof-stage evidence is missing/stale, or when tests were rewritten without individual proof under timeout.
- Do not re-plan/re-run passed stages unless evidence is stale, scope changed, a gate failed/flaked, or a new concrete risk appears.
- Every rewritten E2E test must use hard selector preconditions and hard assertions.
- Reliability loops must use explicit timeout, fail-fast, and stop on first failure.
- If product behavior cannot be proven deterministically, report product/test mismatch and stop instead of weakening the test.


## Canonical and Diagnostic Gate Classification

The active task contract must identify canonical acceptance gates before implementation begins. A command run only for investigation, comparison, reproduction, or diagnosis is diagnostic unless the task contract explicitly promotes it to a canonical gate.

A failed diagnostic command is recorded but does not independently block acceptance when all canonical gates pass and the failure is proven to arise only from test ordering, fixture isolation, environment setup, selector acquisition, or another harness-only condition that does not invalidate canonical evidence.

A diagnostic failure becomes blocking when it reveals a credible product, security, integrity, persistence, audit, raw-data, approval, or export defect; invalidates evidence from a canonical gate; or cannot be separated from application behavior. Codex must not relabel a declared canonical gate as diagnostic after it fails.

The task contract must state:

```text
Canonical acceptance gates:
Diagnostic commands, if any:
Diagnostic-failure classification authority:
```

## Pre-Review Test-Harness Stabilization

The active task contract may authorize one bounded test-harness stabilization iteration before Reviewer invocation. It is disabled unless the contract explicitly states `Test-Harness Stabilization: enabled`, names the authorized test files, and sets a finite iteration budget.

It is permitted only when runtime evidence proves the intended application behavior exists and the failure is isolated to test timing, readiness, fixture setup, selector acquisition, or harness synchronization. The correction must not change product code or semantics, weaken/remove/skip/quarantine/retry-away an assertion, or use an arbitrary fixed sleep as the primary remedy. The focused test must pass repeatedly and all canonical gates must be rerun before Reviewer. This authority expires when Reviewer is invoked.

## Autonomous Multi-Item P1 Campaign Exception

Default behavior outside an explicitly enabled autonomous multi-item P1 campaign:

- a successful commit is terminal for the current task;
- do not begin another item automatically.

Autonomous exception:

- A per-item commit is a checkpoint, not terminal, only when the active current task contract contains all of:
  - `P1 Acceptance Campaign: enabled`
  - `Autonomous multi-item campaign enabled? yes`
  - `Frozen P1 registry approved? yes`
  - `Per-item commit is checkpoint? yes`
  - `Continue after clean checkpoint? yes`
  - a finite maximum item count
  - a finite maximum accepted-commit count
- The autonomous exception changes only post-commit continuation.
- It does not weaken review, QA, Breaker, gate, scope, readiness-packet, commit, push, or restart boundaries.
- Push remains separately authorized.
- An item checkpoint does not authorize registry expansion.

Campaign terminal states:

- every frozen P1 item is complete;
- maximum item or accepted-commit budget is reached;
- any canonical gate remains failed after authorized recovery;
- Reviewer is not `VERDICT=ACCEPT`;
- Breaker is not `BREAKER=PASS`;
- QA is not `QA=PASS`;
- product or UX ambiguity appears;
- schema, migration, external compatibility, security, raw-data, audit, approval, export, or persistence policy requires a decision;
- scope changes or an unexpected file appears;
- the defect is materially different from the current frozen P1;
- runtime proof remains inconclusive.

## Required Handoff State Machine

```text
Implementer ready-for-review + gates passed
→ Orchestrator invokes Reviewer
→ Reviewer Accept?
   no: stop (Request changes/Reject is terminal)
   yes: Breaker required?
       no: commit if auto-commit eligible
       yes: Orchestrator invokes Breaker
           `BREAKER=PASS`?
              no: stop (Breaker P1/P0/FAIL is terminal)
              yes: commit if auto-commit eligible
→ a successful commit is terminal for the current task
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

If Reviewer is required and gates passed, invoke Reviewer. If Reviewer returns `VERDICT=ACCEPT` and Breaker is required, invoke Breaker. These are required actions, not optional human approvals.



## Orchestrator-Led Implementation Completion Rule

For Orchestrator-led implementation tasks, implementation completion is not a terminal state when review is required.

These are evidence for the Review Packet, not stopping points:

- implementation complete,
- declared gates passed,
- working tree dirty only with expected files,
- all changed files are within scope,
- ready-for-review handoff produced by Implementer.

If all are true:

```text
Reviewer required? yes
Declared gates passed? yes
Reviewer verdict returned? no
```

then stopping is forbidden. Orchestrator must invoke Reviewer immediately.

Implementer may stop at `ready for reviewer`; that terminal state belongs only to Implementer. Orchestrator must consume the handoff and continue through required Reviewer/Breaker/commit flow already authorized by the task contract.

Bad:

```text
All gates passed. Working tree is dirty with only expected files. Ready for Reviewer.
```

Good:

```text
All gates passed. Working tree contains only expected files. Reviewer is required, so invoking Reviewer now.
```

After Reviewer `VERDICT=ACCEPT`, invoke Breaker if required. If the task contract includes `Happy-path auto-commit: enabled` and the commit path is eligible, commit expected files and stop. Do not push unless separately authorized.

## Auto-Authorized Action Enforcement Rule

Human authorization is resolved by the task contract, not by the agent's comfort level at each step.

Do not re-ask for permission for an action already authorized by the task contract. If the task contract includes the relevant authorization and all required gates/verdicts have passed, Orchestrator must continue to the next authorized action instead of stopping to ask the human.

Examples:
- If `Happy-path auto-commit: enabled` is present, Reviewer returned exact `VERDICT=ACCEPT`, `Happy-path auto-commit eligible? yes`, Breaker returned exact `BREAKER=PASS` when required, and commit guards passed, Orchestrator must commit expected files and stop. Do not ask `Would you like me to commit?`
- If Reviewer is required and implementation gates passed, invoke Reviewer. Do not ask whether to start review.
- If Breaker is required after Reviewer `VERDICT=ACCEPT`, invoke Breaker. Do not ask whether to start Breaker.

Asking for permission at `ready to commit`, `ready for Reviewer`, or `ready for Breaker` is a workflow violation unless one of these blockers exists:
- auto-commit was not enabled,
- Reviewer has not returned exact `VERDICT=ACCEPT`,
- Breaker is required and has not passed,
- a declared gate or guard failed,
- unexpected scope or dirty files appeared,
- Reviewer `VERDICT=REQUEST_CHANGES` / `VERDICT=REJECT` or Breaker `P1/P0/FAIL` occurred,
- the task contract is ambiguous,
- the action is push and `Happy-path auto-push: enabled` or explicit push authorization is absent.

### Pre-stop Checklist

Before stopping, Orchestrator must verify:

1. Did I reach a real terminal state from this file's state machine?
2. Is there a required next gate, handoff, review, Breaker invocation, commit, or push already authorized by the task contract?
3. Am I asking the human for permission that the task contract already gave?
4. If `Happy-path auto-commit: enabled` is present, did Reviewer return exact `VERDICT=ACCEPT` and `Happy-path auto-commit eligible? yes`?
5. If Breaker was required, did Breaker return exact `BREAKER=PASS`?
6. If the commit path is eligible, did I commit expected files and stop?

If a required authorized next action remains, continue to that action. Stop only at a true terminal state or an explicit blocker.

## Restart / Resume Authorization Rule

On restart, session resume, or when discovering existing dirty files or local commits, do not infer authorization from prior context. Prior discussion, prior recommendations, generated zip files, local dirty files, unpushed commits, `ready to commit` language, or the agent's own judgment that a change is valuable are not authorization.

If there is no current task contract with explicit lane and authorization, Orchestrator may only report status and ask for next instruction. Do not edit, stage, commit, amend, push, run new implementation gates, or start a new task.

A prior statement such as `I recommend committing`, `ready to commit`, `to commit:`, or `these changes are worth retaining` is advisory, not authorization.

Commit requires either:
- a current task contract with `Happy-path auto-commit: enabled` and all required gates, Reviewer verdict, Breaker verdict when required, and commit guards satisfied, or
- an explicit human instruction to commit this specific change.

Push requires explicit current push authorization and is never inferred from local commit existence, branch-ahead status, a clean working tree, or a successful commit.

This rule coexists with the Auto-Authorized Action Enforcement Rule:
- Do not re-ask when the current task contract already authorizes the action and prerequisites are satisfied.
- Do not act when authorization exists only in prior context, restart state, local files, unpushed commits, or inference.

If authorization is ambiguous, stop and ask.

## Reviewer Request Changes / Reject Boundary

Reviewer `Request changes` and `Reject` are terminal states for the current task. They are not permission to return to Implementer, apply an obvious fix, expand scope, rerun gates, invoke Breaker, commit, or push.

Any remediation requires a new explicit human-authorized task. If remediation touches files outside the prior expected-file allowlist, the new human authorization must name the expanded files.

## Breaker P1/P0/FAIL Boundary

Breaker `P1 found`, `P0 found`, or `FAIL` blocks commit. Do not fix, rerun, or commit until the human explicitly authorizes a new remediation task. Breaker `BREAKER=PASS` may proceed to commit if Reviewer returned exact `VERDICT=ACCEPT` and commit gates are satisfied.

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

For narrow test-only remediation, Reviewer defaults to bounded Level 1 review unless the diff changes product code or touches concrete P0/P1 invariants. Reviewer should verify only:
- changed-file scope and lane compliance,
- required gate and guard evidence,
- whether the specific fix matches the failed test/setup issue,
- whether any adjacent test or fixture change is justified by the same narrow failure.

Reviewer should not perform broad architecture review, unrelated UX review, whole-suite analysis, or future-work planning for bounded Level 1 review. Reviewer output should be `VERDICT=ACCEPT` or a blocking verdict with a specific blocking reason.

If Reviewer has not returned a verdict within 10 minutes for a narrow Level 1 review, Orchestrator must stop waiting and report Reviewer wait status. Do not infer acceptance, do not invoke Breaker, do not commit, and do not push.

**Level 2 Standard Review** — normal product/test changes, review-screen UI, autosave, modals, export warnings, audit visibility, and E2E infrastructure.

**Level 3 Deep Review** — export correctness, raw-data immutability, audit integrity, state machines, persistence architecture, schema/data-model, generated CSV, or multi-file architecture.

Reviewers/Breakers report verified items, unverified items, blockers, and readiness impact. Timebox language is guidance, not a reason to skip required checks, but bounded Level 1 review must not expand into unrelated analysis without a concrete risk.

## Role Ownership

- **Orchestrator:** task contract, lane selection, sequencing, gates, evidence, Product UX routing, Reviewer/Breaker invocation, commit/push authorization.
- **Implementer:** smallest safe change, test-first discipline, targeted gates, ready-for-review handoff. No staging, commit, or push.
- **Reviewer:** implementation correctness, evidence validity, scope/lane verification, gate compliance, hard assertions, and auto-commit eligibility.
- **Breaker:** P0/P1 adversarial invariant risks: raw data mutation, audit append-only, export correctness, approval/export bypass, failed autosave leakage, misleading UI state, and overclaimed coverage that affects readiness.
- **Product UX Gatekeeper:** product/UX ambiguity decisions only. Human remains final product authority.

## Feature Development Prompt Pattern

Feature/product behavior work should normally use Orchestrator with `Pre-authorized lane: product/invariant hardening`.

Feature prompts should name exact expected files whenever possible and enforce lane scope, exact scope, bounded tests through `test_gate.py`/`e2e_gate.py`, Product UX Gatekeeper when triggers apply, Reviewer before commit, and Breaker after exact `VERDICT=ACCEPT` when P0/P1 risk exists.

Product changes must protect: **The system suggests. The reviewer decides. Raw data stays unchanged.**


## Machine-Readable Commit Readiness

Commit-capable tasks must use the ignored runtime packet:

```text
.artifacts/commit-readiness.json
```

The packet is evidence, not authority by itself. It must be created only after the final staged diff has passed canonical gates and exact role verdicts. The commit gate must not create, rewrite, or infer packet values.

Required fields:

```text
schema_version
task_id
reviewer_verdict
breaker_verdict
qa_verdict
canonical_gates_passed
scope_guard_passed
commit_authorized
push_authorized
reviewed_head
reviewed_diff_sha256
reviewed_at
informational_notes
required_changes
```

Exact passing values are `VERDICT=ACCEPT`, `BREAKER=PASS`, and `QA=PASS`. Qualified or unknown verdicts are invalid. Non-blocking observations belong in `informational_notes`; work required before acceptance belongs in `required_changes`. A non-empty `required_changes` value blocks commit.

The independent current task identity is supplied to the hook as `HOUSEHOLDER_TASK_ID`; it must exactly match `task_id`. The hook fails closed when the variable is absent.

The reviewed fingerprint is SHA-256 over the exact byte output of:

```bash
git diff --cached --binary --full-index --no-ext-diff HEAD
```

run from the Git repository root. The packet itself must be ignored and unstaged. Immediately before commit, the hook must confirm the current HEAD equals `reviewed_head` and the staged fingerprint equals `reviewed_diff_sha256`. Any implementation or staging change after review therefore requires fresh role verdicts and a new packet. `push_authorized` remains separate and is never inferred from commit eligibility.

## Commit Gate

Auto-commit is disabled unless the prompt includes exactly:

```text
Happy-path auto-commit: enabled
```

Commit only when all are true:
- Reviewer verdict is exactly `VERDICT=ACCEPT`.
- Reviewer states `Happy-path auto-commit eligible? yes`.
- Breaker verdict is exactly `BREAKER=PASS` when Breaker was required.
- QA verdict is exactly `QA=PASS` when QA/UAT was required.
- The commit-readiness packet at `.artifacts/commit-readiness.json` exists, is valid JSON, and matches the reviewed task ID, reviewed HEAD, and staged diff fingerprint.
- The packet sets `canonical_gates_passed=true`, `scope_guard_passed=true`, and `commit_authorized=true`.
- The packet does not include any `REQUIRED_CHANGES` that would conflict with commit eligibility.
- The packet was not staged as part of the commit.
- All required gates passed.
- Artifact guard passed.
- Lane scope guard passed with the declared lane.
- Scope guard passed with exact expected files.
- Fast pre-commit passed: `./.venv/bin/python -m pytest tests/unit tests/integration -q --tb=short`.
- Staged files exactly match expected files.
- No unresolved product questions, schema concerns, failed-first-fix violation, or workflow violation.

Do not commit on qualified or invalid verdicts, missing evidence, failed tests, unexpected files, unresolved product questions, mismatched fingerprints, packet staleness, or packet validation failure. `push_authorized` remains separate and must not be inferred from commit eligibility.

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
