from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts/ci"))

import campaign_state

AUTH_PATH = campaign_state.auth_file()
AUTH = campaign_state.freeze(json.loads(AUTH_PATH.read_text(encoding="utf-8")))
ALT_TASK_ID = "MACHINE-ENFORCED-CAMPAIGN-STATE-ALT-20260730"


def git_result(stdout="", returncode=0):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr="")


def fake_git(mapping):
    def runner(args, binary=False):
        rc, out = mapping[tuple(args)]
        if binary and isinstance(out, str):
            out = out.encode("utf-8")
        return git_result(out, rc)

    return runner


def auth_copy(**updates):
    data = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
    data.update(updates)
    return campaign_state.freeze(data)


def git_in(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=path, capture_output=True, text=True, check=True)


def nested_repo_paths(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "git-copy-repo"
    app = repo / "aws_nonprofit_toolkit"
    app.mkdir(parents=True)
    git_in(repo, "init")
    git_in(repo, "config", "user.email", "test@example.com")
    git_in(repo, "config", "user.name", "Test User")
    return repo, app


def write_authorization(app_root: Path, task_id: str, auth_data) -> Path:
    auth_path = app_root / campaign_state.authorization_path(task_id)
    auth_path.parent.mkdir(parents=True, exist_ok=True)
    auth_path.write_text(json.dumps(auth_data, default=lambda value: dict(value) if isinstance(value, dict) or hasattr(value, "items") else list(value), indent=2) + "\n", encoding="utf-8")
    return auth_path


def git_add_commit(repo: Path, app_root: Path, *rel_paths: str) -> None:
    git_in(repo, "add", *(str(Path(app_root.name) / rel_path) for rel_path in rel_paths))
    git_in(repo, "commit", "-m", "seed authorized repo")


def build_real_copy_repo(tmp_path: Path, source_rel: str, dest_rel: str) -> Path:
    repo, app = nested_repo_paths(tmp_path)
    write_authorization(app, campaign_state.TASK_ID, AUTH)

    source_path = app / source_rel
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(f"seeded source for {source_rel}\n", encoding="utf-8")
    git_add_commit(repo, app, str(campaign_state.authorization_path(campaign_state.TASK_ID)), source_rel)

    dest_path = app / dest_rel
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, dest_path)
    git_in(repo, "add", str(Path(app.name) / dest_rel))
    return app


def test_load_authorization_is_frozen():
    auth = campaign_state.load_authorization()
    with pytest.raises(TypeError):
        auth["task_id"] = "changed"
    assert isinstance(auth["authorized_implementation_files"], tuple)


def test_load_authorization_accepts_second_committed_authorization(tmp_path, monkeypatch):
    repo, app = nested_repo_paths(tmp_path)
    alt_auth = auth_copy(task_id=ALT_TASK_ID, campaign_id=ALT_TASK_ID)
    write_authorization(app, ALT_TASK_ID, alt_auth)
    git_add_commit(repo, app, str(campaign_state.authorization_path(ALT_TASK_ID)))
    monkeypatch.setattr(campaign_state, "repo_root", lambda: app)

    loaded = campaign_state.load_authorization(ALT_TASK_ID)
    assert loaded["task_id"] == ALT_TASK_ID
    assert loaded["campaign_id"] == ALT_TASK_ID
    assert loaded["implementation_line_budget"] == AUTH["implementation_line_budget"]


def test_load_authorization_rejects_untracked_authorization(tmp_path, monkeypatch):
    repo, app = nested_repo_paths(tmp_path)
    write_authorization(app, campaign_state.TASK_ID, AUTH)
    monkeypatch.setattr(campaign_state, "repo_root", lambda: app)

    with pytest.raises(ValueError) as exc:
        campaign_state.load_authorization()
    assert "must exist in HEAD" in str(exc.value)


