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

The active task contract must include the exact phrase:

```text
P1 Acceptance Campaign: enabled
```

Without that exact phrase, this skill is disabled.

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
- Post-Commit Residual Remediation enabled? yes/no
- Commit under verification:
- Named P1 defect:
- Frozen residual repair files:
- Maximum residual repair theories: zero / one
- Maximum residual implementation iterations: zero / one / two
- Direct Contract-Caller Inventory required? yes/no
- Frozen direct-caller scope rule:
- Maximum pre-review caller-completion iterations: zero / one
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
- Pre-review caller completion budget remaining:
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
Maximum pre-review caller-completion iterations: 1
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

## Post-Commit Verification and Residual Remediation

A P1 task may combine post-commit verification with bounded residual remediation only when the active current task contract includes the exact phrase:

```text
Post-Commit Residual Remediation: enabled
```

Without that exact phrase, post-commit verification is verification-only. If a defect is found, record the runtime evidence and stop without editing.

This mode is available only when the active task contract separately authorizes the task type, lane, frozen maximum repair files, required agents, repair budgets, and commit authority. It grants no standing authority.

The active task contract must declare:

```text
Post-Commit Residual Remediation enabled? yes/no
Commit under verification:
Named P1 defect:
Frozen residual repair files:
Maximum residual repair theories: zero / one
Maximum residual implementation iterations: zero / one / two
Direct Contract-Caller Inventory required? yes/no
Maximum pre-review caller-completion iterations: zero / one
```

### Same-Defect Boundary

A failure qualifies as residual only when it preserves the same:

- P1 ID;
- user workflow;
- product contract;
- protected invariant;
- expected outcome;
- causal defect family addressed by the commit under verification.

Qualifying examples:

- a client-side stale-response fix prevents stale UI updates, but the same stale request still persists at the server;
- browser duplicate suppression works, but the same no-op transition is still appended by the service;
- the committed repair covers one already-declared runtime mode, but the same defect remains in another already-declared mode.

Non-qualifying examples:

- a different P1 workflow fails;
- another screen or record type exposes a separate defect;
- a new product or UX choice appears;
- a new file outside the frozen residual scope is required;
- schema or migration work is required;
- the original causal defect family is disproven and a materially different architecture is needed.

A non-residual or ambiguous defect requires a new human-authorized task.

### Residual Repair Eligibility

Residual remediation is permitted only when all are true:

1. The failure is a direct-runtime reproduction of the same named P1 defect.
2. The product behavior and acceptance criteria are unchanged.
3. The maximum residual repair file set was frozen before verification began.
4. The remaining failing layer is proven through discriminating runtime evidence.
5. The repair uses one evidence-driven residual theory.
6. No new product or UX decision is required.
7. No schema, migration, authentication, export-policy, approval-policy, raw-data-policy, audit-policy, or external-writeback change is required.
8. Security, persistence, and process-integrity impacts are understood.
9. Required Reviewer, Breaker, and QA/UAT capabilities are available.
10. Auto-commit is separately authorized when a commit may be created.
11. Push remains separately authorized.

### Residual Repair Limits

Canonical maximums are:

```text
Maximum residual repair theories: one
Maximum residual implementation iterations: two
Maximum pre-review caller-completion iterations: one
```

The active task contract may set stricter limits.

Iteration 2 is permitted only before Reviewer invocation and only for a narrow implementation defect within the same proven residual theory and frozen file set. A new theory, additional product file, third implementation iteration, or second caller-completion iteration is terminal.

### Required Residual Sequence

When this mode is enabled:

```text
post-commit runtime verification
→ residual defect reproduction
→ same-defect classification
→ failing-layer proof
→ scope-deviation check
→ bounded residual repair
→ focused test
→ full focused tests
→ direct runtime UAT
→ affected frozen P1 regressions
→ broad regression
→ guards
→ Reviewer
→ Breaker
→ QA/UAT
→ commit if separately authorized
```

Continue through ordinary successful stages without pausing for a new prompt.

### Failed-Gate Boundary

Residual remediation does not authorize repair merely because a gate fails. Failed gates remain governed by the canonical Householder failed-gate policy and require its separate explicit authorization, including the Failed-First Repair Lane when applicable.

Do not reclassify a timeout, socket denial, signal, assertion failure, collection failure, or ambiguous infrastructure failure as residual review feedback.

### Residual Stop Conditions

Stop without editing or committing when:

- the defect is not clearly the same named P1 defect;
- residual classification is ambiguous;
- another file is required outside the frozen residual set;
- a new product or UX choice is required;
- schema or migration work is required;
- security, raw-data, audit, approval, export, persistence, or external-writeback impact is unresolved;
- the residual theory or iteration budget is exhausted;
- Reviewer does not return clean `Accept`;
- Breaker returns P1, P0, or FAIL;
- QA/UAT fails after the allowed repair;
- runtime execution remains unavailable or inconclusive.

