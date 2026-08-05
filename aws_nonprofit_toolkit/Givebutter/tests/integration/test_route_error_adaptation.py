import importlib

import pytest

app_module = importlib.import_module("scripts.uploader.app")


@pytest.fixture
def client():
    app_module.app.config.update(TESTING=True)
    with app_module.app.test_client() as test_client:
        yield test_client


def test_validation_failure_keeps_public_400_message_and_no_exception_leak(client, monkeypatch):
    def fail(**kwargs):
        raise ValueError("decision is required")

    monkeypatch.setattr(app_module.validation_decision_service, "record_validation_decision", fail)
    response = client.post("/imports/demo/validation/1/decision", data={})
    assert response.status_code == 400
    assert response.get_json() == {"error": "decision is required"}
    assert "ValueError" not in response.get_data(as_text=True)


def test_duplicate_unexpected_failure_is_safe_500(client, monkeypatch):
    def fail(**kwargs):
        raise RuntimeError("private repository detail")

    monkeypatch.setattr(app_module.duplicate_decision_service, "record_duplicate_decision", fail)
    response = client.post("/imports/demo/duplicates/1/decision", data={"decision": "same_person"})
    assert response.status_code == 500
    assert response.get_json() == {"error": "Error recording decision"}
    assert "private repository detail" not in response.get_data(as_text=True)
