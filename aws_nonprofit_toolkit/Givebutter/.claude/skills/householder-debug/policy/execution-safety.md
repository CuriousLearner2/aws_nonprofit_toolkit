# Execution Safety

## Policy Precedence

1. Current explicit human authorization
2. Task-specific frozen authorization
3. `policy/execution-safety.md`
4. `policy/task-contract.md`
5. Agent files
6. Generated prompts, packets, and reports

A lower-precedence source may narrow behavior but may not broaden authority or redefine a higher-precedence rule.

## Rule Registry

- `ES-01` Assessment-to-Implementation Firewall
- `ES-02` Review-Capability Preflight
- `ES-03` Reasoning Escalation
- `ES-04` Environment-Only Recovery
- `ES-05` Failed-Gate Handling
- `ES-06` Interrupted or Background Processes
- `ES-07` Restart and Resume
- `ES-08` Edit-Batch, Repair-Batch, and Focused-Run Accounting
- `ES-09` Characterization Firewall
- `ES-10` Review Diff Freeze
- `ES-11` Focused-First Execution
- `ES-12` Compatibility Tripwires
- `ES-13` Budget Enforcement
- `ES-14` Recovery Envelope and Terminal Outcomes

## ES-01 Assessment-to-Implementation Firewall

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

## ES-02 Review-Capability Preflight

Before implementation or auto-commit-capable work:

```text
Reviewer invocation available? yes/no/unknown
Breaker invocation available? yes/no/unknown
Task/subagent mechanism available? yes/no/unknown
If unavailable, exact limitation:
```

The presence of policy files does not prove agents are callable.
Do not replace required Reviewer/Breaker with self-review without explicit human waiver.

## ES-03 Reasoning Escalation

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

## ES-04 Environment-Only Recovery

One identical retry is allowed only when the intended gate did not begin meaningful execution and the sole cause is proven to be wrong working directory, `PATH`, `python`, or `pytest`.

Requirements:

- Givebutter venv exists and imports succeed;
- no files, dependencies, tests, fixtures, hooks, or commands change;
- retry count is 1 of 1.

Not allowed for assertion failures, verified-venv collection failures, missing dependencies, socket restrictions, timeouts, signals, hangs, schema/database/product/test defects, or ambiguous failures.

## ES-05 Failed-Gate Handling

A declared gate passes only on exit code 0.

Failure includes:
- nonzero exit;
- timeout;
- hang;
- exit 143;
- interruption;
- unusable or truncated output.

Default: stop immediately. Do not inspect, grep, rerun, split, diagnose, repair, invoke Reviewer/Breaker, commit, or push.
Ordinary failures are referred to ES-08. If ES-08 provides no applicable batch, stop.

ES-04 identical environment retry remains separate and consumes no repair batch.

## ES-06 Interrupted or Background Processes

If a gate or server cannot be confirmed stopped, stop. Do not continue with gates, review, commit, or push. Do not leave background processes running unless the human explicitly authorized an operational server task.

## ES-07 Restart and Resume

Do not infer authority from prior conversation, generated ZIPs, dirty files, local commits, or earlier recommendations.
A current task contract is required before editing, testing, staging, committing, or pushing.

## ES-08 Edit-Batch, Repair-Batch, and Focused-Run Accounting

These rules are authoritative whenever a task contract allows implementation or repair work.

### Definitions

- A **primary edit batch** begins with the first authorized file modification and ends when its declared focused test command starts.
- A **repair batch** is a separately named, preauthorized edit batch used after a classified failure.
- A **focused run** is one declared focused test command executed against the immediately preceding edit batch.
- Source, test, fixture, expectation, path, import, dependency, environment, and command edits all count as writes unless ES-04 permits an identical environment-only retry.

### Bounded recovery envelope

A failed focused run ends the current edit batch. Further writes are prohibited unless the task contract preauthorized an applicable named repair batch before the primary edit began.

Supported named repair batches:

- implementation repair;
- test-harness repair;
- review repair.

The Orchestrator must classify the failure before consuming a repair batch. ES-05 supplies the gate classification; ES-08 owns the selection of the applicable named batch and whether another edit is permitted. A repair batch may address only the same authorized owner, files, behavior, and acceptance proof. It may not introduce a new product decision, architectural owner, file, schema, workflow, or authorization source.

Each consumed repair batch is followed by exactly one focused run. If no applicable repair batch remains, stop.

### Failure classification

- Wrong cwd, interpreter, or executable path with the exact command otherwise unchanged: apply ES-04; no repair batch consumed.
- Test fixture, mock, harness, or expectation defect: consume a preauthorized test-harness repair batch.
- Defect in the authorized implementation: consume a preauthorized implementation repair batch.
- Reviewer or Breaker finds one concrete in-scope defect: consume a preauthorized review repair batch.
- New owner, file, product decision, architecture, schema, workflow, or authorization source: stop.

Do not relabel repeated debugging as cleanup, plumbing, or continuation of the same batch.

### ES-09 Characterization Firewall

When Git, framework, tool, path, or runtime behavior is uncertain, run a separate assessment-only characterization task first. Characterization may use disposable temporary repositories or fixtures, but it must not edit tracked task files.

### ES-10 Review Diff Freeze

- Freeze and record the staged fingerprint before Reviewer or Breaker starts.
- Any staged-diff change invalidates prior role verdicts and generated evidence.
- Any authorized staged-diff change invalidates the prior fingerprint, role verdicts, and generated evidence.
- When an authorized diff change occurs, refreeze the new staged fingerprint before rerunning the required roles.
- Commit eligibility is reachable only after all required roles are green against the same frozen fingerprint.

## ES-11 Focused-First Execution

Focused-first changes execution efficiency, not the final acceptance standard.

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

### ES-13 Budget Enforcement

Every implementation task must declare exact cumulative limits for:

- authorized files;
- implementation and test lines;
- primary edit batches;
- implementation repair batches;
- test-harness repair batches;
- review repair batches;
- focused runs;
- review cycles;
- elapsed time.

Automatic continuation is allowed only while the task remains inside this recovery envelope.

For a Fast fix, recommended defaults are:

- primary edit batches: 1;
- implementation repair batches: 1;
- test-harness repair batches: 1;
- review repair batches: 1;
- review cycles: 2;
- focused runs: enough for the declared primary and repair batches;
- diagnosis, implementation, and focused proof: roughly 15 minutes before reassessment.

For an Architecture pilot, declare milestone-specific recovery envelopes and cumulative budgets.

Stop when:

- an unauthorized file or owner is required;
- cumulative file or line budgets are exceeded;
- the same focused proof remains red after the applicable repair batches are consumed;
- another implementation strategy is required;
- the maximum review cycles are exhausted;
- evidence cannot be tied to execution;
- elapsed time reaches the declared ceiling.

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

Stop and request review only when a tripwire remains red after the applicable
preauthorized repair batch is exhausted, scope or diff budget is exceeded,
ownership is ambiguous, a product decision is required, or the task would
broadly exceed the approved vertical slice.

### ES-12 Compatibility Tripwires

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
