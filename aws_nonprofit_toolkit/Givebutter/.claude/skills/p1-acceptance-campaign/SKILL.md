---
name: p1-acceptance-campaign
description: Runs bounded, evidence-driven P1 runtime acceptance campaigns for Householder / DonorTrust using real browser workflows, frozen scope, strict repair budgets, and required review gates.
allowed-tools: Read, Grep, Glob, Bash, Task
---

# P1 Acceptance Campaign Skill

This skill defines a task-specific execution module for P1 runtime acceptance and bounded remediation.

It is subordinate to:

```text
.claude/skills/householder-debug/SKILL.md
```

If this skill conflicts with the canonical Householder workflow, the canonical workflow wins.

This skill does not grant lane, file, product, schema, commit, push, stash, branch, or destructive Git authority. All such authority must come from the active current task contract.

## Core Quality Rule

```text
No demonstrated user workflow, no acceptance.
No acceptance, no commit.
```

For browser-visible P1 behavior, source inspection, handler presence, unit tests, mocked helpers, or tests blocked before application startup are supporting evidence only. They do not independently prove acceptance.

## Activation

The active task contract must contain exactly:

```text
P1 Acceptance Campaign: enabled
```

Without that phrase, this skill is disabled.

Use it only when the active task contract independently authorizes:

- P1 runtime acceptance;
- task type and lane;
- frozen P1 registry;
- exact or bounded repair files for each item;
- browser and socket-capable execution;
- required agents and gates;
- repair and correction budgets;
- commit authority, if any.

This skill adds bounded execution behavior only. It grants no standing product, lane, scope, commit, or push authority.

## Excluded Task Types

Do not use this skill for:

- assessment-only work;
- verification-only work without repair authority;
- status-only tasks;
- push-only tasks;
- commit-preparation-only tasks;
- stash or branch cleanup;
- repository inventory;
- historical archival;
- read-only review;
- Manual UAT triage;
- reasoning-escalation assessment;
- workflow-policy redesign.

These retain their normal terminal behavior.

A verification-only task that finds a defect must report it and stop unless the active task contract separately authorizes bounded remediation under this skill.

## Current-Task-Only Authority

Campaign authority comes only from the active current task contract.

The following do not count as authority:

- prior conversation;
- prior prompt;
- previous task contract;
- earlier recommendation;
- dirty files;
- uncommitted work;
- prior review status;
- old screenshots or test results;
- restart or resumed session;
- inferred user intent.

A resumed task must receive a current task contract that again contains:

```text
P1 Acceptance Campaign: enabled
```

## Mandatory Task Contract

Before meaningful work, Orchestrator must instantiate:

```text
P1 campaign task contract:
- P1 Acceptance Campaign enabled? yes/no
- Task type:
- Pre-authorized lane:
- Frozen registry source:
- P1 item order:
- Browser-visible items:
- Socket-capable execution available? yes/no/unknown
- Browser automation available? yes/no/unknown
- Reviewer required? yes/no
- Breaker required for repairs? yes/no
- Product UX Gatekeeper required when ambiguity appears? yes/no
- QA/UAT required? yes/no
- Maximum repair attempts per P1:
- Maximum repaired P1 items in campaign:
- Maximum post-review correction cycles per repaired P1:
- Maximum P1 repairs per commit:
- Happy-path auto-commit enabled? yes/no
- Push authorized? yes/no
- Stop conditions:
- Terminal state:
```

Do not proceed when a required field is unknown.

## Capability Preflight

Before runtime testing, verify:

```text
Reviewer invocation available? yes/no/unknown
Breaker invocation available? yes/no/unknown
QA/UAT invocation available? yes/no/unknown
Product UX Gatekeeper invocation available? yes/no/unknown
Browser automation available? yes/no/unknown
Socket-capable local execution available? yes/no/unknown
Screenshot capture available? yes/no/unknown
Runtime trace available? yes/no/unknown
Network inspection available? yes/no/unknown
Console inspection available? yes/no/unknown
```

Rules:

