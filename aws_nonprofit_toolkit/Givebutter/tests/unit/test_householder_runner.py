from __future__ import annotations

import json
import subprocess
import sys
import shutil
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "ci"))

import householder_runner  # noqa: E402


TASK_ID = "HOUSEHOLDER-WORKTREE-RUNNER-CORE-20260731"


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=check)


def make_repo(tmp_path: Path) -> tuple[Path, Path]:
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
    target_householder_state = repo / "Givebutter/scripts/ci/householder_state.py"
    target_householder_state.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_householder_state, target_householder_state)
    git(repo, "add", "seed.txt")
    git(repo, "add", "Givebutter/scripts/ci/householder_state.py")
    git(repo, "commit", "-m", "seed")
    git(repo, "remote", "add", "origin", str(origin))
    git(repo, "push", "-u", "origin", "main")
    git(repo, "fetch", "origin", "main")
    return repo, origin


def bind(monkeypatch, repo: Path) -> None:
    monkeypatch.setattr(householder_runner, "repo_root", lambda: repo)


def record_path(repo: Path, task_id: str = TASK_ID) -> Path:
    return repo / "Givebutter/.artifacts" / f"householder-runner.{task_id}.json"


def read_record(repo: Path, task_id: str = TASK_ID) -> dict[str, object]:
    return json.loads(record_path(repo, task_id).read_text(encoding="utf-8"))


def write_record(repo: Path, payload: dict[str, object], task_id: str = TASK_ID) -> None:
    record_path(repo, task_id).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def create_campaign(monkeypatch, repo: Path, parent: Path, task_id: str = TASK_ID) -> dict[str, object]:
    monkeypatch.chdir(repo)
    bind(monkeypatch, repo)
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
