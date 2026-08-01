from __future__ import annotations

import json
import os
import subprocess
import sys
import shutil
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "ci"))

import householder_runner  # noqa: E402


TASK_ID = "HOUSEHOLDER-WORKTREE-RUNNER-CORE-20260731"
_GIT_ENV_STRIP = (
    "GIT_INDEX_FILE",
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_COMMON_DIR",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
)


def git_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in _GIT_ENV_STRIP:
        env.pop(key, None)
    return env


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=check, env=git_env())


@pytest.fixture(autouse=True)
def isolate_git_repo_selection_env(monkeypatch):
    original_run = subprocess.run

    def sanitized_run(*args, **kwargs):
        env = dict(kwargs.get("env", os.environ.copy()))
        for key in _GIT_ENV_STRIP:
            env.pop(key, None)
        kwargs["env"] = env
        return original_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", sanitized_run)
    yield


def make_repo(tmp_path: Path, layout: str = "flat") -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    origin = tmp_path / "origin.git"
    repo.mkdir(parents=True, exist_ok=True)
    origin.mkdir(parents=True, exist_ok=True)
    git(origin, "init", "--bare")
    git(repo, "init")
    git(repo, "branch", "-M", "main")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test User")
    seed = repo / "seed.txt"
    seed.write_text("seed\n", encoding="utf-8")
    source_householder_state = Path(__file__).resolve().parent.parent.parent / "scripts" / "ci" / "householder_state.py"
    if layout == "flat":
        app_root = repo
    elif layout == "nested":
        app_root = repo / "aws_nonprofit_toolkit"
    else:
        raise ValueError("unknown layout")
    target_householder_state = app_root / "Givebutter/scripts/ci/householder_state.py"
    target_householder_state.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_householder_state, target_householder_state)
    git(repo, "add", "seed.txt")
    git(repo, "add", str(target_householder_state.relative_to(repo)))
    git(repo, "commit", "-m", "seed")
    git(repo, "remote", "add", "origin", str(origin))
    git(repo, "push", "-u", "origin", "main")
    git(repo, "fetch", "origin", "main")
    return repo, app_root


def bind(monkeypatch, repo: Path) -> None:
    monkeypatch.setattr(householder_runner, "repo_root", lambda: repo)


def record_path(repo: Path, task_id: str = TASK_ID) -> Path:
    return repo / "Givebutter/.artifacts" / f"householder-runner.{task_id}.json"


def read_record(repo: Path, task_id: str = TASK_ID) -> dict[str, object]:
    return json.loads(record_path(repo, task_id).read_text(encoding="utf-8"))


def write_record(repo: Path, payload: dict[str, object], task_id: str = TASK_ID) -> None:
    record_path(repo, task_id).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def create_campaign(monkeypatch, repo: Path, parent: Path, task_id: str = TASK_ID, *, app_root: Path | None = None) -> dict[str, object]:
    app_root = app_root or repo
    monkeypatch.chdir(app_root)
    bind(monkeypatch, app_root)
    return householder_runner.create(task_id, parent)


def test_create_uses_dedicated_branch_and_worktree(monkeypatch, tmp_path):
    repo, _ = make_repo(tmp_path)
    parent = tmp_path / "external-worktrees"

    report = create_campaign(monkeypatch, repo, parent)

    branch = f"codex/{TASK_ID}"
    worktree = parent / TASK_ID
    assert report["task_id"] == TASK_ID
    assert report["branch"] == branch
    assert Path(report["worktree_path"]) == worktree
    assert worktree.exists()
    assert git(repo, "branch", "--show-current").stdout.strip() == "main"
    assert git(worktree, "branch", "--show-current").stdout.strip() == branch
    assert read_record(repo)["base_sha"] == git(repo, "rev-parse", "HEAD").stdout.strip()
    assert (worktree / "Givebutter/.artifacts/householder-task-state.json").exists()


def test_create_resolves_nested_actual_layout(monkeypatch, tmp_path):
    repo, app_root = make_repo(tmp_path, layout="nested")
    parent = tmp_path / "external-worktrees"

    report = create_campaign(monkeypatch, repo, parent, app_root=app_root)

    branch = f"codex/{TASK_ID}"
    worktree = parent / TASK_ID
    assert report["task_id"] == TASK_ID
    assert report["branch"] == branch
    assert Path(report["worktree_path"]) == worktree
    assert worktree.exists()
    assert git(app_root, "branch", "--show-current").stdout.strip() == "main"
    assert git(worktree, "branch", "--show-current").stdout.strip() == branch
    assert read_record(app_root)["base_sha"] == git(app_root, "rev-parse", "HEAD").stdout.strip()
    assert (worktree / "aws_nonprofit_toolkit/Givebutter/.artifacts/householder-task-state.json").exists()


