from __future__ import annotations

import json
import multiprocessing as mp
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts/ci"))

import householder_state


TASK_ID = householder_state.TASK_ID


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=check)


def new_repo(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    app = repo / "aws_nonprofit_toolkit"
    app.mkdir(parents=True)
    git(repo, "init")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test User")
    seed = app / "seed.txt"
    seed.write_text("seed\n", encoding="utf-8")
    git(repo, "add", "aws_nonprofit_toolkit/seed.txt")
    git(repo, "commit", "-m", "seed")
    return repo, app


def bind(monkeypatch, app: Path) -> None:
    monkeypatch.setattr(householder_state, "repo_root", lambda: app)


def state_path() -> Path:
    return householder_state.state_path()


def load_state() -> dict[str, object]:
    return json.loads(state_path().read_text(encoding="utf-8"))


def make_state(*, state: str = "idle", **overrides) -> dict[str, object]:
    record: dict[str, object] = {
        "schema_version": 1,
        "task_id": TASK_ID,
        "state": state,
        "created_at": "2026-07-31T00:00:00Z",
        "updated_at": "2026-07-31T00:00:00Z",
        "primary_allowed": 1,
        "primary_used": 0,
        "implementation_repair_allowed": 1,
        "implementation_repair_used": 0,
        "test_harness_repair_allowed": 1,
        "test_harness_repair_used": 0,
        "review_repair_allowed": 1,
        "review_repair_used": 0,
        "focused_runs_allowed": 4,
        "focused_runs_used": 0,
        "review_cycles_allowed": 2,
        "review_cycles_used": 0,
    }
    record.update(overrides)
    record["state_digest"] = householder_state._digest(record)
    return record


def write_state(record: dict[str, object]) -> None:
    state_path().parent.mkdir(parents=True, exist_ok=True)
    state_path().write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def stage_extra(repo: Path, app: Path, rel: str) -> None:
    p = app / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("x\n", encoding="utf-8")
    git(repo, "add", str(Path(app.name) / rel))


def lock_holder(lock_path: str, ready: mp.Event, release: mp.Event) -> None:
    import fcntl

    with open(lock_path, "a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        ready.set()
        release.wait(10)
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def worker_status(app: str, q: mp.Queue) -> None:
    import householder_state as hs

    hs.repo_root = lambda: Path(app)
    try:
        q.put(("ok", hs.status(TASK_ID)))
    except Exception as exc:  # pragma: no cover - child process transport
        q.put(("err", type(exc).__name__, str(exc)))


def test_initialize_succeeds_and_duplicate_fails(monkeypatch, tmp_path):
    _, app = new_repo(tmp_path)
    bind(monkeypatch, app)
    state = householder_state.initialize(TASK_ID)
    assert state["schema_version"] == 1
    assert state["task_id"] == TASK_ID
    assert state["state"] == "idle"
    with pytest.raises(ValueError, match="already exists"):
        householder_state.initialize(TASK_ID)


def test_missing_state_and_malformed_json_fail(monkeypatch, tmp_path):
    _, app = new_repo(tmp_path)
    bind(monkeypatch, app)
    with pytest.raises(ValueError, match="missing"):
        householder_state.load(TASK_ID)
    state_path().parent.mkdir(parents=True, exist_ok=True)
    state_path().write_text("{not-json", encoding="utf-8")
    with pytest.raises(ValueError, match="malformed"):
        householder_state.load(TASK_ID)


def test_unsupported_schema_and_negative_counter_fail(monkeypatch, tmp_path):
    _, app = new_repo(tmp_path)
    bind(monkeypatch, app)
    householder_state.initialize(TASK_ID)
    state = load_state()
    state["schema_version"] = 99
    state_path().write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported schema"):
        householder_state.status(TASK_ID)
    state["schema_version"] = 1
    state["primary_used"] = -1
    state_path().write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="non-negative integer"):
        householder_state.status(TASK_ID)


def test_tampered_state_digest_is_rejected(monkeypatch, tmp_path):
    _, app = new_repo(tmp_path)
    bind(monkeypatch, app)
    householder_state.initialize(TASK_ID)
    state = load_state()
    state["primary_used"] = 1
    write_state(state)
    with pytest.raises(ValueError, match="state digest mismatch"):
        householder_state.load(TASK_ID)


def test_atomic_write_leaves_no_partial_file(monkeypatch, tmp_path):
    _, app = new_repo(tmp_path)
    bind(monkeypatch, app)
    monkeypatch.setattr(householder_state.os, "replace", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("boom")))
    with pytest.raises(OSError):
        householder_state.initialize(TASK_ID)
    artifacts = app / "Givebutter/.artifacts"
    assert not any(p.suffix == ".tmp" for p in artifacts.glob("*"))
    assert not state_path().exists()


