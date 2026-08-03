# Stateful campaign wrapper

The wrapper is the authoritative controller for a campaign. It stores each campaign under
`/private/tmp/householder-campaigns/<campaign-id>/` as an append-only `events.jsonl` log and a
derived `state.json` checkpoint. Every command verifies the event hash chain, checkpoint,
repository identity, HEAD, gate blob, contract digest, and persisted containment data.

## Commands

```text
init <campaign-id> <operation-id> <repo> <gate-sha> <contract=sha>...
status <campaign-id>
next <campaign-id>
start-edit <campaign-id> <contract-index> <operation-id>
finish-edit <campaign-id> <contract-index> <operation-id>
record-result <campaign-id> <operation-id> <contract-index>
quarantine <campaign-id> <operation-id> <reason>
stop <campaign-id> <operation-id> <reason>
```

`record-result` accepts only the contract index. Gate, test, commit, and patch evidence must
come from the wrapper's preceding `finish-edit`; caller-supplied evidence is rejected.

## State and evidence

The normal lifecycle is:

```text
READY -> ACTIVE -> VALIDATING -> COMMITTED
```

`FAILED`, `QUARANTINED`, and `STOPPED` are terminal states. `next` creates the bounded
implementation or validation action. `start-edit` admits the current implementation contract
and appends `EDIT_STARTED`. `finish-edit` checks the working tree, runs the architecture gate,
the persisted suites, and `git diff --check`, generates the patch, records exact changed files
and totals, and appends `EDIT_VALIDATED`. A successful `record-result` consumes that evidence.

Each event contains a sequence, timestamp, operation ID, command, payload digest, previous
event hash, event hash, and replayed state snapshot. Appends use the campaign lock, append mode,
flush, and `fsync`; the checkpoint is atomically refreshed afterward. A missing or malformed
checkpoint is rebuilt from a valid event log. Modified checkpoints fail with
`CHECKPOINT_MISMATCH`; broken, reordered, duplicated, deleted, or truncated logs fail with
`EVENT_LOG_CORRUPT`.

Every mutating command has an operation ID. Repeating the same ID and payload returns the
original result without another event. Reusing an ID with different input returns
`OPERATION_CONFLICT`.

## Containment and errors

Repository, worktree, Git identity, contract paths, authorized files, suite IDs, suite argv,
and suite cwd are persisted at initialization. Later commands cannot substitute them. Paths
are canonicalized and symlink escapes, traversal, renames, binaries, submodules, unauthorized
files, alternate Git/index contexts, and ceiling violations are rejected. The wrapper never
accepts shell input or arbitrary commands.

Stable errors include `DIRTY_WORKTREE`, `STALE_HEAD`, `GATE_MUTATED`, `CONTRACT_MUTATED`,
`WORKTREE_MISMATCH`, `GIT_DIR_MISMATCH`, `SUITE_NOT_ALLOWED`, `ARBITRARY_COMMAND_REJECTED`,
`EDIT_NOT_ADMITTED`, `EDIT_ALREADY_STARTED`, `EDIT_ALREADY_VALIDATED`,
`FABRICATED_RESULT_REJECTED`, `UNAUTHORIZED_CHANGE`, `RENAME_REJECTED`, `BINARY_CHANGE`,
`SUBMODULE_REJECTED`, `SYMLINK_ESCAPE`, `EDIT_VALIDATION_FAILED`, `SUITE_FAILED`,
`DIFF_CHECK_FAILED`, `EVENT_APPEND_FAILED`, `EVENT_LOG_CORRUPT`, and
`CHECKPOINT_MISMATCH`.

## Operational sequence

After `init`, an implementation campaign uses only wrapper-directed actions:

```text
next <campaign-id>
start-edit <campaign-id> 0 <admission-operation-id>
finish-edit <campaign-id> 0 <validation-operation-id>
record-result <campaign-id> <result-operation-id> 0
next <campaign-id>
record-result <campaign-id> <validation-result-operation-id> 0
```

The wrapper supplies the action, admission, validation evidence, and final transition; callers
do not provide prior state, commands, paths, patch contents, or test results.

## Limitation

In this environment Codex and the wrapper run under the same OS user, so Codex can physically
write files even though unauthorized or fabricated work cannot be accepted by the wrapper.
True write prevention requires a separate service account, container, VM, or privileged daemon;
that OS-level separation was unavailable here and is intentionally not simulated.