def test_create_rejects_dirty_main(monkeypatch, tmp_path):
    repo, _ = make_repo(tmp_path)
    parent = tmp_path / "external-worktrees"
    (repo / "seed.txt").write_text("dirty\n", encoding="utf-8")
    bind(monkeypatch, repo)
    monkeypatch.chdir(repo)

    with pytest.raises(ValueError, match="clean main"):
        householder_runner.create(TASK_ID, parent)


def test_create_rejects_diverged_main(monkeypatch, tmp_path):
    repo, _ = make_repo(tmp_path)
    parent = tmp_path / "external-worktrees"
    extra = repo / "extra.txt"
    extra.write_text("extra\n", encoding="utf-8")
    git(repo, "add", "extra.txt")
    git(repo, "commit", "-m", "diverge main")
    bind(monkeypatch, repo)
    monkeypatch.chdir(repo)

    with pytest.raises(ValueError, match="HEAD and origin/main"):
        householder_runner.create(TASK_ID, parent)


def test_create_rejects_duplicate_task_id(monkeypatch, tmp_path):
    repo, _ = make_repo(tmp_path)
    parent = tmp_path / "external-worktrees"
    create_campaign(monkeypatch, repo, parent)

    with pytest.raises(ValueError, match="duplicate task"):
        create_campaign(monkeypatch, repo, parent)


def test_create_cleans_up_on_expected_ledger_failure(monkeypatch, tmp_path):
    repo, _ = make_repo(tmp_path)
    parent = tmp_path / "external-worktrees"
    bind(monkeypatch, repo)
    monkeypatch.chdir(repo)
    real_run_git = householder_runner.run_git
    calls: list[tuple[tuple[str, ...], Path | None]] = []

    def runner(args, *, cwd=None, binary=False):
        calls.append((tuple(args), cwd))
        return real_run_git(args, cwd=cwd, binary=binary)

    def fake_householder(worktree_path, args, *, json_output=False):
        if args[0] == "initialize":
            raise ValueError("initialize failed")
        raise AssertionError(f"unexpected householder_state call: {args}")

    monkeypatch.setattr(householder_runner, "run_git", runner)
    monkeypatch.setattr(householder_runner, "run_householder_state", fake_householder)

    with pytest.raises(ValueError, match="initialize failed"):
        householder_runner.create(TASK_ID, parent)

    assert ("worktree", "remove", "--force", str((parent / TASK_ID).resolve())) in [entry for entry, _ in calls]
    assert ("branch", "-D", f"codex/{TASK_ID}") in [entry for entry, _ in calls]
    assert not (parent / TASK_ID).exists()


def test_create_does_not_swallow_unexpected_exceptions(monkeypatch, tmp_path):
    repo, _ = make_repo(tmp_path)
    parent = tmp_path / "external-worktrees"

    def fake_householder(worktree_path, args, *, json_output=False):
        if args[0] == "initialize":
            raise RuntimeError("boom")
        raise AssertionError(f"unexpected householder_state call: {args}")

    monkeypatch.setattr(householder_runner, "run_householder_state", fake_householder)

    with pytest.raises(RuntimeError, match="boom"):
        create_campaign(monkeypatch, repo, parent)


def test_create_rejects_unignored_in_repo_parent(monkeypatch, tmp_path):
    repo, _ = make_repo(tmp_path)
    bind(monkeypatch, repo)
    monkeypatch.chdir(repo)

    with pytest.raises(ValueError, match="outside the repository tracked tree"):
        householder_runner.create(TASK_ID, repo / ".codex-worktrees")


def test_temp_repo_git_commands_ignore_hostile_inherited_index(monkeypatch, tmp_path):
    monkeypatch.setenv("GIT_INDEX_FILE", ".git/index")
    repo, _ = make_repo(tmp_path)
    parent = tmp_path / "external-worktrees"

    report = create_campaign(monkeypatch, repo, parent)

    worktree = parent / TASK_ID
    assert report["worktree_path"] == str(worktree)
    assert worktree.exists()
    assert git(repo, "status", "--short", "--untracked-files=no").stdout.strip() == ""
    assert git(worktree, "status", "--short", "--untracked-files=no").stdout.strip() == ""


