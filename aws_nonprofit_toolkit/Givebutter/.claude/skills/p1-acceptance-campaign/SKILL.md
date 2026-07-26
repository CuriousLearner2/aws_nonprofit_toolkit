---
name: p1-acceptance-campaign
description: Bounded runtime acceptance and repair workflow for a frozen Householder P1 registry.
allowed-tools: Read, Grep, Glob, Bash, Task
---

# P1 Acceptance Campaign

Subordinate to `.claude/skills/householder-debug/SKILL.md` and all applicable canonical policy modules.

Activation requires the exact phrase:

```text
P1 Acceptance Campaign: enabled
```

This skill grants no lane, edit, commit, push, schema, branch, stash, or product authority by itself.

## Exclusions

Do not use for assessment-only, status-only, push-only, commit-prep-only, manual UAT triage, repository inventory, or workflow-policy redesign.

## Campaign Contract

Before work, declare:

```text
P1 Acceptance Campaign enabled? yes/no
Autonomous multi-item campaign enabled? yes/no
Frozen registry human-approved? yes/no
Per-item commit is checkpoint? yes/no
Continue after clean checkpoint? yes/no
Maximum items:
Maximum accepted commits:
Maximum repairs per item:
Maximum repaired items:
Maximum repairs per commit:
Post-Commit Residual Remediation enabled? yes/no
Commit under verification:
Named P1 defect:
Frozen residual files:
Maximum residual theories/iterations:
Direct Contract-Caller Inventory required? yes/no
Frozen caller scope:
Maximum caller-completion iterations:
Task type and lane:
Browser/socket capability:
Reviewer/Breaker/QA capability:
Product UX routing:
Happy-path auto-commit enabled? yes/no
Push authorized? yes/no
Stop conditions:
Terminal state:
```

Unknown required fields block execution.

## Frozen Registry

For every item record:

```text
P1 ID:
Workflow:
Route/screen:
User action:
Expected visible result:
Required durable business outcome:
Authoritative identity:
Commit boundary:
Serialization/navigation handoff:
Reload/restart expectation:
Configuration matrix:
Duplicate/retry/partial-failure expectation:
Exact transaction-level acceptance test:
Invariant:
Implementation files:
Existing tests:
Fixture/data:
Runtime evidence:
Authorized repair files:
Forbidden files:
Trace gap:
```

Freeze item order, wording, acceptance criteria, evidence, scope, repair budgets, and commit boundaries.
Do not add, remove, merge, split, reorder, or reinterpret items during execution.

## One Item at a Time

No parallel repairs, speculative shared edits, mixed defects, or multiple P1 repairs in one commit.

Before each item report a task compass with current item, phase, evidence, files, budgets, next gate, and stop conditions.

## Evidence and Action Ledgers

Maintain append-only ledgers outside repository files.

Evidence entry:

```text
Observation ID:
P1 ID:
Phase:
Command/browser action:
Runtime:
Visible result:
Network:
Console:
Durable/resulting state:
Artifact:
Classification:
```

Classifications:

- accepted;
- deterministic product defect;
- deterministic harness defect;
- stale expectation;
- environment block;
- inconclusive.

Every edit must link to a reproduced observation.

## Runtime Proof

Every browser-visible P1 requires:

- successful app startup and readiness;
- actual browser navigation and interaction;
- hard visible assertions;
- relevant network result;
- exact durable/resulting-state verification;
- reload/recovery/adversarial evidence when required.

Source inspection, mocked helpers, or unit tests are supporting evidence only.

## Repair Eligibility

Repair only when:

- exact workflow reproduced;
- failing layer proven;
- repair files frozen;
- no product choice, schema/migration, security, raw-data, audit, approval, export, or persistence ambiguity;
- budgets remain;
- required review capabilities exist.

Default maximums unless stricter:

```text
one repair theory
one implementation attempt
one focused rerun
one P1 repair per commit
```

A failed focused repair is terminal.

## Direct Caller Inventory

When a local request/service/payload/persistence contract changes, inventory every repo-local direct caller before editing and before Reviewer when the task contract requires it.
One mechanical pre-review completion iteration may update frozen direct callers without changing semantics.
External compatibility or new product files require a stop.

## Residual Remediation

Enabled only by:

```text
Post-Commit Residual Remediation: enabled
```

The residual defect must be the same P1, workflow, invariant, expected outcome, and causal defect family.
A new theory, file, product choice, schema, security, raw-data, audit, approval, export, or persistence decision requires a new task.

## Validation Ladder

1. exact scope;
2. focused failing test;
3. focused file;
4. adversarial cases;
5. direct browser UAT;
6. network and durable-state verification;
7. relevant unit/integration;
8. broad regression;
9. artifact guard;
10. lane guard;
11. exact scope guard;
12. `git diff --check`;
13. caller inventory completion;
14. Reviewer;
15. Breaker;
16. QA runtime acceptance;
17. commit only after exact verdicts.

Use canonical wrappers, timeouts, verdicts, readiness packet, and commit/push rules.

## Reviewer Fidelity

Reviewer must verify:

- current item only;
- every edit linked to evidence;
- exact scope and immutable registry;
- no invented product behavior;
- repair budget obeyed;
- real runtime path;
- durable outcome and identity;
- no test weakening;
- direct callers complete;
- visible and durable state agree.

Only exact `VERDICT=ACCEPT` can continue.

## Breaker Mandate

Breaker attempts to falsify scope, identity, duplicates, stale state, retry, recovery, raw/effective values, audit, export/readiness, external writeback, direct callers, and budget compliance.

Only exact `BREAKER=PASS` can continue.

## QA Requirement

Runtime QA executes the exact workflow in a real browser and verifies visible plus durable state.
Only exact `QA=PASS` can continue.

## Autonomous Checkpoint

A commit is a checkpoint rather than terminal only when the active contract explicitly enables autonomous multi-item execution, freezes the registry, sets finite budgets, and says to continue after a clean checkpoint.

Continue only when:

- item accepted;
- exact scope maintained;
- worktree clean;
- registry unchanged;
- budgets remain;
- no stop condition exists.

## Stop Conditions

Stop for:

- product/UX decision;
- extra file;
- schema/migration;
- unresolved security, raw-data, audit, approval, export, persistence, or compatibility;
- ambiguous root cause;
- failed focused repair;
- exhausted budget;
- non-accept Reviewer/Breaker/QA verdict;
- unexpected worktree/stash/branch/commit;
- unavailable runtime or inconclusive evidence;
- registry drift.

## Final Report

Provide a P1 matrix with workflow, runtime evidence, durable result, identity, defect, repair, files, commit, Reviewer, Breaker, QA, and limitations.
Also report registry integrity, items assessed/passed/repaired/blocked, budgets, commits, broad regression, final branch/HEAD, worktree, stashes, and push status.