- Do not claim browser acceptance without browser automation and socket-capable execution.
- Do not substitute source inspection for runtime proof.
- Do not implement a repair when required Reviewer or Breaker invocation is unavailable.
- Product UX Gatekeeper is required only for a real unresolved product choice.
- QA/UAT is required for browser-visible P1 acceptance.

## Environment and Repository Preflight

Bootstrap from the Givebutter project directory:

```bash
GIVEBUTTER_DIR="/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter"
cd "$GIVEBUTTER_DIR"
export PATH="$GIVEBUTTER_DIR/.venv/bin:$PATH"

command -v python
command -v pytest
python -c "import sys; print(sys.executable)"
```

Use the Givebutter virtualenv and repository gate wrappers required by the canonical workflow.

Before the campaign:

```bash
git status --short
git branch --show-current
git log -5 --oneline
git stash list
```

Stop if the worktree is not in the state declared by the active task contract.

Do not clean, stash, restore, or absorb unexpected files.

## Frozen P1 Registry

Before execution, build a repo-grounded registry.

For each item record:

```text
P1 ID:
Workflow:
Exact screen or route:
Exact user action:
Expected visible result:
Expected backend, persisted, or returned result:
Invariant protected:
Implementation files:
Existing unit/integration tests:
Existing E2E tests:
Fixture or seeded data:
Runtime evidence required:
Authorized repair files:
Forbidden files:
Any trace gap:
```

Use actual repository paths, routes, functions, tests, and fixtures.

Do not invent files, routes, components, classes, or services.

After grounding, freeze:

- item list;
- item order;
- workflow wording;
- acceptance criteria;
- runtime evidence requirements;
- authorized repair files;
- forbidden files;
- repair budgets;
- commit boundaries.

Do not add, remove, reorder, merge, split, reinterpret, or expand items during execution.

New P1 candidates may be proposed only in the final report.

## One Item at a Time

Process exactly one P1 item at a time.

Do not:

- diagnose a later P1 while repairing the current item;
- modify shared files for several speculative defects;
- run parallel Implementers on different P1 repairs;
- combine separate P1 defects in one diff or commit.

Read-only repository discovery may be batched before registry freeze.

Browser diagnosis, editing, remediation, review, and commit work must remain sequential.

## Task Compass

Before starting each item, report:

```text
Task compass
- Current P1 ID:
- Exact user workflow:
- Current phase:
- Acceptance evidence required:
- Authorized repair files:
- Forbidden files:
- Item repair budget remaining:
- Campaign repaired-item budget remaining:
- Post-review correction budget remaining:
- Next declared gate:
- Stop conditions:
```

## Evidence Ledger

Maintain an append-only evidence ledger outside repository files:

```text
Evidence ledger entry
- Observation ID:
- P1 ID:
- Phase:
- Exact command or browser action:
- Runtime environment:
- Flask startup result:
- Browser URL:
- Observed visible result:
- Network evidence:
- Console evidence:
- Backend or persisted result:
- Artifact reference:
- Classification:
```

Allowed classifications:

```text
pass
deterministic product defect
deterministic test-harness defect
stale test expectation
environment block
inconclusive
```

Do not store campaign ledgers in repository files unless the active task contract explicitly authorizes that documentation.

## Action Ledger

Maintain an append-only action ledger:

```text
Action ledger entry
- Action ID:
- Linked Observation ID:
- P1 ID:
- Exact files:
- Exact change:
- Reason:
- Focused gate:
- Result:
```

Every edit must link to a reproduced observation.

An edit without a linked defect observation is unauthorized.

## Runtime Proof Standard

Every browser-visible P1 item requires:

- successful application startup;
- a known localhost port;
- successful readiness check;
- browser navigation to the actual app;
- actual user interaction;
- visible-state assertions;
- relevant network evidence;
- resulting backend, persisted, or returned-state verification;
- recovery or adversarial coverage where required.

Record:

```text
Flask startup:
Port:
Browser URL:
Initial screenshot:
User action:
Transitional screenshot:
Final screenshot:
Console errors:
Relevant network requests:
Request count:
Response status:
Visible final state:
Backend or persisted result:
Recovery tested:
Pass/fail:
```

Where available, collect a Playwright trace or equivalent runtime trace.

Do not expose credentials, secrets, or private data.

## Real-Path Test Requirements

Critical-path E2E must use:

- real DOM events;
- real Flask routes;
- real temporary files;
- real request processing;
- hard assertions;
- resulting-state verification.

Mocks may supplement rare failure paths but cannot be the only proof.

Forbidden as sole proof:

- direct internal helper invocation;
- hidden file-input assignment for drag-and-drop;
- source-string inspection;
- `if element: assert ...`;
- print-only success;
- page-load-only success;
- network-idle-only success;
- absence of exceptions without visible and resulting-state verification.

## Environment Classification

A browser-visible P1 cannot be accepted unless the app starts successfully.

Classify precisely:

- failure before Flask binds: environment or harness block;
- browser never starts: environment or harness block;
- browser assertion fails after startup: potential product or test defect;
- timeout or signal without stable reproduction: inconclusive infrastructure failure;
- consistently reproduced user-workflow failure after startup: deterministic product or test defect.

Known sandbox socket denial such as:

```text
PermissionError: [Errno 1] Operation not permitted
```

is not a product defect.

Use an authorized socket-capable environment when available.

Do not change ports or test semantics merely to evade restrictions.

## Per-Item Execution Sequence

For each P1 item:

1. Issue the task compass.
2. Confirm exact repository state.
3. Start the real application.
4. Execute the baseline user workflow.
5. Collect runtime evidence.
6. Classify the result.
7. If pass, record the checkpoint and continue.
8. If deterministic product defect, assess repair eligibility.
9. If deterministic test-harness defect, do not change product code.
10. If stale expectation, do not change product behavior.
11. If environment blocked, use authorized socket-capable execution.
12. If inconclusive after one focused investigation, stop the campaign.

## Scope Deviation Check

Before every edit, report:

```text
Scope deviation check
- Current P1 ID:
- Reproduced defect:
- Observation ID proving defect:
- Evidence proving failing layer:
- Proposed edit:
- Proposed edit directly addresses proven layer? yes/no
- Every file already authorized? yes/no
- New product decision required? yes/no
- Unrelated cleanup or refactor included? yes/no
- Another P1 workflow affected? yes/no/unknown
- Schema or migration required? yes/no
- Security or integrity ambiguity? yes/no
- Item repair budget remaining:
- Campaign repaired-item budget remaining:
- Proceed permitted? yes/no
```

Proceed only when:

```text
directly addresses proven layer: yes
every file authorized: yes
new product decision required: no
unrelated cleanup or refactor included: no
schema or migration required: no
security or integrity ambiguity: no
another P1 workflow affected: no, or already covered by frozen acceptance gates
```

Any uncertainty is terminal.

## Bounded Repair Eligibility

A repair is authorized only when all are true:

- application startup succeeded;
- the exact user workflow reproduced the defect;
- the failing layer is proven by discriminating evidence;
- exact repair files were frozen before testing;
- no new product choice is required;
- no new file is required;
- no schema or migration change is required;
- security, raw-data, approval, export, audit, and persistence effects are understood;
- item repair budget remains;
- campaign repaired-item budget remains.

Before editing, record:

```text
P1 repair authorization
- P1 ID:
- Exact defect:
- Observation ID:
- Reproduction command or browser action:
- Proven failing layer:
- Competing hypotheses considered:
- Discriminating evidence:
- Authorized files:
- Forbidden files:
- Single intended repair:
- Focused failing test:
- New product decision required? no
- Schema or migration required? no
- Security or integrity ambiguity? no
- Item repair budget remaining:
- Campaign repaired-item budget remaining:
```

## Repair Budgets

Default maximums, unless the active task contract is stricter:

```text
Maximum repair attempts per P1 item: 1
Maximum post-review correction cycles per repaired P1: 1
Maximum P1 repairs per commit: 1
```