def test_resolve_app_root_is_unique_and_fail_closed(monkeypatch, tmp_path):
    repo, app_root = make_repo(tmp_path)
    bind(monkeypatch, app_root)

    assert householder_runner._resolve_app_root(repo) == repo

    nested_repo = tmp_path / "nested-repo"
    nested_repo.mkdir()
    (nested_repo / "aws_nonprofit_toolkit/Givebutter/scripts/ci").mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        Path(__file__).resolve().parent.parent.parent / "scripts" / "ci" / "householder_state.py",
        nested_repo / "aws_nonprofit_toolkit/Givebutter/scripts/ci/householder_state.py",
    )
    assert householder_runner._resolve_app_root(nested_repo) == nested_repo / "aws_nonprofit_toolkit"

    ambiguous = tmp_path / "ambiguous"
    (ambiguous / "Givebutter/scripts/ci").mkdir(parents=True, exist_ok=True)
    (ambiguous / "aws_nonprofit_toolkit/Givebutter/scripts/ci").mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        Path(__file__).resolve().parent.parent.parent / "scripts" / "ci" / "householder_state.py",
        ambiguous / "Givebutter/scripts/ci/householder_state.py",
    )
    shutil.copy2(
        Path(__file__).resolve().parent.parent.parent / "scripts" / "ci" / "householder_state.py",
        ambiguous / "aws_nonprofit_toolkit/Givebutter/scripts/ci/householder_state.py",
    )
    with pytest.raises(ValueError, match="unique app root"):
        householder_runner._resolve_app_root(ambiguous)


def test_status_fails_outside_recorded_worktree(monkeypatch, tmp_path):
    repo, _ = make_repo(tmp_path)
    parent = tmp_path / "external-worktrees"
    create_campaign(monkeypatch, repo, parent)
    bind(monkeypatch, repo)
    monkeypatch.chdir(repo)

    with pytest.raises(ValueError, match="recorded worktree"):
        householder_runner.status(TASK_ID)


def test_status_rejects_wrong_branch(monkeypatch, tmp_path):
    repo, _ = make_repo(tmp_path)
    parent = tmp_path / "external-worktrees"
    create_campaign(monkeypatch, repo, parent)
    worktree = parent / TASK_ID
    git(worktree, "checkout", "-b", "detour")
    bind(monkeypatch, repo)
    monkeypatch.chdir(worktree)

    with pytest.raises(ValueError, match="wrong branch"):
        householder_runner.status(TASK_ID)


def test_start_edit_authorizes_before_transition_and_consumes_nothing(monkeypatch, tmp_path):
    repo, _ = make_repo(tmp_path)
    parent = tmp_path / "external-worktrees"
    create_campaign(monkeypatch, repo, parent)
    worktree = parent / TASK_ID
    bind(monkeypatch, repo)
    monkeypatch.chdir(worktree)

    calls: list[tuple[object, ...]] = []

    def fake_householder(worktree_path, args, *, json_output=False):
        calls.append((worktree_path, *args, json_output))
        if args[0] == "status":
            return {"counters": {}}
        if args[0] == "can-write":
            return {"allowed": False, "reason": "blocked"}
        raise AssertionError("begin-edit must not be called after denied authorization")

    monkeypatch.setattr(householder_runner, "run_householder_state", fake_householder)

    with pytest.raises(ValueError, match="blocked"):
        householder_runner.start_edit(TASK_ID, "primary")
    assert [call[1] for call in calls] == ["status", "can-write"]
    assert calls[0][0] == worktree
    assert calls[1][0] == worktree


def test_run_focused_authorizes_before_transition(monkeypatch, tmp_path):
    repo, _ = make_repo(tmp_path)
    parent = tmp_path / "external-worktrees"
    create_campaign(monkeypatch, repo, parent)
    worktree = parent / TASK_ID
    bind(monkeypatch, repo)
    monkeypatch.chdir(worktree)

    calls: list[tuple[object, ...]] = []

    def fake_householder(worktree_path, args, *, json_output=False):
        calls.append((worktree_path, *args, json_output))
        if args[0] == "status":
            return {"counters": {}}
        if args[0] == "can-run-focused":
            return {"allowed": False, "reason": "blocked"}
        raise AssertionError("begin-focused-run must not be called after denied authorization")

    monkeypatch.setattr(householder_runner, "run_householder_state", fake_householder)

    with pytest.raises(ValueError, match="blocked"):
        householder_runner.run_focused(TASK_ID, [sys.executable, "-c", "print('nope')"])
    assert [call[1] for call in calls] == ["status", "can-run-focused"]
    assert calls[0][0] == worktree
    assert calls[1][0] == worktree


