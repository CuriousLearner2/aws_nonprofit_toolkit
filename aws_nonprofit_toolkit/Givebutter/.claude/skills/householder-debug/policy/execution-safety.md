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
