"""Reload/sequence regression for the shared reviewer-state API projection."""

from datetime import datetime, timezone
from pathlib import Path
import tempfile

import pytest
from sqlalchemy.orm import sessionmaker

from scripts.householder.database_models import Base, ImportBatch, RawImportRow, create_db_engine
from scripts.uploader.app import app


@pytest.fixture
def reviewer_state_client(monkeypatch):
    db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = Path(db_file.name)
    db_file.close()
    database_url = f"sqlite:///{db_path}"
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(ImportBatch(
        id="reviewer-state-sequence",
        filename="sequence.csv",
        upload_timestamp=datetime.now(timezone.utc),
        status="pending_review",
        raw_row_count=1,
    ))
    row = RawImportRow(
        batch_id="reviewer-state-sequence",
        row_index=1,
        raw_csv_data={"name": "Sequence User", "email": "sequence@example.com"},
    )
    session.add(row)
    session.commit()
    raw_id = row.id
    session.close()

    monkeypatch.setitem(app.config, "TESTING", True)
    monkeypatch.setitem(app.config, "HOUSEHOLDER_REPOSITORY", "database")
    monkeypatch.setitem(app.config, "GIVEBUTTER_DATABASE_URL", database_url)
    monkeypatch.setenv("HOUSEHOLDER_REPOSITORY", "database")
    monkeypatch.setenv("GIVEBUTTER_DATABASE_URL", database_url)
    with app.test_client() as client:
        yield client, raw_id
    db_path.unlink(missing_ok=True)


def _save(client, raw_id, decision, sequence):
    return client.post(
        "/imports/reviewer-state-sequence/row-decision",
        json={
            "raw_import_row_id": raw_id,
            "decision": decision,
            "notes": f"sequence {sequence}",
            "reviewer_name": "Sequence Reviewer",
            "interaction_sequence": sequence,
        },
    )


def test_reload_preserves_next_sequence_and_rejects_stale_mutation(reviewer_state_client):
    client, raw_id = reviewer_state_client

    first = _save(client, raw_id, "needs_follow_up", 1)
    assert first.status_code == 200

    reloaded = client.get(f"/imports/reviewer-state-sequence/row-decision/{raw_id}")
    assert reloaded.status_code == 200
    assert reloaded.get_json()["interaction_sequence"] == 1

    second = _save(client, raw_id, "reject_row", 2)
    assert second.status_code == 200

    stale = _save(client, raw_id, "needs_follow_up", 1)
    assert stale.status_code == 200
    assert stale.get_json()["stale_ignored"] is True

    final = client.get(f"/imports/reviewer-state-sequence/row-decision/{raw_id}").get_json()
    assert final["decision"] == "reject_row"
    assert final["interaction_sequence"] == 2
    assert [event["decision"] for event in final["history"]] == [
        "reject_row", "needs_follow_up"
    ]