def test_run_focused_cli_reaches_runner_and_preserves_arguments(monkeypatch, tmp_path, capsys):
    repo, _ = make_repo(tmp_path)
    bind(monkeypatch, repo)
    monkeypatch.chdir(repo)
    calls: list[tuple[str, list[str]]] = []

    def fake_run_focused(task_id, command):
        calls.append((task_id, list(command)))
        return {"task_id": task_id, "command": list(command)}

    monkeypatch.setattr(householder_runner, "run_focused", fake_run_focused)

    exit_code = householder_runner.main([
        "run-focused",
        "--task-id",
        TASK_ID,
        "--",
        sys.executable,
        "-c",
        "print('cli smoke')",
    ])

    assert exit_code == 0
    assert calls == [
        (
            TASK_ID,
            ["--", sys.executable, "-c", "print('cli smoke')"],
        )
    ]
    out = capsys.readouterr().out
    assert '"command": [' in out
    assert "print('cli smoke')" in out


def test_run_focused_records_real_success_and_failure_exit_codes(monkeypatch, tmp_path):
    repo, _ = make_repo(tmp_path)
    parent = tmp_path / "external-worktrees"
    create_campaign(monkeypatch, repo, parent)
    worktree = parent / TASK_ID
    bind(monkeypatch, repo)
    monkeypatch.chdir(worktree)

    householder_runner.start_edit(TASK_ID, "primary")

    success = householder_runner.run_focused(TASK_ID, [sys.executable, "-c", "print('ok')"])
    assert success["exit_code"] == 0
    assert "ok" in success["stdout"]

    failure = householder_runner.run_focused(TASK_ID, [sys.executable, "-c", "import sys; sys.exit(7)"])
    assert failure["exit_code"] == 7


def test_start_review_requires_frozen_staged_fingerprint_and_records_review_state(monkeypatch, tmp_path):
    repo, _ = make_repo(tmp_path)
    parent = tmp_path / "external-worktrees"
    create_campaign(monkeypatch, repo, parent)
    worktree = parent / TASK_ID
    bind(monkeypatch, repo)
    monkeypatch.chdir(worktree)
    (worktree / "seed.txt").write_text("reviewed\n", encoding="utf-8")
    git(worktree, "add", "seed.txt")
    householder_runner.start_edit(TASK_ID, "primary")
    assert householder_runner.run_focused(TASK_ID, [sys.executable, "-c", "import sys; sys.exit(0)"])["exit_code"] == 0

    result = householder_runner.start_review(TASK_ID)

    assert result["frozen_staged_fingerprint"]
    assert result["ledger_after"]["review_active"] is True
    assert read_record(repo)["frozen_staged_fingerprint"] == result["frozen_staged_fingerprint"]


def test_finish_review_requires_accept_and_pass_for_frozen_fingerprint(monkeypatch, tmp_path):
    repo, _ = make_repo(tmp_path)
    parent = tmp_path / "external-worktrees"
    create_campaign(monkeypatch, repo, parent)
    worktree = parent / TASK_ID
    bind(monkeypatch, repo)
    monkeypatch.chdir(worktree)
    (worktree / "seed.txt").write_text("reviewed\n", encoding="utf-8")
    git(worktree, "add", "seed.txt")
    householder_runner.start_edit(TASK_ID, "primary")
    assert householder_runner.run_focused(TASK_ID, [sys.executable, "-c", "import sys; sys.exit(0)"])["exit_code"] == 0
    start = householder_runner.start_review(TASK_ID)

    with pytest.raises(ValueError, match="reviewer result must be ACCEPT"):
        householder_runner.finish_review(TASK_ID, "REQUEST_CHANGES", "PASS")

    result = householder_runner.finish_review(TASK_ID, "ACCEPT", "PASS")
    assert result["ledger_after"]["state"] == "review_green"
    assert result["reviewer_result"] == "ACCEPT"
    assert result["breaker_result"] == "PASS"
    assert result["frozen_staged_fingerprint"] == start["frozen_staged_fingerprint"]


