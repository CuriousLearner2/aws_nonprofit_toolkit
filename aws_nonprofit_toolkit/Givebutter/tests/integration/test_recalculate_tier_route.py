import importlib

from scripts.uploader.app import app

uploader_module = importlib.import_module("scripts.uploader.app")


def test_recalculate_tier_route_delegates_and_preserves_response(monkeypatch, tmp_path):
    app.config["TESTING"] = True
    monkeypatch.setattr(uploader_module, "PROCESSING_DIR", tmp_path)
    (tmp_path / "batch.csv").write_text("transaction_id\nTXN-001\n", encoding="utf-8")
    expected = {"tier": "WARNING", "issues": ["Date: needs review"], "suggestions": ["fix date"]}
    calls = []

    def fake_service(record, processing_dir, filename):
        calls.append((record, processing_dir, filename))
        return expected

    monkeypatch.setattr(uploader_module, "recalculate_tier_service", type("Service", (), {"recalculate_tier": fake_service}))
    with app.test_client() as client:
        response = client.post("/api/processing/batch.csv/recalculate-tier", json={"record": {"transaction_id": "TXN-001"}})

    assert response.status_code == 200
    assert response.get_json() == expected
    assert calls[0][0] == {"transaction_id": "TXN-001"}
    assert calls[0][2] == "batch.csv"


def test_recalculate_tier_route_rejects_invalid_filename():
    app.config["TESTING"] = True
    with app.test_client() as client:
        response = client.post("/api/processing/not-a-csv.txt/recalculate-tier", json={"record": {"transaction_id": "TXN-001"}})

    assert response.status_code in {400, 404}


def test_recalculate_tier_route_rejects_missing_record(monkeypatch, tmp_path):
    app.config["TESTING"] = True
    monkeypatch.setattr(uploader_module, "PROCESSING_DIR", tmp_path)
    (tmp_path / "batch.csv").write_text("transaction_id\nTXN-001\n", encoding="utf-8")
    with app.test_client() as client:
        response = client.post("/api/processing/batch.csv/recalculate-tier", json={})

    assert response.status_code == 400
    assert response.get_json() == {"error": "No record provided"}


def test_recalculate_tier_route_maps_service_errors_to_500(monkeypatch, tmp_path):
    app.config["TESTING"] = True
    monkeypatch.setattr(uploader_module, "PROCESSING_DIR", tmp_path)
    (tmp_path / "batch.csv").write_text("transaction_id\nTXN-001\n", encoding="utf-8")

    def failing_service(record, processing_dir, filename):
        raise RuntimeError("validation unavailable")

    monkeypatch.setattr(uploader_module, "recalculate_tier_service", type("Service", (), {"recalculate_tier": failing_service}))
    with app.test_client() as client:
        response = client.post("/api/processing/batch.csv/recalculate-tier", json={"record": {"transaction_id": "TXN-001"}})

    assert response.status_code == 500
    assert response.get_json() == {"error": "Recalculation failed: validation unavailable"}
