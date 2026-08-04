import json
import os
from datetime import datetime

from sqlalchemy.orm import sessionmaker

from scripts.householder.database_models import Base, ImportBatch, ReviewDecision, create_db_engine
from scripts.uploader.app import app


def test_import_decision_history_journey(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'journey.db'}"
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(ImportBatch(id="journey", filename="journey.csv", upload_timestamp=datetime(2026, 1, 1), status="review", raw_row_count=1))
    session.add(ReviewDecision(batch_id="journey", decision="accept", reviewer="journey", created_at=datetime(2026, 1, 2)))
    session.commit()
    session.close()
    os.environ["GIVEBUTTER_DATABASE_URL"] = database_url
    os.environ["HOUSEHOLDER_REPOSITORY"] = "database"
    app.config["TESTING"] = True
    with app.test_client() as client:
        audit = client.get("/imports/journey/audit")
        assert b"/imports/journey/decision-history" in audit.data
        report = client.get("/imports/journey/decision-history")
        assert report.status_code == 200
        assert b"journey" in report.data
        download = client.get("/imports/journey/decision-history.json")
        assert json.loads(download.data)["decisions"][0]["decision"] == "accept"
        for destination in ("audit", "dashboard", "readiness", "exports"):
            assert client.get(f"/imports/journey/{destination}").status_code == 200