def test_authorize_delivery_requires_review_green_and_valid_receipts(monkeypatch, tmp_path):
    repo, _ = make_repo(tmp_path)
    parent = tmp_path / "external-worktrees"
    create_campaign(monkeypatch, repo, parent)
    worktree = parent / TASK_ID
    bind(monkeypatch, repo)
    monkeypatch.chdir(worktree)
    (worktree / "seed.txt").write_text("delivery\n", encoding="utf-8")
    git(worktree, "add", "seed.txt")
    householder_runner.start_edit(TASK_ID, "primary")
    assert householder_runner.run_focused(TASK_ID, [sys.executable, "-c", "import sys; sys.exit(0)"])["exit_code"] == 0
    start = householder_runner.start_review(TASK_ID)
    finish = householder_runner.finish_review(TASK_ID, "ACCEPT", "PASS")
    assert finish["ledger_after"]["state"] == "review_green"

    with pytest.raises(ValueError, match="focused_receipt receipt is required"):
        householder_runner.authorize_delivery(TASK_ID)

    payload = read_record(repo)
    payload.update(
        {
            "focused_receipt": {
                "task_id": TASK_ID,
                "frozen_staged_fingerprint": start["frozen_staged_fingerprint"],
                "status": "passed",
            },
            "full_gate_receipt": {
                "task_id": TASK_ID,
                "frozen_staged_fingerprint": start["frozen_staged_fingerprint"],
                "status": "passed",
            },
            "review_receipt": {
                "task_id": TASK_ID,
                "frozen_staged_fingerprint": start["frozen_staged_fingerprint"],
                "status": "review_green",
                "reviewer_result": "ACCEPT",
                "breaker_result": "PASS",
            },
            "runtime_evidence_receipt": {
                "task_id": TASK_ID,
                "frozen_staged_fingerprint": start["frozen_staged_fingerprint"],
                "status": "passed",
            },
            "readiness_receipt": {
                "task_id": TASK_ID,
                "frozen_staged_fingerprint": start["frozen_staged_fingerprint"],
                "status": "passed",
            },
            "pre_commit_receipt": {
                "task_id": TASK_ID,
                "frozen_staged_fingerprint": start["frozen_staged_fingerprint"],
                "status": "passed",
            },
        }
    )
    write_record(repo, payload)

    report = householder_runner.authorize_delivery(TASK_ID)
    assert report["allowed"] is True
    assert report["frozen_staged_fingerprint"] == start["frozen_staged_fingerprint"]


def test_cleanup_rejects_dirty_or_unpushed_and_removes_recorded_worktree(monkeypatch, tmp_path):
    repo, _ = make_repo(tmp_path)
    parent = tmp_path / "external-worktrees"
    create_campaign(monkeypatch, repo, parent)
    worktree = parent / TASK_ID
    bind(monkeypatch, repo)
    monkeypatch.chdir(worktree)

    (worktree / "seed.txt").write_text("dirty\n", encoding="utf-8")
    with pytest.raises(ValueError, match="dirty"):
        householder_runner.cleanup(TASK_ID)

    git(worktree, "add", "seed.txt")
    git(worktree, "commit", "-m", "unpublished")
    with pytest.raises(ValueError, match="unpushed"):
        householder_runner.cleanup(TASK_ID)

    git(worktree, "reset", "--hard", "HEAD~1")
    assert householder_runner.cleanup(TASK_ID)["removed_worktree"] == str(worktree)
    assert not worktree.exists()


def test_main_remains_unchanged(monkeypatch, tmp_path):
    repo, _ = make_repo(tmp_path)
    parent = tmp_path / "external-worktrees"
    head = git(repo, "rev-parse", "HEAD").stdout.strip()
    origin_head = git(repo, "rev-parse", "origin/main").stdout.strip()
    create_campaign(monkeypatch, repo, parent)
    worktree = parent / TASK_ID
    bind(monkeypatch, repo)
    monkeypatch.chdir(worktree)
    householder_runner.start_edit(TASK_ID, "primary")
    householder_runner.run_focused(TASK_ID, [sys.executable, "-c", "import sys; sys.exit(0)"])

    assert git(repo, "rev-parse", "HEAD").stdout.strip() == head
    assert git(repo, "rev-parse", "origin/main").stdout.strip() == origin_head
    assert git(repo, "status", "--short", "--untracked-files=no").stdout.strip() == ""


def test_valid_campaign_reaches_completed_focused_run(monkeypatch, tmp_path):
    repo, _ = make_repo(tmp_path)
    parent = tmp_path / "external-worktrees"
    create_campaign(monkeypatch, repo, parent)
    worktree = parent / TASK_ID
    bind(monkeypatch, repo)
    monkeypatch.chdir(worktree)

    start = householder_runner.start_edit(TASK_ID, "primary")
    assert start["ledger_after"]["state"] == "editing"
    result = householder_runner.run_focused(TASK_ID, [sys.executable, "-c", "import sys; sys.exit(0)"])
    assert result["exit_code"] == 0
    assert result["ledger_after"]["state"] == "editing"
