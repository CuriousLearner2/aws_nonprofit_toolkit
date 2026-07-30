# Execution Safety

## Assessment-to-Implementation Firewall

Assessment-only work stops after root-cause or status reporting.

Allowed:
- evidence collection;
- root-cause proof;
- smallest recommended implementation task;
- expected files and suggested gates.

Forbidden:
- edits;
- new tests;
- implementation gates;
- Reviewer/Breaker handoff;
- staging, commit, amend, or push.

A proven cause is not implementation authorization.

## Review-Capability Preflight

Before implementation or auto-commit-capable work:

```text
Reviewer invocation available? yes/no/unknown
Breaker invocation available? yes/no/unknown
Task/subagent mechanism available? yes/no/unknown
If unavailable, exact limitation:
```

The presence of policy files does not prove agents are callable.
Do not replace required Reviewer/Breaker with self-review without explicit human waiver.

## Reasoning Escalation

Escalate when evidence is contradictory, cross-layer, production-sensitive, or unresolved after one focused attempt; when the same gate fails under different plausible causes; or when persistence, raw-data, audit, approval, export, security, concurrency, stale state, browser events, fallback, or mode-specific behavior remains ambiguous.

Procedure:

1. Preserve worktree, logs, tests, and evidence.
2. Stop guessing.
3. Delegate the narrow question to a stronger or unpinned subagent when available.
4. If unresolved, stop with:

```text
REASONING ESCALATION REQUIRED
- Current phase:
- Unresolved question:
- Evidence collected:
- Competing explanations:
- Why current reasoning is insufficient:
- Recommended capability:
- Exact next action:
- Production files modified? yes/no
- Git status:
```

Do not edit production code while escalation is unresolved.

## Environment-Only Recovery

One identical retry is allowed only when the intended gate did not begin meaningful execution and the sole cause is proven to be wrong working directory, `PATH`, `python`, or `pytest`.

Requirements:

- Givebutter venv exists and imports succeed;
- no files, dependencies, tests, fixtures, hooks, or commands change;
- retry count is 1 of 1.

Not allowed for assertion failures, verified-venv collection failures, missing dependencies, socket restrictions, timeouts, signals, hangs, schema/database/product/test defects, or ambiguous failures.

## Failed Gates

A declared gate passes only on exit code 0.

Failure includes:
- nonzero exit;
- timeout;
- hang;
- exit 143;
- interruption;
- unusable or truncated output.

Default: stop immediately. Do not inspect, grep, rerun, split, diagnose, repair, invoke Reviewer/Breaker, commit, or push.

### Failed-First Repair Lane

Enabled only by the exact task-contract phrase:

```text
Failed-First Repair Lane: enabled
```

One narrow attempt may be authorized only for a pre-classified low-risk issue in already-authorized files:

- brittle test assertion;
- wrong fixture expectation;
- copy/case/punctuation mismatch;
- missing stable marker in an authorized template;
- test expecting the wrong seeded value;
- presentational template mismatch.

Stop without repair when backend route/service/repository logic, schema, raw data, export, audit, review/autosave/approval semantics, workflow state, new product decisions, extra files, or multiple affected pages/tests are implicated.

After repair, rerun only the failed focused gate. If it fails again, stop.

## Interrupted or Background Processes

If a gate or server cannot be confirmed stopped, stop. Do not continue with gates, review, commit, or push. Do not leave background processes running unless the human explicitly authorized an operational server task.

## Restart and Resume

Do not infer authority from prior conversation, generated ZIPs, dirty files, local commits, or earlier recommendations.
A current task contract is required before editing, testing, staging, committing, or pushing.

## Focused-First Execution Contract

Focused-first changes execution efficiency, not the final acceptance standard.

### Evidence-Backed Focused-First Rules

Before diagnosis or implementation, every execution-context claim must be proven
with an exact command, file lookup, or tool-capability check. Report missing,
absent, or unavailable items explicitly; do not guess paths, wrappers,
interpreters, or role mechanisms.

Verify the active local Python and pytest runtime against the supported CI
baseline. If they differ, declare the mismatch rather than treating the local
runtime as canonical.

Prove Reviewer, Breaker, and QA invocation plus verdict collection before any
role is spawned. Presence of policy files does not prove the tools are callable.

Classification starts as engineering investigation whenever the authoritative
owner is ambiguous or multiple layers disagree. Keep implementation unauthorized
until that ambiguity is resolved by focused evidence.

Assessment and implementation are separate explicit authorizations. Assessment
never implies implementation authorization.

Automatic continuation is allowed only after explicit implementation
authorization and explicit reclassification to a narrower execution class, and
only while the declared milestones, tripwires, scope, and budgets remain green.

### Execution-Context Preflight

Before diagnosis or implementation, confirm once:

```text
Execution context:
- Repository root:
- Application root:
- Branch:
- HEAD:
- Tracked worktree:
- Stashes:
- Canonical policy path:
- Project Python:
- Project pytest:
- Focused gate wrappers:
- Broad gate command:
- Reviewer/Breaker/QA invocation and verdict collection:
- Known unrelated runtime artifacts:
```

Do not guess paths, interpreters, wrappers, gate names, or role-collection mechanics.
Two failed path or command guesses trigger reassessment before continuing.

If a wrapper or command does not exist, report it as absent instead of
substituting a nearby command or assuming a renamed script.

### Five-Minute Feasibility Classification

For a reproducible defect, spend at most roughly five minutes establishing:

- one deterministic defect proof or equivalent runtime reproduction;
- the authoritative owner;
- the adjacent compatibility proof most likely to catch collateral damage;
- expected product files;
- expected product diff size;
- materially connected downstream consumers.

Classify before product edits:

```text
Execution classification:
- Fast fix
- Engineering investigation
- Architecture pilot
```

A **Fast fix** normally has one authoritative owner, no unresolved product decision,
at most two product files, and an expected product diff of roughly 30 lines or fewer.

An **Engineering investigation** is required when ownership or identity is ambiguous,
multiple representations disagree, persistence/read models diverge, schema or workflow
implications appear, the expected product diff materially exceeds the fast-fix budget,
or baseline behavior is already inconsistent.

An **Architecture pilot** must declare a narrow vertical slice, milestone gates,
compatibility tripwires, and explicit file/diff budgets.

Reclassification and stopping are successful outcomes. Do not force an engineering
investigation through the fast-fix lane.

### Focused-First Escalation Ladder

For an authorized implementation:

1. deterministic defect proof;
2. adjacent compatibility proof;
3. focused test case;
4. focused test file;
5. affected integration or browser files;
6. canonical broad gates;
7. Reviewer, Breaker, QA, readiness, commit, push, exact-SHA CI, and live acceptance.

Do not use broad gates to discover whether an implementation approach is viable.
Run broad gates only after focused proof is green and the diff is stable.

Rerun only evidence materially invalidated by a later edit.

### Attempts, Time, and Scope Budgets

For a Fast fix:

- allow one primary implementation attempt;
- allow one narrow correction;
- stop and reclassify when focused proof is not green within roughly 15 minutes;
- stop when ownership remains unclear, scope expands, an adjacent contract regresses,
  product files exceed the task budget, or the product diff materially exceeds estimate.

The 15-minute budget covers diagnosis, implementation, and focused proof.
Full release acceptance has a separate time budget.

For an Architecture pilot:

- declare milestones and mandatory compatibility tripwires;
- advance automatically only when the current milestone and all tripwires are green;
- stop after a second failed approach at any milestone;
- stop when file, diff, schema, migration, consumer, or vertical-slice bounds are crossed.

### Dirty-File Provenance

If tracked files are already dirty before implementation, classify each file
explicitly:

- authorized current-task scope;
- authorized pre-existing work protected by an exact scope allowance;
- unresolved provenance that blocks implementation.

If any dirty tracked file cannot be placed in one of those three buckets, stop
and do not implement. Unresolved provenance blocks implementation until it is
either attributed to the current task or excluded by exact scope.

### Budget Semantics

Budgets are concrete and internally consistent:

- primary expected files are the default file set for the proven owner;
- maximum authorized files is the hard ceiling;
- optional second files require proof that the focused evidence cannot be
  completed without that exact companion file, and the contract must name it;
- third product file or any unproven optional file exceeds the budget
  immediately.

For a fast fix, the normal budget is one primary file plus at most one proven
optional file. Any request for a third product file, or any optional file that
cannot be proven necessary, is a stop-and-reclassify condition.

### Autonomous Checkpoints

At milestone completion or approximately every ten minutes, emit:

```text
Execution checkpoint:
- Milestone:
- Product files changed:
- Product diff size:
- Tests green:
- Tests red:
- Scope variance:
- Next action:
- Stop condition triggered: yes/no
```

The checkpoint is for self-governance and auditability.
Do not pause for human approval while milestone gates are green, tripwires pass,
scope remains within budget, and no stop condition is triggered.

Stop and request review only when a tripwire remains red after one narrow correction,
scope or diff budget is exceeded, ownership is ambiguous, a product decision is
required, or the task would broaden beyond the approved vertical slice.

### Compatibility Tripwires

Every defect repair or architecture pilot must name:

- the exact defect proof;
- at least one adjacent compatibility proof;
- any invariant tests that must run after every product edit.

A tripwire failure blocks progression. Do not weaken the tripwire to fit the patch.

### Reuse Before Expansion

Before creating a new harness, fixture, helper, or generalized abstraction, search for
and reuse existing project fixtures, browser helpers, server launchers, identity
helpers, and gate commands.

Record desirable but nonessential cleanup in a deferred list. Do not implement
"while here" refactors inside the current task.
