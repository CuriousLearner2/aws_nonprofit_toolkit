# Durable Outcomes for Stateful P1 Work

## Complete Transaction

Acceptance must prove:

```text
user action
→ route/API success
→ service operation
→ durable commit
→ authoritative durable identity
→ serializer/view-model handoff
→ browser-visible downstream state
→ persistence after reload
```

UI text, HTTP 2xx, an intermediate queue row, or an isolated service return is not sufficient.

## Authoritative Identity

The exact persisted identity must be stored, returned, and used downstream.

Do not reconstruct authoritative identity from:

- filename;
- label;
- timestamp;
- list position;
- newest-first ordering;
- another non-unique display attribute.

If legacy fallback is unavoidable, it must be explicit, bounded, and fail closed when ambiguous.

## Required Evidence

When material to the workflow, prove:

- unset/default, explicit true, and explicit false configuration;
- duplicate names or display values;
- same-second or rapid repeated actions;
- stale or reordered responses;
- retry after timeout;
- partial failure before commit;
- partial failure after commit but before response;
- reload;
- supported process restart;
- cleanup, submit, cancel, archive, or move preserving identity metadata;
- failed writes do not create false success;
- retries do not attach to the wrong object.

At least one transaction-level test is required when the user-visible outcome crosses multiple boundaries.

## Proportionality

Do not impose persistence proof on stateless copy-only, layout-only, or similarly low-risk work.
The task contract must explicitly state whether this doctrine applies.

## P1 Examples

- Validation edit: the exact effective value persists; failed autosave does not change effective state; reload shows the same value.
- Row decision: the exact row decision and audit entry persist without duplication or cross-row contamination.
- Readiness: computed from durable effective state, not stale UI state.
- Export: artifact derives from the correct persisted batch and effective values; failed or blocked state cannot produce misleading success.
- Upload: the exact queue item has a durable batch association and valid review destination.
- Recovery/cleanup: identity metadata moves or is removed consistently without relinking another record.
