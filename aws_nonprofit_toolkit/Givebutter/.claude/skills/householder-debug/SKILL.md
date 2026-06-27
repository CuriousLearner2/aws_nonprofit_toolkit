---
name: householder-debug
description: Orchestrates a disciplined Householder / DonorTrust bug-fix loop using the implementer and reviewer agents.
allowed-tools: Read, Grep, Glob, Bash, Task
---

# Householder Debug Skill

Use this skill for Householder / DonorTrust bug fixes, review-screen issues, autosave issues, validation issues, approval/export issues, E2E issues, workflow/docs updates, and small scoped implementation changes.

## Operating model

The workflow is deliberately simple:

```text
Classify → declare gate → make one proof step → verify gate → stop or proceed
```

Do not drift into open-ended debugging. Do not reinterpret failed gates as partial success.

## Core non-negotiables

These rules are intentionally short and high-priority. Apply them before lower-level workflow details.

1. **Assessment-only means direct execution.** If a task is classified as Assessment only, Orchestrator must perform it directly in the current context. Do not spawn child agents, nested Orchestrators, Implementers, Reviewers, Breakers, or Product UX Gatekeeper unless the human prompt explicitly authorizes that handoff.
2. **Assessment-only stops at the report.** Inspect, run bounded commands, collect evidence, recommend one next task, and stop. Do not debug, repair, split, retry, optimize, or implement.
3. **Implementation gates flow to Reviewer.** After an implementation gate passes and review is required, Orchestrator must invoke Reviewer immediately. `Ready for Reviewer` is not a terminal state unless the human requested preparation-only or Reviewer invocation is unavailable/failed and reported.
4. **Terminal states are hard stops.** Assessment delivered, failed-gate report delivered, cleanup completed, Reviewer verdict delivered, commit completed, and push completed are terminal states. Do not start the next logical task without explicit human authorization.
5. **Breaker is risk-based.** Invoke Breaker only for concrete P0/P1 invariant or process-integrity risk, or when the human asks. Do not use Breaker as routine extra review.


## Instruction Compliance Gate

Before beginning meaningful work, identify the task contract:

- task type,
- allowed actions,
- forbidden actions,
- declared command or gate,
- stop conditions,
- terminal state.

Follow the narrowest reasonable interpretation of the human's instructions.

If a command failure, hang, timeout, interruption, unusable/truncated output, or exit `143` matches a declared stop condition, stop command execution and report partial evidence. Do not rerun, debug, split, repair, recover, optimize, or work around the failure unless the human explicitly authorizes that recovery work.

For assessment-only tasks, failure evidence is valid evidence. Do not convert an assessment into implementation, debugging, output-capture repair, optimization, or process management.

### One-shot assessment rule

For assessment-only tasks, each explicitly listed command may be run at most once unless the human explicitly authorizes retries.

If an assessment command fails, hangs, times out, exits `143`, is interrupted, or produces unusable/truncated output:

- mark that command's evidence unavailable or unreliable,
- do not rerun it,
- do not try alternate output capture,
- do not start or poll background jobs,
- do not split the suite or narrow the command,
- do not inspect files to debug the command failure,
- proceed directly to the assessment report using reliable evidence already captured.

### No recovery work in assessment

In assessment-only tasks, recovery work is out of scope unless explicitly requested.

Do not improve command structure, add timeouts, change shell redirection, change fixture strategy, modify output capture, split test batches, or investigate why a command failed. Report the failure as part of the assessment baseline.


### Failed-gate evidence boundary and post-failure command freeze

After any declared gate fails, hangs, times out, exits `143`, is interrupted, or produces unusable/truncated output, stop command execution immediately.

The agent may report only the failed command output already produced and the mechanical stop-report fields required by this workflow. Do not run new commands, inspect additional files, grep for root cause, open related fixtures, diagnose beyond the failed command output, revise the gate, rerun, split, debug, repair, recover, or recommend keeping the change as correct unless the human explicitly authorizes a rescope/debug task.

When a declared acceptance gate fails, the implementation is not accepted. Do not claim the change is correct, ready for Reviewer, ready for commit, or should be kept. Report only the available options: revert, preserve unstaged pending human-authorized rescope, or authorize a new investigation/implementation task.