The active task contract must define the campaign-wide repaired-item limit.

Rules:

- one repair theory;
- one implementation attempt;
- one focused rerun;
- no second theory;
- no additional files;
- no opportunistic cleanup.

A failed focused repair is terminal.

## Exact Scope Checks

Compare `git status --short` with the frozen item allowlist:

1. before the first edit;
2. immediately after each edit;
3. before Reviewer;
4. before staging;
5. before commit.

Any unexpected path is terminal.

Do not clean it up, stash it, restore it, or expand scope automatically.

## Repair Validation Ladder

After a repair:

1. exact scope check;
2. single focused failing test;
3. full focused test file;
4. adversarial cases for the current P1;
5. direct browser UAT;
6. network-count and resulting-state verification;
7. relevant unit/integration tests;
8. broad unit/integration regression;
9. artifact guard;
10. lane guard;
11. exact scope guard;
12. `git diff --check`;
13. Reviewer;
14. Breaker;
15. Product UX Gatekeeper when required;
16. QA/UAT;
17. commit only after clean verdicts.

Use repository wrappers and explicit timeouts required by the canonical workflow.

## Reviewer Task-Fidelity Gate

Reviewer must assess task fidelity before technical quality:

```text
Stayed on current P1 item? yes/no
Every edit linked to reproduced runtime evidence? yes/no
Exact scope maintained? yes/no
Registry remained immutable? yes/no
Product behavior invented? yes/no
Unrelated cleanup performed? yes/no
Repair budget obeyed? yes/no
Runtime path matched user workflow? yes/no
Source inspection substituted for UAT? yes/no
Tests weakened? yes/no
Separate P1 repairs mixed? yes/no
```

Any unfavorable answer blocks acceptance.

Reviewer must also verify:

- exact defect reproduced before fix;
- exact workflow passes after fix;
- implementation changes only the proven failing layer;
- tests exercise the real runtime path;
- visible and resulting state agree;
- duplicate action is prevented;
- recovery works;
- raw data remains immutable;
- audit remains append-only;
- approval and export integrity remain intact;
- security is not weakened;
- final guards passed;
- evidence is not overclaimed.

Required clean result:

```text
Verdict: Accept
Happy-path auto-commit eligible? yes
```

Anything else blocks commit.

## Breaker Mandate

Breaker must attempt to falsify:

- scope fidelity;
- registry immutability;
- evidence linkage;
- duplicate-event handling;
- stale state;
- recovery after failure;
- cross-row leakage;
- direct URL or UI manipulation;
- misleading success state;
- raw/effective-value confusion;
- audit mismatch;
- export or approval bypass;
- unsafe DOM injection;
- unsafe navigation;
- unintended external writeback;
- mixed P1 repairs;
- budget violations;
- runtime-path substitution;
- test weakening.

Breaker P1, P0, or FAIL is terminal.

## Product UX Boundary

Invoke Product UX Gatekeeper only when a real unresolved product choice appears.

Codex may not decide:

- labels;
- status meanings;
- warning semantics;
- approval behavior;
- export behavior;
- notes required versus optional;
- navigation behavior;
- disabled or hidden controls;
- multiple-file policy;
- duplicate-upload intent.

A new or ambiguous product decision is terminal and requires human input.

## QA/UAT Requirement

QA/UAT must execute the exact user workflow in a socket-capable real browser environment.

QA/UAT must return:

```text
Pass
```

or:

```text
Fail
```

A pass requires:

- application startup;
- browser action;
- visible-state verification;
- backend or resulting-state verification;
- required adversarial and recovery cases;
- no relevant console error;
- no reliance on source inspection alone.

## Post-Review Correction

A maximum of one post-review correction cycle is permitted per repaired P1 item.

It may occur only when:

- Reviewer returns `Request changes`;
- Reviewer identifies a narrow issue;
- the same files remain authorized;
- no new product choice is required;
- no security or integrity issue is involved;
- no failed gate is being reclassified as review feedback;
- the active task contract authorizes the correction cycle.

