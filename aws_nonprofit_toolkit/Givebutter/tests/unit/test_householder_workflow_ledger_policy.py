"""Regression tests for ledger workflow policy references."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATOR = ROOT / ".claude" / "agents" / "orchestrator.md"
IMPLEMENTER = ROOT / ".claude" / "agents" / "implementer.md"
EXECUTION_SAFETY = ROOT / ".claude" / "skills" / "householder-debug" / "policy" / "execution-safety.md"
TASK_CONTRACT = ROOT / ".claude" / "skills" / "householder-debug" / "policy" / "task-contract.md"


def _assert_order(text: str, snippets: list[str]) -> None:
    cursor = 0
    for snippet in snippets:
        next_pos = text.find(snippet, cursor)
        assert next_pos != -1, f"missing snippet: {snippet}"
        cursor = next_pos + len(snippet)


def test_orchestrator_requires_ledger_sequence():
    text = ORCHESTRATOR.read_text(encoding="utf-8")
    _assert_order(
        text,
        [
            "can-write",
            "begin-edit --batch <type>",
            "can-run-focused",
            "begin-focused-run",
            "finish-focused-run --exit-code <code>",
            "classify-failure --type <type>",
            "begin-review",
            "finish-review --reviewer <verdict> --breaker <verdict>",
        ],
    )
    assert "Ledger refusal is terminal for the current task." in text
    assert "ledger sequencing and refusal handling" in text


def test_implementer_and_policy_docs_name_ledger_owner():
    implementer = IMPLEMENTER.read_text(encoding="utf-8")
    safety = EXECUTION_SAFETY.read_text(encoding="utf-8")
    contract = TASK_CONTRACT.read_text(encoding="utf-8")

    assert "householder_state.py can-write" in implementer
    assert "finish-focused-run --exit-code <code>" in implementer
    assert "executable owner" in safety
    assert "Raw prose counters or inferred readiness do not override ledger state" in safety
    assert "Ledger executable owner:" in contract
    assert "Ledger progression required? yes/no" in contract
    assert "Ledger refusal terminal? yes/no" in contract