@pytest.mark.parametrize(
    "mutator, expected",
    [
        (
            lambda repo, app, auth_path: auth_path.write_text(
                auth_path.read_text(encoding="utf-8").replace(
                    "commit-readiness validation against this frozen authorization.",
                    "commit-readiness validation against this frozen authorization (mutated).",
                ),
                encoding="utf-8",
            ),
            "working tree content mismatch",
        ),
        (
            lambda repo, app, auth_path: (
                auth_path.write_text(
                    auth_path.read_text(encoding="utf-8").replace(
                        "commit-readiness validation against this frozen authorization.",
                        "commit-readiness validation against this frozen authorization (staged).",
                    ),
                    encoding="utf-8",
                ),
                git_in(repo, "add", str(Path(app.name) / campaign_state.authorization_path(campaign_state.TASK_ID))),
            ),
            "staged content mismatch",
        ),
        (
            lambda repo, app, auth_path: git_in(
                repo,
                "rm",
                "--cached",
                str(Path(app.name) / campaign_state.authorization_path(campaign_state.TASK_ID)),
            ),
            "must be tracked",
        ),
    ],
)
def test_load_authorization_rejects_committed_mutations(tmp_path, monkeypatch, mutator, expected):
    repo, app = nested_repo_paths(tmp_path)
    auth_path = write_authorization(app, campaign_state.TASK_ID, AUTH)
    git_add_commit(repo, app, str(campaign_state.authorization_path(campaign_state.TASK_ID)))
    monkeypatch.setattr(campaign_state, "repo_root", lambda: app)

    mutator(repo, app, auth_path)
    with pytest.raises(ValueError) as exc:
        campaign_state.load_authorization()
    assert expected in str(exc.value)


def test_load_authorization_rejects_task_id_path_mismatch(tmp_path, monkeypatch):
    repo, app = nested_repo_paths(tmp_path)
    mismatched = auth_copy(task_id=campaign_state.TASK_ID, campaign_id=campaign_state.TASK_ID)
    write_authorization(app, ALT_TASK_ID, mismatched)
    git_add_commit(repo, app, str(campaign_state.authorization_path(ALT_TASK_ID)))
    monkeypatch.setattr(campaign_state, "repo_root", lambda: app)

    with pytest.raises(ValueError) as exc:
        campaign_state.load_authorization(ALT_TASK_ID)
    assert "task ID mismatch" in str(exc.value)


def test_load_authorization_rejects_introduction_commit_not_in_ancestry(tmp_path, monkeypatch):
    repo, app = nested_repo_paths(tmp_path)
    write_authorization(app, campaign_state.TASK_ID, AUTH)
    git_add_commit(repo, app, str(campaign_state.authorization_path(campaign_state.TASK_ID)))
    monkeypatch.setattr(campaign_state, "repo_root", lambda: app)
    monkeypatch.setattr(campaign_state, "_head_auth_intro_commit", lambda pathspec: "deadbeef")
    real_run_git = campaign_state.run_git

    def runner(args, binary=False):
        if tuple(args) == ("merge-base", "--is-ancestor", "deadbeef", "HEAD"):
            return git_result("", 1)
        return real_run_git(args, binary=binary)

    monkeypatch.setattr(campaign_state, "run_git", runner)

    with pytest.raises(ValueError) as exc:
        campaign_state.load_authorization()
    assert "ancestor of HEAD" in str(exc.value)


@pytest.mark.parametrize(
    ("source_rel", "dest_rel", "bucket"),
    [
        ("Givebutter/scripts/ci/pre_commit_gate.py", "Givebutter/scripts/ci/runtime_evidence.py", "implementation"),
        ("Givebutter/tests/unit/test_pre_commit_gate.py", "Givebutter/tests/unit/test_campaign_state.py", "test"),
    ],
)
def test_collect_scope_report_detects_real_copy_from_unchanged_authorized_source(monkeypatch, tmp_path, source_rel, dest_rel, bucket):
    app = build_real_copy_repo(tmp_path, source_rel, dest_rel)
    monkeypatch.setattr(campaign_state, "repo_root", lambda: app)

    detection = campaign_state.run_git([
        "diff",
        "--cached",
        "--name-status",
        "--find-renames",
        "--find-copies",
        "--find-copies-harder",
        "--diff-filter=ACDMRT",
    ])
    assert detection.returncode == 0
    assert detection.stdout.startswith("C")
    assert dest_rel in detection.stdout
    assert source_rel in detection.stdout

    report = campaign_state.collect_scope_report(campaign_state.TASK_ID)
    assert report["status_counts"]["copies"] == 1
    assert report["status_counts"]["additions"] == 0
    assert report[f"{bucket}_files"] == (dest_rel,)


