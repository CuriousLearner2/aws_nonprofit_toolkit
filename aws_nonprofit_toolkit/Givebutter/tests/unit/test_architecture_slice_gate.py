from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts' / 'ci'))

import architecture_slice_gate  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_PATH = REPO_ROOT / 'scripts' / 'ci' / 'architecture_slice_gate.py'
GATE_BLOB_SHA = subprocess.check_output(['git', 'hash-object', str(GATE_PATH)], cwd=REPO_ROOT, text=True).strip()
TASK_ID = 'HOUSEHOLDER-ARCHITECTURE-SLICE-GATE-20260801'


def _run_git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    for key in (
        'GIT_INDEX_FILE',
        'GIT_DIR',
        'GIT_WORK_TREE',
        'GIT_COMMON_DIR',
        'GIT_OBJECT_DIRECTORY',
        'GIT_ALTERNATE_OBJECT_DIRECTORIES',
    ):
        env.pop(key, None)
    env.setdefault('GIT_AUTHOR_NAME', 'Codex')
    env.setdefault('GIT_AUTHOR_EMAIL', 'codex@example.com')
    env.setdefault('GIT_COMMITTER_NAME', 'Codex')
    env.setdefault('GIT_COMMITTER_EMAIL', 'codex@example.com')
    return subprocess.run(['git', *args], cwd=repo, capture_output=True, text=True, check=check, env=env)


def _init_repo(root: Path) -> Path:
    repo = root / 'repo'
    repo.mkdir()
    _run_git(repo, 'init')
    _run_git(repo, 'config', 'user.email', 'codex@example.com')
    _run_git(repo, 'config', 'user.name', 'Codex')
    return repo


def _write(repo: Path, rel: str, text: str) -> Path:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


def _write_binary(repo: Path, rel: str, data: bytes) -> Path:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _commit(repo: Path, message: str) -> None:
    _run_git(repo, 'add', '-A')
    _run_git(repo, 'commit', '-m', message)


def _canonical_sha(contract: dict) -> str:
    payload = json.dumps(contract, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


def _contract(**overrides: object) -> dict:
    contract = {
        'schema_version': 1,
        'task_id': TASK_ID,
        'baseline_ref': 'HEAD',
        'seam': 'editable_field_validation',
        'authorized_files': [
            'scripts/householder/validation_policy.py',
            'scripts/householder/new_validation_policy.py',
            'tests/unit/test_validation_policy.py',
        ],
        'allowed_new_production_files': [
            'scripts/householder/new_validation_policy.py',
        ],
        'production_changed_lines_max': 160,
        'test_changed_lines_max': 120,
        'forbidden_files': [
            'scripts/householder/forbidden.py',
        ],
        'forbidden_imports': ['os'],
        'forbidden_symbols': ['dangerous_call'],
        'required_test_commands': [
            'pytest -q tests/unit/test_validation_policy.py',
        ],
        'gate_blob_sha': GATE_BLOB_SHA,
    }
    contract.update(overrides)
    return contract


def _write_contract(repo: Path, contract: dict, *, name: str = 'contract.json', pretty: bool = True) -> tuple[Path, str]:
    path = repo.parent / name
    if pretty:
        text = json.dumps(contract, indent=2) + '\n'
    else:
        text = json.dumps(contract, separators=(',', ':'), sort_keys=False) + '\n'
    path.write_text(text, encoding='utf-8')
    return path, _canonical_sha(contract)


def _write_contract_text(repo: Path, text: str, *, name: str = 'contract.json') -> Path:
    path = repo.parent / name
    path.write_text(text, encoding='utf-8')
    return path


def _evaluate(repo: Path, contract_path: Path, contract_sha: str, *, gate_path: Path = GATE_PATH, cwd: Path | None = None) -> dict:
    return architecture_slice_gate.evaluate_contract(
        contract_path=contract_path,
        contract_sha=contract_sha,
        gate_path=gate_path,
        cwd=cwd or repo,
    )


def _run_cli(repo: Path, contract_path: Path, contract_sha: str, *, gate_path: Path = GATE_PATH) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(gate_path), '--contract', str(contract_path), '--contract-sha', contract_sha],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )


