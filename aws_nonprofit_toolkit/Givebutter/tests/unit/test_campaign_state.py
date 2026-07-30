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
    data = dict(AUTH)
    data.update(updates)
    return campaign_state.freeze(data)


def git_in(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=path, capture_output=True, text=True, check=True)


def build_real_copy_repo(tmp_path: Path, source_rel: str, dest_rel: str) -> Path:
    repo = tmp_path / "git-copy-repo"
    repo.mkdir()
    git_in(repo, "init")
    git_in(repo, "config", "user.email", "test@example.com")
    git_in(repo, "config", "user.name", "Test User")

    source_path = repo / source_rel
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(f"seeded source for {source_rel}\n", encoding="utf-8")

    auth_path = repo / campaign_state.AUTHORIZATION_PATH
    auth_path.parent.mkdir(parents=True, exist_ok=True)
    auth_path.write_text(AUTH_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    git_in(repo, "add", source_rel)
    git_in(repo, "commit", "-m", "seed authorized copy source")

    dest_path = repo / dest_rel
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, dest_path)
    git_in(repo, "add", dest_rel)
    return repo


def test_load_authorization_is_frozen():
    auth = campaign_state.load_authorization()
    with pytest.raises(TypeError):
        auth["task_id"] = "changed"
    assert isinstance(auth["authorized_implementation_files"], tuple)


@pytest.mark.parametrize(
    "setup, expected",
    [
        (lambda m, t: m.setattr(campaign_state, "auth_file", lambda: t / "missing.json"), "missing"),
        (lambda m, t: (m.setattr(campaign_state, "auth_file", lambda: (t / "auth.json")), (t / "auth.json").write_text('{"task_id":"x","campaign_id":"x"}', encoding="utf-8"), m.setattr(campaign_state, "sha256_file", lambda _: "ok"), m.setattr(campaign_state, "run_git", lambda *a, **k: git_result("b0fb9a635df72d737127ba40501594b9ad3dafd9" if a[0][0] == "hash-object" else "", 0))), "task ID"),
        (lambda m, t: (m.setattr(campaign_state, "auth_file", lambda: (t / "auth.json")), (t / "auth.json").write_text(AUTH_PATH.read_text(encoding="utf-8"), encoding="utf-8"), m.setattr(campaign_state, "sha256_file", lambda _: "wrong"), m.setattr(campaign_state, "run_git", lambda *a, **k: git_result("b0fb9a635df72d737127ba40501594b9ad3dafd9" if a[0][0] == "hash-object" else "", 0))), "SHA-256"),
        (lambda m, t: (m.setattr(campaign_state, "sha256_file", lambda _: "46f614cc82df0e15afecd4d878abfdc99971c137eea3c3a99fa6f0b53013ed3c"), m.setattr(campaign_state, "run_git", lambda args, binary=False: git_result("", 1) if args[:4] == ["merge-base", "--is-ancestor", "faa6d57ae333b4c2f6d2ba6067d0d48e95c466d3", "HEAD"] else git_result("b0fb9a635df72d737127ba40501594b9ad3dafd9", 0))), "ancestor"),
    ],
)
def test_load_authorization_blocks_identity_problems(monkeypatch, tmp_path, setup, expected):
    setup(monkeypatch, tmp_path)
    with pytest.raises(ValueError) as exc:
        campaign_state.load_authorization()
    assert expected in str(exc.value)