def test_collect_scope_report_accepts_authorized_scope_and_prints_budget_summary(monkeypatch, capsys):
    monkeypatch.setattr(campaign_state, "load_authorization", lambda task_id=campaign_state.TASK_ID: AUTH)
    monkeypatch.setattr(campaign_state, "_authorization_facts", lambda task_id: {"sha256": campaign_state.sha256_file(AUTH_PATH), "git_blob": "b0fb9a635df72d737127ba40501594b9ad3dafd9", "introduction_commit": "faa6d57ae333b4c2f6d2ba6067d0d48e95c466d3"})
    monkeypatch.setattr(
        campaign_state,
        "run_git",
        fake_git(
            {
                ("diff", "--cached", "--name-status", "--find-renames", "--find-copies", "--find-copies-harder", "--diff-filter=ACDMRT"): (0, "\n".join([
                    "R100\tGivebutter/scripts/ci/runtime_evidence.py\tGivebutter/scripts/ci/pre_commit_gate.py",
                    "C080\tGivebutter/tests/unit/test_campaign_state.py\tGivebutter/tests/unit/test_pre_commit_gate.py",
                    "M\tGivebutter/scripts/ci/campaign_state.py",
                    "M\tGivebutter/tests/unit/test_campaign_state.py",
                ])),
                ("diff", "--cached", "--numstat", "--find-renames", "--find-copies", "--find-copies-harder", "--diff-filter=ACDMRT"): (0, "\n".join([
                    "11\t7\tGivebutter/scripts/ci/runtime_evidence.py => Givebutter/scripts/ci/pre_commit_gate.py",
                    "4\t2\tGivebutter/scripts/ci/campaign_state.py",
                    "3\t1\tGivebutter/tests/unit/test_campaign_state.py => Givebutter/tests/unit/test_pre_commit_gate.py",
                    "4\t2\tGivebutter/tests/unit/test_campaign_state.py",
                ])),
                ("rev-parse", "HEAD"): (0, "deadbeef"),
                ("diff", "--cached", "--binary", "--full-index", "--no-ext-diff", "HEAD"): (0, b"binary-diff"),
            }
        ),
    )
    report = campaign_state.collect_scope_report(campaign_state.TASK_ID)
    campaign_state.print_report(report)
    out = capsys.readouterr().out
    assert report["implementation_files"] == ("Givebutter/scripts/ci/campaign_state.py", "Givebutter/scripts/ci/pre_commit_gate.py")
    assert report["test_files"] == ("Givebutter/tests/unit/test_campaign_state.py", "Givebutter/tests/unit/test_pre_commit_gate.py")
    assert report["implementation_line_budget"] == {"inserted": 15, "deleted": 9, "actual": 24, "allowed": AUTH["implementation_line_budget"]}
    assert report["test_line_budget"] == {"inserted": 7, "deleted": 3, "actual": 10, "allowed": AUTH["test_line_budget"]}
    assert "remaining_file_budgets: implementation=" in out
    assert "counts: additions=0 modifications=2 renames=1 copies=1 deletions=0" in out
    assert "exports_uat" not in "".join(report["implementation_files"] + report["test_files"])