def _base_repo(tmp_path: Path) -> Path:
    repo = _init_repo(tmp_path)
    _write(repo, 'scripts/householder/validation_policy.py', 'def validate(value):\n    return value.strip()\n')
    _write(repo, 'tests/unit/test_validation_policy.py', 'def test_validate():\n    assert True\n')
    _commit(repo, 'baseline')
    return repo


def test_schema_and_required_fields_validation(tmp_path: Path) -> None:
    repo = _base_repo(tmp_path)
    contract = _contract()
    contract_path, contract_sha = _write_contract(repo, contract, pretty=False)

    mutated = dict(contract)
    mutated['schema_version'] = 2
    contract_path.write_text(json.dumps(mutated, indent=2) + '\n', encoding='utf-8')
    with pytest.raises(ValueError, match='unsupported schema_version'):
        _evaluate(repo, contract_path, contract_sha)

    missing = dict(contract)
    missing.pop('forbidden_symbols')
    missing_path, missing_sha = _write_contract(repo, missing, name='missing.json')
    with pytest.raises(ValueError, match='missing required fields'):
        _evaluate(repo, missing_path, missing_sha)


def test_contract_sha_is_normalized(tmp_path: Path) -> None:
    repo = _base_repo(tmp_path)
    _write(repo, 'scripts/householder/validation_policy.py', 'def validate(value):\n    return value.strip().lower()\n')
    contract = _contract()
    contract_path, contract_sha = _write_contract(repo, contract, pretty=False)

    result = _evaluate(repo, contract_path, contract_sha)

    assert result['pass'] is True
    assert result['contract_sha'] == contract_sha


def test_unknown_top_level_fields_are_rejected_in_sorted_order(tmp_path: Path) -> None:
    repo = _base_repo(tmp_path)
    _write(repo, 'scripts/householder/validation_policy.py', 'def validate(value):\n    return value.strip().lower()\n')
    contract = _contract()
    contract['zzz_extra'] = True
    contract['aaa_extra'] = False
    contract_path, contract_sha = _write_contract(repo, contract)

    with pytest.raises(ValueError, match=r'contract contains unknown fields: aaa_extra, zzz_extra'):
        _evaluate(repo, contract_path, contract_sha)


def test_duplicate_required_key_with_different_values_is_rejected(tmp_path: Path) -> None:
    repo = _base_repo(tmp_path)
    _write(repo, 'scripts/householder/validation_policy.py', 'def validate(value):\n    return value.strip().lower()\n')
    raw_text = f'''{{
  "schema_version": 1,
  "task_id": "{TASK_ID}",
  "baseline_ref": "HEAD",
  "seam": "editable_field_validation",
  "authorized_files": ["scripts/householder/validation_policy.py"],
  "allowed_new_production_files": [],
  "production_changed_lines_max": 160,
  "production_changed_lines_max": 161,
  "test_changed_lines_max": 120,
  "forbidden_files": [],
  "forbidden_imports": [],
  "forbidden_symbols": [],
  "required_test_commands": [],
  "gate_blob_sha": "{GATE_BLOB_SHA}"
}}
'''
    contract_path = _write_contract_text(repo, raw_text)
    expected_contract = _contract(production_changed_lines_max=161)
    contract_sha = _canonical_sha(expected_contract)

    with pytest.raises(ValueError, match='duplicate contract key: production_changed_lines_max'):
        _evaluate(repo, contract_path, contract_sha)


def test_duplicate_required_key_with_identical_values_is_rejected(tmp_path: Path) -> None:
    repo = _base_repo(tmp_path)
    _write(repo, 'scripts/householder/validation_policy.py', 'def validate(value):\n    return value.strip().lower()\n')
    raw_text = f'''{{
  "schema_version": 1,
  "task_id": "{TASK_ID}",
  "baseline_ref": "HEAD",
  "seam": "editable_field_validation",
  "authorized_files": ["scripts/householder/validation_policy.py"],
  "allowed_new_production_files": [],
  "production_changed_lines_max": 160,
  "production_changed_lines_max": 160,
  "test_changed_lines_max": 120,
  "forbidden_files": [],
  "forbidden_imports": [],
  "forbidden_symbols": [],
  "required_test_commands": [],
  "gate_blob_sha": "{GATE_BLOB_SHA}"
}}
'''
    contract_path = _write_contract_text(repo, raw_text)
    contract_sha = _canonical_sha(_contract())

    with pytest.raises(ValueError, match='duplicate contract key: production_changed_lines_max'):
        _evaluate(repo, contract_path, contract_sha)