After correction:

- focused tests rerun;
- full focused file reruns;
- required broad gates rerun;
- guards rerun;
- direct UAT reruns;
- Reviewer is reinvoked;
- Breaker and QA/UAT are reinvoked when affected.

A second correction cycle is terminal.

Reviewer `Reject` is terminal.

Breaker P1/P0/FAIL is terminal.

## Commit Rules

One P1 repair per commit.

Commit only when:

- runtime workflow passes;
- focused tests pass;
- full focused file passes;
- adversarial cases pass;
- broad regression passes;
- artifact guard passes;
- lane guard passes;
- exact scope guard passes;
- `git diff --check` passes;
- Reviewer returns clean `Accept`;
- Reviewer says auto-commit eligible;
- Breaker passes when required by the active task contract or risk;
- Product UX Gatekeeper is clear when required;
- QA/UAT returns `Pass`;
- staged files exactly match the frozen allowlist;
- the active task contract contains `Happy-path auto-commit: enabled`.

Do not use `--no-verify`.

Do not amend prior commits.

Do not push unless separately and explicitly authorized.

## Checkpoint After Every Item

Append:

```text
P1 checkpoint
- P1 ID:
- Result: pass / repaired / blocked / inconclusive
- Runtime workflow exercised? yes/no
- Evidence collected:
- Product defect found? yes/no
- Test-harness defect found? yes/no
- Files changed:
- Repair budget used:
- Commit:
- Registry unchanged? yes/no
- Scope remained exact? yes/no
- Worktree state:
- Next P1 ID:
```

Continue automatically only when:

- current item is complete;
- registry is unchanged;
- exact scope was maintained;
- worktree is clean;
- no stop condition exists;
- campaign repair budget remains;
- no unresolved P1 defect invalidates later evidence.

## Campaign Stop Conditions

Stop the entire campaign when:

- a new product choice is required;
- a file outside frozen scope is required;
- schema or migration change is required;
- security, raw-data, audit, approval, export, or persistence semantics are unresolved;
- root cause remains ambiguous after one focused investigation;
- the focused repair fails;
- a second repair theory is needed;
- Reviewer does not return clean `Accept`;
- Breaker returns P1/P0/FAIL;
- QA/UAT fails after the one repair;
- an unexpected file appears;
- repair budget is exhausted;
- socket-capable execution is unavailable;
- background processes cannot be confirmed stopped;
- an environment failure remains inconclusive;
- registry integrity is violated.

## Blocker Report

When stopping, report:

```text
Campaign blocker
- Current P1 ID:
- Current phase:
- Exact workflow:
- Exact command or browser action:
- Flask startup succeeded? yes/no
- Browser interaction began? yes/no
- Observation ID:
- Exact failure:
- Classification:
- Proven failing layer:
- Authorized files:
- Additional file required?:
- Product decision required?:
- Repair attempt used?:
- Campaign repair budget remaining:
- Worktree state:
- Smallest human decision or next authorization required:
```

Do not continue into speculative work.

## Final Report

Return a P1 acceptance matrix:

```text
P1 ID
Workflow
Runtime exercised?
Result
Evidence IDs
Screenshots or traces
Network evidence
Backend or persisted-state evidence
Defect found?
Repair made?
Files changed
Commit
Reviewer
Breaker
Product UX
QA/UAT
Remaining limitation
```

Also report:

```text
Registry frozen?:
Registry changed during campaign?:
P1 items assessed:
P1 items passed:
P1 items repaired:
P1 items blocked:
P1 candidates proposed but not added:
Repair attempts used:
Campaign repaired-item budget remaining:
Post-review correction cycles used:
Files changed:
Commits created:
Broad regression result:
Final worktree:
Final branch and HEAD:
Stashes changed?:
Push performed?:
```

Do not claim P1 readiness unless every frozen registry item has:

- real runtime evidence;
- passing acceptance;
- passing QA/UAT;
- no unresolved blocker.