@pytest.mark.parametrize(
    ("status", "dst", "src", "expected_files", "expected_lines", "field"),
    [
        ("R100", "Givebutter/scripts/ci/runtime_evidence.py", "Givebutter/scripts/ci/campaign_state.py", ("Givebutter/scripts/ci/campaign_state.py",), {"inserted": 11, "deleted": 7, "actual": 18, "allowed": AUTH["implementation_line_budget"]}, "renames"),
        ("R095", "Givebutter/tests/unit/test_pre_commit_gate.py", "Givebutter/tests/unit/test_campaign_state.py", ("Givebutter/tests/unit/test_campaign_state.py",), {"inserted": 3, "deleted": 1, "actual": 4, "allowed": AUTH["test_line_budget"]}, "renames"),
        ("C100", "Givebutter/scripts/ci/runtime_evidence.py", "Givebutter/scripts/ci/pre_commit_gate.py", ("Givebutter/scripts/ci/pre_commit_gate.py",), {"inserted": 11, "deleted": 7, "actual": 18, "allowed": AUTH["implementation_line_budget"]}, "copies"),
        ("C080", "Givebutter/tests/unit/test_campaign_state.py", "Givebutter/tests/unit/test_pre_commit_gate.py", ("Givebutter/tests/unit/test_pre_commit_gate.py",), {"inserted": 3, "deleted": 1, "actual": 4, "allowed": AUTH["test_line_budget"]}, "copies"),
    ],
)
def test_collect_scope_report_counts_prefixed_rename_and_copy_statuses(monkeypatch, status, dst, src, expected_files, expected_lines, field):
    monkeypatch.setattr(campaign_state, "load_authorization", lambda task_id=campaign_state.TASK_ID: AUTH)
    monkeypatch.setattr(campaign_state, "_authorization_facts", lambda task_id: {"sha256": campaign_state.sha256_file(AUTH_PATH), "git_blob": "b0fb9a635df72d737127ba40501594b9ad3dafd9", "introduction_commit": "faa6d57ae333b4c2f6d2ba6067d0d48e95c466d3"})
    monkeypatch.setattr(
        campaign_state,
        "run_git",
        fake_git(
            {
                ("diff", "--cached", "--name-status", "--find-renames", "--find-copies", "--find-copies-harder", "--diff-filter=ACDMRT"): (0, f"{status}\t{dst}\t{src}"),
                ("diff", "--cached", "--numstat", "--find-renames", "--find-copies", "--find-copies-harder", "--diff-filter=ACDMRT"): (0, f"{expected_lines['inserted']}\t{expected_lines['deleted']}\t{dst} => {src}"),
                ("rev-parse", "HEAD"): (0, "deadbeef"),
                ("diff", "--cached", "--binary", "--full-index", "--no-ext-diff", "HEAD"): (0, b"binary-diff"),
            }
        ),
    )
    report = campaign_state.collect_scope_report(campaign_state.TASK_ID)
    assert report["status_counts"][field] == 1
    assert report["implementation_files"] == expected_files or report["test_files"] == expected_files
    assert report["implementation_line_budget"] == expected_lines or report["test_line_budget"] == expected_lines


@pytest.mark.parametrize(
    "status,dst,src,expected_error",
    [
        ("R100", "Givebutter/scripts/ci/not_allowed.py", "Givebutter/scripts/ci/campaign_state.py", "rename/copy must stay within authorized scope"),
        ("R095", "Givebutter/scripts/ci/campaign_state.py", "Givebutter/scripts/ci/not_allowed.py", "rename/copy must stay within authorized scope"),
        ("C100", "Givebutter/scripts/ci/not_allowed.py", "Givebutter/scripts/ci/pre_commit_gate.py", "rename/copy must stay within authorized scope"),
        ("C080", "Givebutter/tests/unit/test_campaign_state.py", "Givebutter/tests/unit/test_not_allowed.py", "rename/copy must stay within authorized scope"),
        ("R100", "Givebutter/tests/unit/test_campaign_state.py", "Givebutter/scripts/ci/campaign_state.py", "mixed-scope staged path"),
        ("C080", "Givebutter/scripts/ci/campaign_state.py", "Givebutter/tests/unit/test_campaign_state.py", "mixed-scope staged path"),
    ],
)
def test_collect_scope_report_blocks_cross_scope_rename_and_copy(monkeypatch, status, dst, src, expected_error):
    monkeypatch.setattr(campaign_state, "load_authorization", lambda task_id=campaign_state.TASK_ID: AUTH)
    monkeypatch.setattr(campaign_state, "_authorization_facts", lambda task_id: {"sha256": campaign_state.sha256_file(AUTH_PATH), "git_blob": "b0fb9a635df72d737127ba40501594b9ad3dafd9", "introduction_commit": "faa6d57ae333b4c2f6d2ba6067d0d48e95c466d3"})
    monkeypatch.setattr(
        campaign_state,
        "run_git",
        fake_git(
            {
                ("diff", "--cached", "--name-status", "--find-renames", "--find-copies", "--find-copies-harder", "--diff-filter=ACDMRT"): (0, f"{status}\t{dst}\t{src}"),
                ("diff", "--cached", "--numstat", "--find-renames", "--find-copies", "--find-copies-harder", "--diff-filter=ACDMRT"): (0, "1\t1\t" + f"{dst} => {src}"),
                ("rev-parse", "HEAD"): (0, "deadbeef"),
                ("diff", "--cached", "--binary", "--full-index", "--no-ext-diff", "HEAD"): (0, b"binary-diff"),
            }
        ),
    )
    with pytest.raises(ValueError) as exc:
        campaign_state.collect_scope_report(campaign_state.TASK_ID)
    assert expected_error in str(exc.value)


