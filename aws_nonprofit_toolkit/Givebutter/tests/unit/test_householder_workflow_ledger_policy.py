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


def test_orchestrator_makes_ledger_sequence_conditional():
    text = ORCHESTRATOR.read_text(encoding="utf-8")
    assert "Use the heavier ledger/budget path only for:" in text
    assert "Do not initialize or advance the ledger for ordinary scoped work unless the task contract says ledger progression is required." in text
    assert "Do not require ledger transitions unless `Ledger progression required? yes`." in text
    assert "When ledger progression is required, use the execution-safety ES rules and `householder_state.py`." in text


def test_policy_docs_scope_ledger_owner_to_heavy_path():
    implementer = IMPLEMENTER.read_text(encoding="utf-8")
    safety = EXECUTION_SAFETY.read_text(encoding="utf-8")
    contract = TASK_CONTRACT.read_text(encoding="utf-8")

    assert "Ready for reviewer? yes/no" in implementer
    assert "ES-08/ES-13 ledger, batch, and budget machinery is mandatory only when the task contract sets `Ledger progression required? yes`" in safety
    assert "executable owner" in safety
    assert "Raw prose counters or inferred readiness do not override ledger state" in safety
    assert "Ledger progression required? yes/no" in contract
    assert "Ordinary low/medium-risk scoped work normally sets `Ledger progression required? no`." in contract
