from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scripts.householder.database_models import Base, ImportBatch, ReviewDecision
from scripts.householder.decision_history_view_service import (
    get_decision_history_report,
    to_deterministic_json,
)


def _database(tmp_path):
    url = f"sqlite:///{tmp_path / 'history.db'}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    return url, sessionmaker(bind=engine)


def _seed(session_factory):
    session = session_factory()
    session.add_all([
        ImportBatch(id="batch-a", filename="a.csv", upload_timestamp=datetime(2026, 1, 1), status="review", raw_row_count=1),
        ImportBatch(id="batch-b", filename="b.csv", upload_timestamp=datetime(2026, 1, 1), status="review", raw_row_count=1),
    ])
    session.flush()
    same_time = datetime(2026, 1, 2, 12, 0, 0)
    session.add_all([
        ReviewDecision(batch_id="batch-a", decision="first", reviewer="one", created_at=same_time),
        ReviewDecision(batch_id="batch-a", decision="second", reviewer="two", created_at=same_time),
        ReviewDecision(batch_id="batch-b", decision="other", reviewer="other", created_at=same_time),
    ])
    session.commit()
    session.close()


def test_orders_by_created_at_then_id_and_isolates_import(tmp_path):
    url, factory = _database(tmp_path)
    _seed(factory)

    report = get_decision_history_report("batch-a", {"GIVEBUTTER_DATABASE_URL": url})

    assert report["import_id"] == "batch-a"
    assert [item["decision"] for item in report["decisions"]] == ["first", "second"]
    assert all(item["reviewer"] != "other" for item in report["decisions"])


def test_empty_history_is_a_stable_report(tmp_path):
    url, factory = _database(tmp_path)
    session = factory()
    session.add(ImportBatch(id="empty", filename="empty.csv", upload_timestamp=datetime(2026, 1, 1), status="review", raw_row_count=0))
    session.commit()
    session.close()

    assert get_decision_history_report("empty", {"GIVEBUTTER_DATABASE_URL": url}) == {
        "import_id": "empty", "decisions": []
    }


def test_missing_import_is_not_reported_as_empty(tmp_path):
    url, factory = _database(tmp_path)
    with pytest.raises(LookupError):
        get_decision_history_report("missing", {"GIVEBUTTER_DATABASE_URL": url})


def test_json_serialization_is_deterministic(tmp_path):
    url, factory = _database(tmp_path)
    _seed(factory)
    report = get_decision_history_report("batch-a", {"GIVEBUTTER_DATABASE_URL": url})
    assert to_deterministic_json(report) == to_deterministic_json(report)
    assert to_deterministic_json(report).endswith("\n")
