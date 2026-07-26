# E2E Evidence

## Proof Stages

For E2E rewrites, selector/timing changes, browser fixtures, migrations, or async-heavy work:

```text
assessment
→ one-test proof
→ small batch
→ whole file
→ reliability evidence
→ Reviewer
```

The task contract must name the current stage.
Do not skip stages unless the human explicitly authorized the broader staged sequence.

## Real-Path Standard

Critical P1 E2E evidence uses:

- real DOM events;
- real Flask routes;
- real temporary files;
- real request processing;
- hard selector preconditions;
- hard assertions;
- visible-state verification;
- resulting backend or persisted-state verification.

Forbidden as sole proof:

- hidden file-input assignment for drag-and-drop;
- helper-only invocation;
- `if element: assert`;
- silent early return;
- print-only success;
- page-load-only success;
- network-idle-only success;
- absence of exceptions without state verification.

## Timeouts

Default wall-clock limits unless stricter task gates apply:

- single E2E test: 90 seconds;
- full E2E file: 180 seconds;
- reliability iteration: 90 seconds.

Multi-test commands require fail-fast.

## Harness Stabilization

Allowed only when the task contract explicitly enables it, names the files, and sets a finite budget.
Runtime evidence must prove product behavior.
No product-code change, weakened assertion, skip/quarantine, arbitrary fixed sleep, or retry-away behavior.

## Evidence Packet

Record:

```text
Proof stage:
Exact command:
Timeout:
Tests:
Application startup:
Port and URL:
User action:
Visible result:
Network result:
Persisted/resulting state:
Console errors:
Recovery/adversarial case:
Repeat count:
Pass/fail:
```