@pytest.mark.parametrize(
    "entries, counts, expected",
    [
        ([("M", "Givebutter/scripts/ci/not_allowed.py", None)], {"Givebutter/scripts/ci/not_allowed.py": (1, 0)}, "unauthorized staged path"),
        ([("M", "Givebutter/.claude/task-authorizations/MACHINE-ENFORCED-CAMPAIGN-STATE-20260730.json", None)], {campaign_state.normalize(str(campaign_state.AUTHORIZATION_PATH)): (1, 0)}, "authorization file may not be staged"),
        ([("M", "Givebutter/scripts/ci/campaign_state.py", None)], {"Givebutter/scripts/ci/campaign_state.py": (451, 0)}, "implementation line budget exceeded"),
        ([("M", "Givebutter/tests/unit/test_campaign_state.py", None)], {"Givebutter/tests/unit/test_campaign_state.py": (0, 551)}, "test line budget exceeded"),
        ([("M", "Givebutter/tests/unit/test_campaign_state.py", None)], {"Givebutter/tests/unit/test_campaign_state.py": ("-", 0)}, "binary or uncountable change staged"),
    ],
)
def test_collect_scope_report_blocks_invalid_scope(monkeypatch, entries, counts, expected):
    def runner(args, binary=False):
        key = tuple(args)
        if key == ("diff", "--cached", "--name-status", "--find-renames", "--find-copies", "--find-copies-harder", "--diff-filter=ACDMRT"):
            return git_result("\n".join(f"{status}\t{dst}\t{src}" if src else f"{status}\t{dst}" for status, dst, src in entries))
        if key == ("diff", "--cached", "--numstat", "--find-renames", "--find-copies", "--find-copies-harder", "--diff-filter=ACDMRT"):
            if any(v[0] == "-" or v[1] == "-" for v in counts.values()):
                return git_result("-\t-\tGivebutter/tests/unit/test_campaign_state.py")
            return git_result("\n".join(f"{a}\t{d}\t{path}" for path, (a, d) in counts.items()))
        if key == ("rev-parse", "HEAD"):
            return git_result("deadbeef")
        if key == ("diff", "--cached", "--binary", "--full-index", "--no-ext-diff", "HEAD"):
            return git_result(b"binary-diff", 0)
        raise AssertionError(key)

    monkeypatch.setattr(campaign_state, "load_authorization", lambda task_id=campaign_state.TASK_ID: auth_copy())
    monkeypatch.setattr(campaign_state, "_authorization_facts", lambda task_id: {"sha256": campaign_state.sha256_file(AUTH_PATH), "git_blob": "b0fb9a635df72d737127ba40501594b9ad3dafd9", "introduction_commit": "faa6d57ae333b4c2f6d2ba6067d0d48e95c466d3"})
    monkeypatch.setattr(campaign_state, "run_git", runner)
    with pytest.raises(ValueError) as exc:
        campaign_state.collect_scope_report(campaign_state.TASK_ID)
    assert expected in str(exc.value)
