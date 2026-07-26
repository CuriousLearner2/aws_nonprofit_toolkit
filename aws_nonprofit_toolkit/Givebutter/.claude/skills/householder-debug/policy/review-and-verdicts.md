# Review, Breaker, and QA

## Handoff Sequence

```text
Implementer ready-for-review + gates pass
→ Orchestrator invokes Reviewer
→ Reviewer accepts?
   no: stop
   yes: Breaker required?
       yes: invoke Breaker
       no: continue
→ QA required?
   yes: invoke QA
→ commit only after exact passing verdicts and commit guards
```

Passing gates, `Ready for Reviewer`, or a clean expected diff are not terminal when review is required.

## Reviewer

Reviewer owns correctness, evidence, scope, lane compliance, maintainability, and auto-commit eligibility.

For stateful P1 work, Reviewer must ask:

```text
What evidence proves that user-visible success corresponds to the exact
durably persisted business object after reload?
```

Reviewer rejects evidence limited to UI success, HTTP 2xx, queue-row creation, service return values, separate component passes, non-authoritative identity, or favorable explicit configuration that omits the documented default path.

Exact verdicts:

- `VERDICT=ACCEPT`
- `VERDICT=REQUEST_CHANGES`
- `VERDICT=REJECT`

Non-accept verdicts are terminal and require a new human-authorized remediation task.

## Breaker

Breaker is required for concrete P0/P1 invariant or process-integrity risk, not every change.

Adversarial checks include:

- raw-data mutation;
- audit append-only violations;
- export/readiness bypass;
- failed autosave leakage;
- cross-row contamination;
- same-second actions;
- duplicate filenames/labels;
- reversed ordering;
- stale response;
- retry after timeout;
- partial failure;
- reload/restart;
- missing/malformed/orphan identity metadata;
- ambiguous legacy state;
- unset/true/false differences.

Exact verdicts:

- `BREAKER=PASS`
- `BREAKER=FAIL`

Failure is terminal.

## QA/UAT Two Modes

### Manual UAT Triage

Activated for human Manual UAT/RC intake.

- consumes screenshots, videos, notes, and repro descriptions;
- normalizes, classifies, prioritizes, and batches findings;
- assessment-only;
- does not claim runtime acceptance;
- does not edit, implement, commit, or push.

### Runtime Acceptance

Activated only when the task contract or P1 campaign explicitly requires it.

- requires browser and socket-capable runtime;
- executes the exact authorized workflow;
- verifies visible and durable resulting state;
- verifies authoritative identity and reload when relevant;
- performs named recovery/adversarial cases;
- remains read-only.

A triage report is not runtime acceptance.
Source inspection cannot substitute when runtime acceptance is required.
If runtime capability is unavailable, stop rather than infer `QA=PASS`.

Exact verdicts:

- `QA=PASS`
- `QA=FAIL`

`QA=PASS` requires empty `REQUIRED_CHANGES`.

QA never replaces Reviewer or Breaker and never authorizes implementation, commit, or push.

## Product UX Gatekeeper

Use only for unresolved product choices: labels, statuses, warnings, approval/export behavior, notes, navigation, hiding/disabling controls, confirmation behavior, or similar UX semantics.

It does not resolve technical uncertainty, failed gates, root cause, commit, or push.
