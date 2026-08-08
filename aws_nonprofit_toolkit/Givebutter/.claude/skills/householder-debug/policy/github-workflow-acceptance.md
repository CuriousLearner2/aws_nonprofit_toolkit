# GitHub Workflow Acceptance

Applies to `.github/workflows/**`.

## Clean Runner Requirements

Acceptance must prove:

- runner starts without a project `.venv`;
- Givebutter venv is created at:
  `$GITHUB_WORKSPACE/aws_nonprofit_toolkit/Givebutter/.venv`;
- critical commands use exact venv executables;
- `$GITHUB_PATH` persistence is explicit when command resolution is relied on;
- `command -v python`, `command -v pytest`, and `sys.executable` are verified before canonical tests;
- workflow-contract tests cover Python version, permissions, venv path, PATH persistence, and command resolution;
- disposable clean-runner simulation passes.

## Local Readiness Versus Production Acceptance

The task contract must explicitly separate:

- local readiness to create the exact commit and prepare the trusted host-publisher handoff;
- production acceptance after a live GitHub Actions run on that exact SHA.

Local checkout evidence alone cannot produce production acceptance.
Host publication evidence must identify the exact published SHA, and GitHub Actions
acceptance must run against that exact SHA.
A rerun of an older workflow definition does not validate a newer commit.

When live access is unavailable, report a live-verification blocker.
Do not infer success.

## Browser CI

When browser E2E is included, require:

- supported pinned runner;
- exact Python/venv;
- repository-supported Node version;
- lockfile-native JS installation;
- required browser only;
- deterministic app/database startup and readiness;
- bounded timeout and cleanup;
- bounded failure artifacts;
- no production credentials or external writes.
