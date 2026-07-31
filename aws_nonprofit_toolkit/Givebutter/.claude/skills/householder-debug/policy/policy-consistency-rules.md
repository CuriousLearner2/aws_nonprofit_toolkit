# Policy Consistency Rules

Future `scripts/ci/check_policy_consistency.py` should enforce:

1. Every `ES-##` reference exists in `execution-safety.md`.
2. Only `execution-safety.md` defines execution-state semantics.
3. Agent files may reference or narrow rules but may not redefine them.
4. Task-specific numeric limits belong only in task contracts or frozen task authorizations. Global safety invariants and recommended defaults may live in `execution-safety.md`.
5. This does not reject canonical global constants or defaults such as the ES-04 identical retry, maximum default review cycles, or recommended fast-fix size/timing guidance.
6. Policy precedence appears exactly once.
7. Duplicate authoritative headings or conflicting rule IDs fail.
8. Generic correction budgets, ad hoc retry authority, or unclassified correction language fail.
9. Bounded recovery requires explicit counts for primary, implementation-repair, test-harness-repair, and review-repair batches.
10. Every edit batch must have one declared focused run.
11. A failed focused run may continue only through an applicable preauthorized repair batch under ES-08.
12. Reviewer/Breaker after an authorized diff change requires fingerprint invalidation, refreeze, and rerun of the required roles against the new fingerprint.
13. More than two review cycles fails unless a new authorization explicitly narrows and reauthorizes the task.
14. Auto-commit is valid only from fully green acceptance against one frozen fingerprint.
15. Deferred features may not be used as rejection grounds when role scope explicitly excludes them.
