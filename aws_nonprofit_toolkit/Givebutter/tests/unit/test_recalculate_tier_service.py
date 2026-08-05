import pandas as pd

from scripts.householder import recalculate_tier_service as service


def _record():
    return {
        "transaction_id": "TXN-001",
        "date": "2026-05-15",
        "email": "john@example.com",
        "amount": "100",
        "name": "John Smith",
        "phone": "555-0100",
        "address": "1 Main St",
        "Operator_Decision": "approve",
        "Operator_Notes": "reviewed",
    }


def _patch_validators(monkeypatch, *, issue_field=None):
    monkeypatch.setattr(service, "load_rules", lambda: {"rules": True})
    monkeypatch.setattr(service, "load_reference_list", lambda: {"reference": True})
    monkeypatch.setattr(
        service,
        "build_header_mapping",
        lambda keys: {key: key for key in keys if key not in {"Operator_Decision", "Operator_Notes"}},
    )

    def result(field):
        if field == issue_field:
            return "WARNING", "needs review", "correct it"
        return "PASS", None, None

    monkeypatch.setattr(service, "validate_transaction_id", lambda record, headers: result("transaction_id"))
    monkeypatch.setattr(service, "validate_date", lambda record, headers: result("date"))
    monkeypatch.setattr(service, "validate_email", lambda record, headers, rules, reference: result("email"))
    monkeypatch.setattr(service, "validate_amount", lambda record, headers, reference: result("amount"))
    monkeypatch.setattr(service, "validate_name", lambda record, headers, reference: result("name"))
    monkeypatch.setattr(service, "validate_phone", lambda record, headers, rules: result("phone"))
    monkeypatch.setattr(service, "validate_address", lambda record, headers: ("PASS", None))
    monkeypatch.setattr(service, "assign_tier", lambda validation: "WARNING" if issue_field else "PASS")


def test_service_aggregates_validation_and_persists_matching_row(tmp_path, monkeypatch):
    _patch_validators(monkeypatch, issue_field="date")
    path = tmp_path / "batch.csv"
    pd.DataFrame([{"transaction_id": "TXN-001", "name": "Old"}]).to_csv(path, index=False)

    result = service.recalculate_tier(_record(), tmp_path, "batch.csv")

    assert result == {"tier": "WARNING", "issues": ["Date: needs review"], "suggestions": ["correct it"]}
    saved = pd.read_csv(path, dtype=str).fillna("").iloc[0]
    assert saved["name"] == "John Smith"
    assert saved["Validation_Tier"] == "WARNING"
    assert saved["Operator_Decision"] == "approve"
    assert saved["Operator_Notes"] == "reviewed"


def test_service_limits_issues_and_suggestions_to_five(tmp_path, monkeypatch):
    _patch_validators(monkeypatch, issue_field="transaction_id")
    monkeypatch.setattr(service, "validate_date", lambda record, headers: ("WARNING", "bad date", "fix date"))
    monkeypatch.setattr(service, "validate_email", lambda record, headers, rules, reference: ("WARNING", "bad email", "fix email"))
    monkeypatch.setattr(service, "validate_amount", lambda record, headers, reference: ("WARNING", "bad amount", "fix amount"))
    monkeypatch.setattr(service, "validate_name", lambda record, headers, reference: ("WARNING", "bad name", "fix name"))
    monkeypatch.setattr(service, "validate_phone", lambda record, headers, rules: ("WARNING", "bad phone", "fix phone"))
    monkeypatch.setattr(service, "validate_address", lambda record, headers: ("WARNING", "bad address"))
    monkeypatch.setattr(service, "assign_tier", lambda validation: "FAIL")

    result = service.recalculate_tier(_record(), tmp_path, "missing.csv")

    assert result["tier"] == "FAIL"
    assert len(result["issues"]) == 5
    assert len(result["suggestions"]) == 5


def test_service_keeps_persistence_failures_nonfatal(tmp_path, monkeypatch):
    _patch_validators(monkeypatch)
    monkeypatch.setattr(service.pd, "read_csv", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("unreadable")))

    result = service.recalculate_tier(_record(), tmp_path, "batch.csv")

    assert result == {"tier": "PASS", "issues": [], "suggestions": []}