def test_collect_scope_report_accepts_authorized_scope_and_prints_budget_summary(monkeypatch, capsys):
    entries = [
        ("R100", "Givebutter/scripts/ci/runtime_evidence.py", "Givebutter/scripts/ci/pre_commit_gate.py"),
        ("C080", "Givebutter/tests/unit/test_campaign_state.py", "Givebutter/tests/unit/test_pre_commit_gate.py"),
        ("M", "Givebutter/scripts/ci/campaign_state.py", None),
        ("M", "Givebutter/tests/unit/test_campaign_state.py", None),
    ]
    monkeypatch.setattr(campaign_state, "load_authorization", lambda: AUTH)
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
                ("hash-object", str(campaign_state.auth_file())): (0, "b0fb9a635df72d737127ba40501594b9ad3dafd9"),
                ("merge-base", "--is-ancestor", "faa6d57ae333b4c2f6d2ba6067d0d48e95c466d3", "HEAD"): (0, ""),
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
    ("source_rel", "dest_rel", "bucket"),
    [
        ("Givebutter/scripts/ci/pre_commit_gate.py", "Givebutter/scripts/ci/runtime_evidence.py", "implementation"),
        ("Givebutter/tests/unit/test_pre_commit_gate.py", "Givebutter/tests/unit/test_campaign_state.py", "test"),
    ],
)
def test_collect_scope_report_detects_real_copy_from_unchanged_authorized_source(monkeypatch, tmp_path, source_rel, dest_rel, bucket):
    repo = build_real_copy_repo(tmp_path, source_rel, dest_rel)
    monkeypatch.setattr(campaign_state, "repo_root", lambda: repo)
    monkeypatch.setattr(campaign_state, "load_authorization", lambda: AUTH)

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
    monkeypatch.setattr(campaign_state, "load_authorization", lambda: AUTH)
    entries = [(status, dst, src)]
    monkeypatch.setattr(
        campaign_state,
        "run_git",
        fake_git(
            {
                ("diff", "--cached", "--name-status", "--find-renames", "--find-copies", "--find-copies-harder", "--diff-filter=ACDMRT"): (
                    0,
                    "\n".join(f"{entry_status}\t{entry_dst}\t{entry_src}" for entry_status, entry_dst, entry_src in entries),
                ),
                ("diff", "--cached", "--numstat", "--find-renames", "--find-copies", "--find-copies-harder", "--diff-filter=ACDMRT"): (
                    0,
                    f"{expected_lines['inserted']}\t{expected_lines['deleted']}\t{dst} => {src}",
                ),
                ("rev-parse", "HEAD"): (0, "deadbeef"),
                ("diff", "--cached", "--binary", "--full-index", "--no-ext-diff", "HEAD"): (0, b"binary-diff"),
                ("hash-object", str(campaign_state.auth_file())): (0, "b0fb9a635df72d737127ba40501594b9ad3dafd9"),
                ("merge-base", "--is-ancestor", "faa6d57ae333b4c2f6d2ba6067d0d48e95c466d3", "HEAD"): (0, ""),
            }
        ),
    )
    report = campaign_state.collect_scope_report(campaign_state.TASK_ID)
    assert report["status_counts"][field] == 1
    if field == "renames":
        assert report["implementation_files"] == expected_files or report["test_files"] == expected_files
        assert report["implementation_line_budget"] == expected_lines or report["test_line_budget"] == expected_lines
    else:
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
    monkeypatch.setattr(campaign_state, "load_authorization", lambda: AUTH)
    monkeypatch.setattr(
        campaign_state,
        "run_git",
        fake_git(
            {
                ("diff", "--cached", "--name-status", "--find-renames", "--find-copies", "--find-copies-harder", "--diff-filter=ACDMRT"): (0, f"{status}\t{dst}\t{src}"),
                ("diff", "--cached", "--numstat", "--find-renames", "--find-copies", "--find-copies-harder", "--diff-filter=ACDMRT"): (0, "1\t1\t" + f"{dst} => {src}"),
                ("rev-parse", "HEAD"): (0, "deadbeef"),
                ("diff", "--cached", "--binary", "--full-index", "--no-ext-diff", "HEAD"): (0, b"binary-diff"),
                ("hash-object", str(campaign_state.auth_file())): (0, "b0fb9a635df72d737127ba40501594b9ad3dafd9"),
                ("merge-base", "--is-ancestor", "faa6d57ae333b4c2f6d2ba6067d0d48e95c466d3", "HEAD"): (0, ""),
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
            return git_result("\n".join(
                f"{status}\t{dst}\t{src}" if src else f"{status}\t{dst}" for status, dst, src in entries
            ))
        if key == ("diff", "--cached", "--numstat", "--find-renames", "--find-copies", "--find-copies-harder", "--diff-filter=ACDMRT"):
            if any(v[0] == "-" or v[1] == "-" for v in counts.values()):
                return git_result("-\t-\tGivebutter/tests/unit/test_campaign_state.py")
            return git_result("\n".join(f"{a}\t{d}\t{path}" for path, (a, d) in counts.items()))
        if key == ("rev-parse", "HEAD"):
            return git_result("deadbeef")
        if key == ("diff", "--cached", "--binary", "--full-index", "--no-ext-diff", "HEAD"):
            return git_result(b"binary-diff", 0)
        if key == ("hash-object", str(campaign_state.auth_file())):
            return git_result("b0fb9a635df72d737127ba40501594b9ad3dafd9")
        if key == ("merge-base", "--is-ancestor", "faa6d57ae333b4c2f6d2ba6067d0d48e95c466d3", "HEAD"):
            return git_result("")
        raise AssertionError(key)

    monkeypatch.setattr(campaign_state, "load_authorization", lambda: auth_copy())
    monkeypatch.setattr(campaign_state, "run_git", runner)
    with pytest.raises(ValueError) as exc:
        campaign_state.collect_scope_report(campaign_state.TASK_ID)
    assert expected in str(exc.value)