def test_multiple_duplicate_keys_are_rejected(tmp_path: Path) -> None:
    repo = _base_repo(tmp_path)
    _write(repo, 'scripts/householder/validation_policy.py', 'def validate(value):\n    return value.strip().lower()\n')
    raw_text = f'''{{
  "schema_version": 1,
  "task_id": "{TASK_ID}",
  "baseline_ref": "HEAD",
  "seam": "editable_field_validation",
  "authorized_files": ["scripts/householder/validation_policy.py"],
  "allowed_new_production_files": [],
  "production_changed_lines_max": 160,
  "production_changed_lines_max": 161,
  "test_changed_lines_max": 120,
  "test_changed_lines_max": 121,
  "forbidden_files": [],
  "forbidden_imports": [],
  "forbidden_symbols": [],
  "required_test_commands": [],
  "gate_blob_sha": "{GATE_BLOB_SHA}"
}}
'''
    contract_path = _write_contract_text(repo, raw_text)
    contract_sha = _canonical_sha(_contract(production_changed_lines_max=161, test_changed_lines_max=121))

    with pytest.raises(ValueError, match='duplicate contract key: production_changed_lines_max'):
        _evaluate(repo, contract_path, contract_sha)


def test_nested_duplicate_key_is_rejected(tmp_path: Path) -> None:
    repo = _base_repo(tmp_path)
    _write(repo, 'scripts/householder/validation_policy.py', 'def validate(value):\n    return value.strip().lower()\n')
    raw_text = f'''{{
  "schema_version": 1,
  "task_id": "{TASK_ID}",
  "baseline_ref": "HEAD",
  "seam": "editable_field_validation",
  "authorized_files": ["scripts/householder/validation_policy.py"],
  "allowed_new_production_files": [],
  "production_changed_lines_max": 160,
  "test_changed_lines_max": 120,
  "forbidden_files": [],
  "forbidden_imports": [],
  "forbidden_symbols": [],
  "required_test_commands": [],
  "gate_blob_sha": "{GATE_BLOB_SHA}",
  "nested": {{"inner": 1, "inner": 2}}
}}
'''
    contract_path = _write_contract_text(repo, raw_text)
    contract_sha = _canonical_sha(_contract())

    with pytest.raises(ValueError, match='duplicate contract key: inner'):
        _evaluate(repo, contract_path, contract_sha)


def test_valid_reordered_contract_passing_control_and_digest_stable(tmp_path: Path) -> None:
    repo = _base_repo(tmp_path)
    _write(repo, 'scripts/householder/validation_policy.py', 'def validate(value):\n    return value.strip().lower()\n')
    contract = _contract()
    reordered = {
        'schema_version': contract['schema_version'],
        'task_id': contract['task_id'],
        'baseline_ref': contract['baseline_ref'],
        'seam': contract['seam'],
        'authorized_files': list(reversed(contract['authorized_files'])),
        'allowed_new_production_files': list(reversed(contract['allowed_new_production_files'])),
        'production_changed_lines_max': contract['production_changed_lines_max'],
        'test_changed_lines_max': contract['test_changed_lines_max'],
        'forbidden_files': list(reversed(contract['forbidden_files'])),
        'forbidden_imports': list(reversed(contract['forbidden_imports'])),
        'forbidden_symbols': list(reversed(contract['forbidden_symbols'])),
        'required_test_commands': list(reversed(contract['required_test_commands'])),
        'gate_blob_sha': contract['gate_blob_sha'],
    }
    contract_path, contract_sha = _write_contract(repo, reordered, pretty=False)

    result = _evaluate(repo, contract_path, contract_sha)

    assert result['pass'] is True
    assert result['contract_sha'] == contract_sha
    assert result['gate_blob_sha'] == GATE_BLOB_SHA
    assert result['files'] == [
        {'path': 'scripts/householder/validation_policy.py', 'additions': 1, 'deletions': 1},
    ]


