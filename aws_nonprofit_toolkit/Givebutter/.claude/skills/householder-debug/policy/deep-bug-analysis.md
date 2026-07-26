# Deep Bug Analysis

Use this policy for non-trivial, cross-layer, mode-specific, fallback, concurrency, stale-state, browser-state, validation, normalization, readiness, export, audit, raw/effective-value, or workflow-safety defects.

## Required Causal Chain

```text
symptom
→ observed facts
→ competing hypotheses
→ discriminating evidence
→ proven failing layer
→ smallest fix
```

Before implementation answer:

1. Exact observed symptom?
2. Exact path, mode, record, and data shape?
3. At least two plausible causes, unless direct evidence already proves one?
4. What evidence distinguishes them?
5. Exact repo files/functions/data proving the cause?
6. Which layer owns the fix?
7. Smallest fix?
8. Test proving the failing path, not a nearby rule?

## Runtime-Path Trace

For UI/status/issue/value bugs, trace:

- stored value;
- rendered value;
- validator/service input;
- key names at each layer;
- raw versus effective value;
- issue object provenance;
- database, fixture, fallback, cache, or stale-runtime mode;
- object delivered to template/browser.

Do not infer:
- stored truncation from visual clipping;
- fresh validation from issue text;
- path invocation from the existence of a rule;
- correct fallback from database-mode tests;
- exact manual-path repair from a nearby fixture/helper change.

## Repo Grounding

Use `Read`, `Grep`, or `Glob` before naming repo paths, functions, routes, classes, or tests.
When repo inspection is unavailable, label names conceptual/provisional.

## Manual UI Findings

Tie the proposed cause to the exact displayed row/control/screen and runtime source.
Verify before and after on the same path when feasible.
If browser verification is unavailable, use a route/template/view-model test exercising the same object and state the limitation.

If the exact path is unproven, stop with a trace gap.
