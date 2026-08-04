import json
import os
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scripts.householder.database_models import Base, ImportBatch, ReviewDecision, create_db_engine
from scripts.uploader.app import app


@pytest.fixture
def history_client(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'route-history.db'}"
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(ImportBatch(id="route-batch", filename="route.csv", upload_timestamp=datetime(2026, 1, 1), status="review", raw_row_count=1))
    session.add_all([
        ReviewDecision(batch_id="route-batch", decision="accept", reviewer="A", created_at=datetime(2026, 1, 2)),
        ReviewDecision(batch_id="route-batch", decision="defer", reviewer="B", created_at=datetime(2026, 1, 3)),
        ReviewDecision(batch_id="other-batch", decision="other", reviewer="X", created_at=datetime(2026, 1, 1)),
    ])
    session.commit()
    session.close()
    os.environ["GIVEBUTTER_DATABASE_URL"] = database_url
    os.environ["HOUSEHOLDER_REPOSITORY"] = "database"
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client, database_url


def test_html_json_parity_and_navigation(history_client):
    client, database_url = history_client
    engine = create_engine(database_url)
    before = sessionmaker(bind=engine)().query(ReviewDecision).count()
    html = client.get("/imports/route-batch/decision-history")
    download = client.get("/imports/route-batch/decision-history.json")

    assert html.status_code == 200
    assert b"Decision History" in html.data
    assert b"route-batch/decision-history.json" in html.data
    assert b"/imports/route-batch/audit" in html.data
    assert b"/imports/route-batch/dashboard" in html.data
    assert b"/imports/route-batch/readiness" in html.data
    assert b"/imports/route-batch/exports" in html.data
    assert download.status_code == 200
    assert download.content_type == "application/json"
    assert "attachment" in download.headers["Content-Disposition"]
    assert "route-batch-decision-history.json" in download.headers["Content-Disposition"]
    report = json.loads(download.data)
    assert [item["decision"] for item in report["decisions"]] == ["accept", "defer"]
    assert b"other" not in html.data
    after_session = sessionmaker(bind=engine)()
    assert after_session.query(ReviewDecision).count() == before
    after_session.close()


def test_empty_missing_and_cross_import_behavior(history_client):
    client, database_url = history_client
    engine = create_engine(database_url)
    session = sessionmaker(bind=engine)()
    session.add(ImportBatch(id="empty-route", filename="empty.csv", upload_timestamp=datetime(2026, 1, 1), status="review", raw_row_count=0))
    session.commit()
    session.close()

    assert client.get("/imports/empty-route/decision-history").status_code == 200
    assert client.get("/imports/empty-route/decision-history.json").json["decisions"] == []
    assert client.get("/imports/missing-route/decision-history").status_code == 404
    assert client.get("/imports/missing-route/decision-history.json").status_code == 404