Post-commit residual remediation never authorizes unrelated cleanup, another P1 repair, branch or stash changes, push, or broader architecture work.

## Direct Contract-Caller Inventory and Pre-Review Completion

When a P1 repair changes a repository-local request, service, event, payload, or persistence contract, the active task contract may require a direct-caller inventory before editing and before Reviewer handoff.

This rule exists to prevent an otherwise correct contract change from missing repo-local callers and being discovered only during review. It is pre-review completion authority, not a post-review exception.

The active task contract must declare:

```text
Direct Contract-Caller Inventory required? yes/no
Frozen direct-caller scope rule:
Maximum pre-review caller-completion iterations: zero / one
```


Direct-caller completion inventory is limited to repo-local executable callers of the exact changed contract. Repository documentation may be inspected only for compatibility discovery. A documented external, legacy, or supported non-repo-local client is a stop condition, not an authorized completion target.

When enabled, Orchestrator must inventory every repository-local caller of the exact changed contract, including:

- browser or template callers;
- routes and internal service adapters;
- unit, integration, and E2E tests;
- internal scripts or fixtures that submit the same payload;
- repo-local executable scripts or fixtures that directly invoke the same contract.

For each caller record:

```text
Caller path:
Caller type:
Contract used:
Payload or invocation shape:
Can adopt the changed contract mechanically? yes/no
Compatibility promise found? yes/no
Required action:
```

### Mechanical Caller Completion

One pre-review caller-completion iteration may be used only when all are true:

1. The caller is repo-local and directly invokes the exact contract changed by the current P1 repair.
2. The caller is within the frozen direct-caller scope rule declared before implementation.
3. The update is mechanical and preserves the caller's original purpose and assertions.
4. No new production behavior, API policy, compatibility promise, product choice, schema, security, raw-data, audit, approval, or export decision is required.
5. No additional product file outside the frozen repair scope is required.
6. The completion occurs before Reviewer invocation.
7. All affected focused tests, runtime UAT, broad gates, and guards are rerun before Reviewer.

Examples of permitted completion:

- adding the newly required deterministic interaction sequence to repo-local tests that POST to the changed internal route;
- updating a directly associated fixture or browser caller already included in the frozen caller rule;
- preserving the original cancellation or no-op assertion while adopting the new payload contract.

Examples that require a stop:

- a documented external or legacy client cannot adopt the contract without compatibility policy;
- a new route, product file, schema, migration, or fallback mode is needed;
- the caller reveals a different P1 defect;
- the change alters the caller's product semantics rather than only adopting the contract;
- Reviewer has already returned any verdict.

A missed caller discovered by Reviewer remains subject to the canonical terminal-review boundary. Do not use this rule after `Request changes`, `Reject`, or `Accept with minor follow-up`. The purpose of the inventory is to find and complete direct callers before Reviewer.


## Campaign Gate Classification and Harness Stabilization

The active campaign contract must identify canonical acceptance gates and any diagnostic commands. Diagnostic failures follow the canonical Householder classification and cannot be used to excuse a failed canonical gate.

A campaign may use one pre-review test-harness stabilization iteration only when the task contract explicitly enables it, freezes the test-file boundary and finite budget, runtime evidence proves the product behavior, and the canonical Householder stabilization requirements are met. It grants no product-code authority and expires at Reviewer invocation.

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
13. direct contract-caller inventory completion check when the changed contract requires it;
14. Reviewer;
15. Breaker;
16. Product UX Gatekeeper when required;
17. QA/UAT;
18. commit only after clean verdicts.

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
- evidence is not overclaimed;
- every repo-local caller of a changed contract was inventoried when required;
- any mechanical caller completion occurred before Reviewer and within the frozen caller rule.

Required clean result:

```text
VERDICT=ACCEPT
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
- test weakening;
- hidden or unupdated repo-local callers of a changed contract;
- use of caller-completion authority after Reviewer invocation.

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

## Reviewer Verdict Boundary

Reviewer verdicts remain governed by the canonical Householder workflow.

```text
VERDICT=ACCEPT
VERDICT=REQUEST_CHANGES
VERDICT=REJECT
```

Qualified verdicts are invalid. Non-accept verdicts are terminal for the current task. This skill does not authorize post-review correction, reimplementation, rerun, or commit after a non-clean Reviewer verdict. Any remediation requires a new human-authorized task.

Pre-review implementation Iteration 2 and the direct-caller completion rule below cannot be used after Reviewer invocation.

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
- Reviewer returns exact `VERDICT=ACCEPT`;
- Reviewer says auto-commit eligible;
- Breaker returns exact `BREAKER=PASS`;
- QA/UAT returns exact `QA=PASS`;
- The commit-readiness packet validates the reviewed task ID, reviewed HEAD, and reviewed staged diff fingerprint;
- Product UX Gatekeeper is clear when required;
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
Pre-review caller completion cycles used:
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