def test_valid_slice_passes_and_is_deterministic(tmp_path: Path) -> None:
    repo = _base_repo(tmp_path)
    _write(repo, 'scripts/householder/validation_policy.py', 'def validate(value):\n    return value.strip().lower()\n')
    contract = _contract()
    contract_path, contract_sha = _write_contract(repo, contract)

    first = _evaluate(repo, contract_path, contract_sha)
    second = _evaluate(repo, contract_path, contract_sha)
    cli_first = _run_cli(repo, contract_path, contract_sha)
    cli_second = _run_cli(repo, contract_path, contract_sha)

    assert first['pass'] is True
    assert first == second
    assert cli_first.returncode == 0
    assert cli_first.stdout == cli_second.stdout
    assert json.loads(cli_first.stdout) == first
    assert first['files'] == [
        {'path': 'scripts/householder/validation_policy.py', 'additions': 1, 'deletions': 1},
    ]
    assert first['production_totals'] == {'additions': 1, 'deletions': 1, 'changed_lines': 2}
    assert first['test_totals'] == {'additions': 0, 'deletions': 0, 'changed_lines': 0}
    assert first['violations'] == []


def test_aggregate_counts_additions_deletions_and_untracked(tmp_path: Path) -> None:
    repo = _base_repo(tmp_path)
    _write(repo, 'scripts/householder/validation_policy.py', 'def validate(value):\n    return value.strip().upper()\n')
    _write(repo, 'tests/unit/test_validation_policy.py', 'def test_validate():\n    assert True\n    assert 1 == 1\n')
    _write(repo, 'scripts/householder/new_validation_policy.py', 'first\nsecond\n')
    contract = _contract()
    contract_path, contract_sha = _write_contract(repo, contract)

    result = _evaluate(repo, contract_path, contract_sha)

    assert result['pass'] is True
    assert result['files'] == [
        {'path': 'scripts/householder/new_validation_policy.py', 'additions': 2, 'deletions': 0},
        {'path': 'scripts/householder/validation_policy.py', 'additions': 1, 'deletions': 1},
        {'path': 'tests/unit/test_validation_policy.py', 'additions': 1, 'deletions': 0},
    ]
    assert result['production_totals'] == {'additions': 3, 'deletions': 1, 'changed_lines': 4}
    assert result['test_totals'] == {'additions': 1, 'deletions': 0, 'changed_lines': 1}


def test_production_and_test_totals_are_separate(tmp_path: Path) -> None:
    repo = _base_repo(tmp_path)
    _write(repo, 'scripts/householder/validation_policy.py', 'alpha\nbeta\ngamma\n')
    _write(repo, 'tests/unit/test_validation_policy.py', 'one\ntwo\n')
    _commit(repo, 'baseline-2')

    _write(repo, 'scripts/householder/validation_policy.py', 'alpha\ngamma\ndelta\n')
    _write(repo, 'tests/unit/test_validation_policy.py', 'one\nthree\n')
    contract = _contract()
    contract_path, contract_sha = _write_contract(repo, contract)

    result = _evaluate(repo, contract_path, contract_sha)

    assert result['pass'] is True
    assert result['production_totals'] == {'additions': 1, 'deletions': 1, 'changed_lines': 2}
    assert result['test_totals'] == {'additions': 1, 'deletions': 1, 'changed_lines': 2}


def test_unauthorized_and_new_files_rejected(tmp_path: Path) -> None:
    repo = _base_repo(tmp_path)
    _write(repo, 'scripts/householder/validation_policy.py', 'def validate(value):\n    return value.strip()\n')
    _write(repo, 'scripts/householder/extra.py', 'print(1)\n')
    contract = _contract()
    contract_path, contract_sha = _write_contract(repo, contract)

    result = _evaluate(repo, contract_path, contract_sha)

    assert result['pass'] is False
    assert 'unauthorized file changed: scripts/householder/extra.py' in result['violations']
    assert 'new production file not allowed: scripts/householder/extra.py' in result['violations']