A failed-gate stop report must stay mechanical:

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
Commit allowed? no
Push allowed? no
No further diagnosis performed because the gate failed.
Next human choices:
1. Revert current changes
2. Preserve unstaged changes and authorize rescope assessment
3. Authorize a new implementation/debug task
```

### Shared-fixture gate rule

Before declaring or running a multi-file gate for a shared fixture/helper change, verify that every file in the gate actually uses the intended shared fixture path.

If fixture/helper usage is unclear, use collect-only or a single-file proof gate first. Do not mix files with local subprocess fixtures, different ports, different app/database fixture paths, or unknown startup semantics in the same acceptance gate unless that broader fixture architecture work is explicitly authorized by the human.

## Source of truth

Repo-local workflow files are authoritative for this project:

```text
.claude/skills/householder-debug/SKILL.md
.claude/agents/orchestrator.md
.claude/agents/implementer.md
.claude/agents/reviewer.md
.claude/agents/breaker.md
.claude/agents/product-ux-gatekeeper.md
```

Global files under `~/.claude/` are optional mirrors only and must not override repo-local files.

Do not create, move, overwrite, or modify Claude workflow/configuration files during product implementation. For this project, workflow-file edits are handled by ChatGPT unless the human explicitly authorizes a Claude workflow-configuration task.

## Core project principle

The system suggests. The reviewer decides. Raw data stays unchanged.

Hard guardrails:

- No CRM/Givebutter API calls or writeback.
- No credentials, auth/RBAC changes, background jobs, bulk actions, or new export formats.
- No raw source-data mutation.
- No contact merge/delete, household_id assignment, cross-import matching, or master contacts/households.
- Preserve append-only audit behavior.
- Do not change schema/migrations unless explicitly authorized.
- Do not approve broad unrelated refactors.

## Role ownership

- **Orchestrator** owns lane selection, sequencing, gates, evidence, review-level selection, Product UX Gatekeeper routing/reporting, and commit/push authorization.
- **Implementer** owns the smallest safe fix, test-first discipline, targeted evidence, and ready-for-review handoff.
- **Reviewer** owns implementation correctness, scope control, evidence validity, required verification, and final review verdict.
- **Breaker** owns adversarial QA for P0/P1 invariant failures and overclaimed coverage. Breaker is not a second Reviewer.
- **Product UX Gatekeeper** owns product/UX ambiguity only. The human is final product authority.

## Task types and terminal states

Classify every task before work begins.

### Assessment only

Use for diagnosis, planning, verification of assumptions, or workflow comprehension.

- No edits, staging, commits, pushes, or implementation agents.
- Run only commands needed to answer the assessment.
- Return facts, gaps, and one narrow recommended next task.

### Implementation only

Use for one confirmed gap.

- Orchestrator delegates to Implementer, then invokes Reviewer when the declared implementation gate passes.
- Do not broaden into related cleanup, product reassessment, schema changes, or alternate theories.
- Use targeted tests first.
- Stop if the first fix fails the declared gate.

### Commit preparation

Use after clean review/evidence.

- Do not re-investigate the bug or re-assess product behavior.
- Verify changed/staged files only.
- Commit only expected files and only when commit authorization is satisfied.

### Push only

Use only when the human explicitly asks to push or enables auto-push.

- No edits, staging, or new commits.
- Verify intended commits, then push only if explicitly authorized.


## Terminal-state stop rule

When a requested task reaches its terminal state, stop and wait for the human. Do not automatically begin the next logical task, even if it seems obvious or useful.

Terminal states include:

- assessment report delivered,
- failed-gate or fail-fast stop report delivered,
- cleanup completed,
- Reviewer verdict delivered,
- commit completed,
- push completed.

After a terminal state, only report final status and readiness. Do not launch a new assessment, invoke agents, run tests, inspect new files, optimize, commit, push, or begin follow-up work unless the human explicitly asks.

Examples:

- Bad: after pushing CI changes, immediately start E2E performance assessment.
- Good: after pushing CI changes, report pushed commit/status and stop.
- Bad: after Reviewer `Accept`, start commit prep without `Happy-path auto-commit: enabled`.
- Good: after Reviewer `Accept`, report ready for commit prep and stop.

## Agent selection

Use the smallest sufficient agent set.

- Assessment/status: Orchestrator only.
- Small direct implementation without review/commit: Implementer only if the human explicitly chose Implementer.
- Code/test change with review or commit-if-clean: Orchestrator → Implementer → Reviewer.
- Product/UX ambiguity: Product UX Gatekeeper before implementation.
- High-risk invariant work: Breaker after Reviewer `Accept`.
- Docs/workflow-only: Level 1 Reviewer; Breaker only for concrete process-integrity risk.
- Push-only: Orchestrator only.

Do not over-delegate to optional agents without concrete need. Do not under-delegate by having Orchestrator self-implement.

## Product/UX gate

Invoke Product UX Gatekeeper when product/UX ambiguity exists, including choices about visible controls, status semantics, warnings/blockers, notes requirements, approval/export confirmation, navigation, decision semantics, or “should/how/best UX” questions.

Do not invoke Product UX Gatekeeper when the human already made the product decision, or for mechanical test-only/docs-only/commit-prep/push-only work.

Always report:

```text
Product ambiguity present? yes/no
Product UX Gatekeeper invoked? yes/no
If not invoked, reason:
Human product decision needed? yes/no
```

## Review packet

Before Reviewer/Breaker handoff, Orchestrator must collect a concise Review Packet:

- task type and review level,
- changed files/functions/tests,
- intended behavior and explicit non-goals,
- affected invariant categories,
- exact test/evidence commands and results,
- caveats, proven claims, claims not being made,
- Product UX Gatekeeper status.

Use anchors first. Avoid broad narrative.

## Acceptance gates

A declared gate is binary.

If the declared command exits nonzero, hangs, times out, exits `143`, or is interrupted, the gate failed unless the task was explicitly assessment-only or exact failures are proven pre-existing and unrelated with baseline evidence.

Partial symptom improvement is not gate success.

Examples:

- `No port errors` is not success if the targeted E2E file still has assertion failures.
- `One test passed` is not success if the declared full-file command failed.
- `/health` passing is not proof that the target page sees seeded test data.
- Complete evidence is not success if Reviewer was required but not invoked.

When a declared gate fails, stop and report:

- gate name,
- exact command and exit code/timeout,
- passed/failed/skipped count,
- failing tests or failure group,
- whether failures are proven pre-existing and unrelated,
- blocking issue,
- whether failed-first-fix is triggered,
- next allowed action.

Do not redefine the gate after partial progress. If the gate was wrong or too broad, stop and ask the human to approve a new gate.

## Failed-first-fix and fail-fast rules

For implementation tasks, the first attempted fix gets one declared gate.

Stop if:

- the first targeted verification fails,
- the command hangs, times out, exits `143`, or is interrupted,
- more than about 8 minutes pass after the first edit without a passing declared gate,
- the root-cause theory changes materially,
- the next likely fix is broader than authorized.

Do not continue into a second theory, second fix, selector redesign, fixture redesign, subprocess rewrite, product-code change, broad test repair, repeated hanging rerun, Reviewer, Breaker, commit, or push unless the human explicitly authorizes a new task or waives the gate.

Stop report must include:

- files changed,
- exact failed/hung command,
- last observed output/test count,
- first attempted fix,
- why it failed,
- current hypothesis,
- why the next step exceeds scope,
- partial-change recommendation: revert / preserve / ask human,
- next proposed human-authorized task.

## E2E proof-step rule

For E2E infrastructure work, do not migrate or rewrite a whole E2E file until one representative test proves the new pattern.

This applies to changes involving Flask/browser startup, Playwright setup, E2E fixtures, database isolation, server lifecycle, ports, waits/timeouts/selectors, subprocess/thread/process cleanup, or pytest-xdist readiness.

Required sequence:

1. **Assessment**
   - Identify one representative test.
   - Identify its fixture/startup path, URL, route, seeded data, database, and selector.
   - Define a one-test acceptance gate.

2. **One-test proof**
   - Change only the minimum code needed for that representative test.
   - Do not modify all tests.
   - Do not use broad replacement scripts.
   - Do not change product code or assertions except mechanical URL/base_url plumbing.
   - The one-test command must exit 0.

3. **Small batch**
   - Only after the one-test proof passes may a 3–5 test batch be migrated.
   - The small-batch gate must exit 0.

4. **Whole file**
   - Only after the small batch passes may the full affected E2E file be migrated.
   - The full-file gate must exit 0 before Reviewer.

Prohibited:

- Migrating all tests before one-test proof.
- Broad automated replacement scripts unless explicitly authorized after a passing proof step.
- Treating `/health` as proof of page/data readiness.
- Inferring architecture blockers without exact command/traceback evidence.
- Proceeding to Reviewer after a failed proof-step gate.

Failed proof-step report must include:

```text
Representative test or batch:
Exact command:
Exit code / timeout:
Passed/failed/skipped:
First failing test:
Failing URL / route / selector if known:
Server health passed? yes/no
Seeded data visible to page? yes/no/unknown
First attempted fix:
Why it failed:
Next smallest testable step:
Ready for Reviewer? no
Ready for commit prep? no
```

## Proof-step progression rule

When a task uses a staged proof sequence, do not re-plan a stage that already passed.

For E2E infrastructure work, the normal progression is:

```text
Assessment → one-test proof → small batch → whole file → Reviewer
```

After a stage passes, Orchestrator may proceed directly to the next human-authorized stage without re-running prior proof gates, re-listing already-proven tests, re-arguing the approach, or invoking extra planning agents.

Reassessment is required only when:

- a declared gate fails, hangs, times out, exits `143`, or flakes,
- prior evidence is stale or predates the current diff,
- the next step materially changes scope,
- product code or product behavior becomes necessary,
- a new concrete risk appears,
- or the human asks for reassessment.

If none of those conditions apply, proceed to the next authorized proof step with a brief classification, one direct implementation delegation, one declared gate, and a stop report if the gate fails.

## Post-gate handoff rule

After a required implementation gate exits 0, the next required handoff is not a new planning phase.

If the workflow requires Reviewer after the gate, Orchestrator should invoke Reviewer immediately with a concise packet. Do not re-run prior proof gates, re-plan the already-approved approach, restate long history, or ask for another decision unless evidence is stale, scope changed, the gate failed/flaked, product code became necessary, a new concrete risk appeared, or the human asked for reassessment.

The handoff packet should normally be under 10 bullets and take under about 60 seconds to prepare. Include only:

- changed files,
- prior blocking issues or proof history when relevant,
- exact current gate command/result,
- product code changed? yes/no,
- assertions changed? yes/no,
- scope/invariant notes needed for review,
- Product UX Gatekeeper status.

If Reviewer returns `Request changes` or `Reject` with concrete blocking fixes and the human authorizes a fix task, Orchestrator should delegate directly to Implementer. Do not start a new planning loop unless the requested fix is ambiguous or out of scope.

### Reviewer handoff is an action, not a status

When Reviewer is required and the declared implementation gates have passed, Orchestrator must invoke the Reviewer agent. Preparing or printing a Review Packet, saying `Ready for Reviewer`, or asking the human to review is not a terminal state and is not sufficient.

For an Orchestrator-led implementation/review flow, the terminal state is Reviewer verdict delivered, not Reviewer packet prepared. Orchestrator may stop at `Ready for Reviewer` only when the human explicitly requested preparation-only, Reviewer invocation is unavailable or fails, or the task type is not an Orchestrator-led implementation/review flow.

## E2E evidence lanes

### Lane 1 fast evidence

Allowed only for localized UI/CSS/template work when product decision is explicit and the change does not affect validation logic, autosave/persistence, approval/export, audit, raw data, decision semantics, modal state machines, selectors/timing infrastructure, fixtures, or recently fixed P0/P1 paths.

Requires:

- focused E2E once,
- full affected E2E file once.

Five-run is required if the human asks, a run fails/flakes, waits/selectors/timing/fixtures/browser infrastructure changed, Reviewer flags reliability risk, or the task no longer fits Lane 1.

### Standard/high-risk five-run

Full-file five-run E2E is mandatory when changes affect validation logic, autosave/persistence, approval/export gating, audit, raw data, decision semantics, modal state machines, flaky timing/selectors, fixtures, or recently fixed P0/P1 paths.

Report exact command/results and whether five-run was required.

## Review levels

### Level 1 Fast Review

Use for docs-only, workflow-only, test-only, or tiny low-risk changes with complete evidence. Delta review only. Target about 90 seconds per agent.

### Level 2 Standard Review

Use for normal product/test changes, Validation Review UI, autosave, row status, modals, export blockers/warnings, audit visibility, and E2E infrastructure changes. Use anchored review. Reviewer target 2–3 minutes; Breaker target 3–4 minutes; hard stop/report at 6 minutes.

### Level 3 Deep Review

Use for export correctness, raw-data immutability, audit integrity, approval/defer state machines, autosave/persistence architecture, schema/data-model changes, generated CSV behavior, or multi-file architectural changes. Start with 3–4 minute risk triage, then 7–8 minute focused review. Hard stop/report at 12 minutes unless the human authorizes more.

Reviewer/Breaker must self-stop at timebox and report verified items, unverified items, blocker/caveat/follow-up status, and whether readiness is blocked.

## Reviewer and Breaker gates

Evidence is input to Reviewer, not a substitute for Reviewer.

For any lane requiring Reviewer:

1. collect evidence,
2. validate gates,
3. invoke Reviewer,
4. wait for final verdict,
5. commit only if Reviewer returns clean `Accept` and commit gates are satisfied.

Breaker is required after Reviewer `Accept` for high-risk invariant work touching validation review, inline editing/autosave, approval/export, decision modals, audit, raw-data immutability, recent P0/P1 paths, or browser-visible state consistency that could affect reviewer decisions.

Do not invoke Breaker for every adjacent historical concern unless a concrete current-change risk appears.

## Workflow violation handling

A workflow violation blocks auto-commit and auto-push until resolved or explicitly waived by the human.

Examples:

- unauthorized push,
- missing required evidence,
- unexpected files,
- bypassed Reviewer/Breaker/Product UX Gatekeeper,
- committing before Reviewer `Accept`,
- skipping a required gate due to friction,
- continuing after failed-first-fix without authorization.

The Reviewer may still judge code correctness, but workflow is not clean until the violation is resolved or waived.

## Commit gate

Happy-path auto-commit is disabled unless the prompt includes exactly:

```text
Happy-path auto-commit: enabled
```

Auto-commit may run only when all are true:

- Reviewer verdict is exactly `Accept`.
- Reviewer states `Happy-path auto-commit eligible? yes`.
- All required tests/E2E gates passed.
- Fast pre-commit passed: `pytest tests/unit tests/integration -q --tb=short`.
- Working tree contains only expected files.
- No product-code files unless authorized.
- No workflow files unless this is a workflow-config task.
- No generated junk, credentials, caches, screenshots, traces, exports, DBs, `.DS_Store`, or unexpected untracked files.
- No required test failures, blocking issues, unresolved product questions, schema concerns, or failed-first-fix violation.
- Staged files exactly match expected files.

If any condition fails, do not commit. Report reason and human decision needed.

`Accept with minor follow-up`, `Request changes`, and `Reject` are not clean happy path.

## Push gate

Auto-push is disabled unless the prompt includes exactly:

```text
Happy-path auto-push: enabled
```

`Ready to push? yes` is only a status report, never permission.

Do not infer push authorization from tests, Reviewer Accept, commit success, clean branch, or branch ahead of origin.

## Output discipline

Reports should be short, structured, and evidence-based. Prefer exact commands, exit codes, file names, and gate status over narrative.

Required readiness fields when relevant:

```text
Acceptance gate passed? yes/no
Failed-first-fix triggered? yes/no
Reviewer invoked? yes/no
Reviewer verdict:
Breaker invoked? yes/no
Ready for Reviewer? yes/no
Ready for commit prep? yes/no
Ready to push? yes/no
```