def test_lock_prevents_concurrent_mutation(monkeypatch, tmp_path):
    _, app = new_repo(tmp_path)
    bind(monkeypatch, app)
    householder_state.initialize(TASK_ID)
    ctx = mp.get_context("spawn")
    ready = ctx.Event()
    release = ctx.Event()
    q = ctx.Queue()
    holder = ctx.Process(target=lock_holder, args=(str(householder_state.lock_path()), ready, release))
    holder.start()
    assert ready.wait(5)
    worker = ctx.Process(target=worker_status, args=(str(app), q))
    worker.start()
    time.sleep(0.3)
    assert worker.is_alive()
    release.set()
    worker.join(5)
    holder.join(5)
    assert q.get(timeout=5)[0] == "ok"


def test_reset_requires_authorization_and_archives_prior_state(monkeypatch, tmp_path):
    _, app = new_repo(tmp_path)
    bind(monkeypatch, app)
    householder_state.initialize(TASK_ID)
    with pytest.raises(ValueError, match="authorized reset required"):
        householder_state.reset(TASK_ID, False)
    householder_state.reset(TASK_ID, True)
    archives = sorted((app / "Givebutter/.artifacts").glob("householder-task-state.*.archive.json"))
    assert archives


def test_authorized_reset_can_archive_terminal_state(monkeypatch, tmp_path):
    _, app = new_repo(tmp_path)
    bind(monkeypatch, app)
    write_state(make_state(state="terminal"))
    with pytest.raises(ValueError, match="terminal state"):
        householder_state.load(TASK_ID)
    with pytest.raises(ValueError, match="terminal state"):
        householder_state.status(TASK_ID)
    householder_state.reset(TASK_ID, True)
    archives = sorted((app / "Givebutter/.artifacts").glob("householder-task-state.*.archive.json"))
    assert len(archives) == 1
    assert json.loads(archives[0].read_text(encoding="utf-8"))["state"] == "terminal"
    assert householder_state.load(TASK_ID)["state"] == "idle"


def test_reset_wrong_task_id_fails(monkeypatch, tmp_path):
    _, app = new_repo(tmp_path)
    bind(monkeypatch, app)
    householder_state.initialize(TASK_ID)
    with pytest.raises(ValueError, match="task_id mismatch"):
        householder_state.reset("wrong", True)


def test_reset_uses_distinct_archive_names_within_same_second(monkeypatch, tmp_path):
    _, app = new_repo(tmp_path)
    bind(monkeypatch, app)
    householder_state.initialize(TASK_ID)
    fixed_now = datetime(2026, 7, 31, 12, 34, 56, tzinfo=timezone.utc)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    monkeypatch.setattr(householder_state, "datetime", FixedDateTime)
    householder_state.reset(TASK_ID, True)
    householder_state.reset(TASK_ID, True)
    archives = sorted((app / "Givebutter/.artifacts").glob("householder-task-state.*.archive.json"))
    assert len(archives) == 2
    assert len({archive.name for archive in archives}) == 2


def test_status_reports_schema_task_state_and_counters(monkeypatch, tmp_path, capsys):
    _, app = new_repo(tmp_path)
    bind(monkeypatch, app)
    householder_state.initialize(TASK_ID)
    report = householder_state.status(TASK_ID)
    captured = capsys.readouterr().out
    assert report["schema_version"] == 1
    assert report["task_id"] == TASK_ID
    assert report["state"] == "idle"
    assert report["counters"]["focused_runs_allowed"] == 4
    assert '"task_id": "HOUSEHOLDER-STATE-STORE-20260730"' in captured