def test_forbidden_file_import_and_symbol_rejected(tmp_path: Path) -> None:
    repo = _base_repo(tmp_path)
    _write(
        repo,
        'scripts/householder/validation_policy.py',
        'import os\n\ndef validate(value):\n    return dangerous_call(value)\n',
    )
    contract = _contract(
        forbidden_files=['scripts/householder/validation_policy.py'],
        forbidden_imports=['os'],
        forbidden_symbols=['dangerous_call'],
    )
    contract_path, contract_sha = _write_contract(repo, contract)

    result = _evaluate(repo, contract_path, contract_sha)

    assert result['pass'] is False
    assert 'forbidden file changed: scripts/householder/validation_policy.py' in result['violations']
    assert 'forbidden import rejected: os' in result['violations']
    assert 'forbidden symbol rejected: dangerous_call' in result['violations']


def test_contract_mutation_rejected(tmp_path: Path) -> None:
    repo = _base_repo(tmp_path)
    _write(repo, 'scripts/householder/validation_policy.py', 'def validate(value):\n    return value.strip().lower()\n')
    contract = _contract()
    contract_path, contract_sha = _write_contract(repo, contract)
    mutated = json.loads(contract_path.read_text(encoding='utf-8'))
    mutated['production_changed_lines_max'] = 161
    contract_path.write_text(json.dumps(mutated, indent=2) + '\n', encoding='utf-8')

    with pytest.raises(ValueError, match='contract digest mismatch'):
        _evaluate(repo, contract_path, contract_sha)


def test_gate_mutation_rejected(tmp_path: Path) -> None:
    repo = _base_repo(tmp_path)
    _write(repo, 'scripts/householder/validation_policy.py', 'def validate(value):\n    return value.strip().lower()\n')
    contract = _contract()
    contract_path, contract_sha = _write_contract(repo, contract)

    mutated_gate = tmp_path / 'mutated_gate.py'
    shutil.copy2(GATE_PATH, mutated_gate)
    mutated_gate.write_text(mutated_gate.read_text(encoding='utf-8') + '\n# mutation\n', encoding='utf-8')

    with pytest.raises(ValueError, match='gate blob digest mismatch'):
        _evaluate(repo, contract_path, contract_sha, gate_path=mutated_gate)


@pytest.mark.parametrize(
    'baseline_ref, modifier, expected',
    [
        ('definitely-missing', lambda repo: _write(repo, 'scripts/householder/validation_policy.py', 'changed\n'), 'baseline reference not found'),
        ('HEAD', lambda repo: _write_binary(repo, 'scripts/householder/binary.bin', b'\x00binary\x00'), 'binary file not supported'),
        ('HEAD', lambda repo: _run_git(repo, 'mv', 'scripts/householder/validation_policy.py', 'scripts/householder/validation_policy_renamed.py'), 'renames and copies are not supported'),
    ],
)
def test_missing_baseline_binary_and_rename_fail_closed(tmp_path: Path, baseline_ref: str, modifier, expected: str) -> None:
    repo = _base_repo(tmp_path)
    _write(repo, 'scripts/householder/validation_policy.py', 'def validate(value):\n    return value.strip()\n')
    modifier(repo)
    contract = _contract(baseline_ref=baseline_ref)
    contract_path, contract_sha = _write_contract(repo, contract)

    with pytest.raises(ValueError, match=expected):
        _evaluate(repo, contract_path, contract_sha)


def test_ambiguous_repo_root_rejected(tmp_path: Path) -> None:
    repo = _base_repo(tmp_path)
    _write(repo, 'scripts/householder/validation_policy.py', 'def validate(value):\n    return value.strip().lower()\n')
    contract = _contract()
    contract_path, contract_sha = _write_contract(repo, contract)

    with pytest.raises(ValueError, match='ambiguous repo roots or not in a git repository'):
        _evaluate(repo, contract_path, contract_sha, cwd=tmp_path)
