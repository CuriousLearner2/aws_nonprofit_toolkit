from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import sessionmaker

from scripts.householder.database_models import Base, ImportBatch, RawImportRow, ReviewDecision, create_db_engine
from scripts.householder.effective_value_resolution import (
    effective_value_for_field,
    fold_row_reviewed_values,
    get_effective_values,
    merge_effective_values,
)


def test_merge_effective_values_prefers_reviewed_over_raw_and_aliases():
    effective = merge_effective_values(
        {"name": "raw", "street address": "12 Main St"},
        {"name": "reviewed", "address": "34 Elm St"},
    )
    assert effective["name"] == "reviewed"
    assert effective["address"] == "34 Elm St"
    assert effective_value_for_field("address", {"street address": "12 Main St"}, {"address": "34 Elm St"}) == "34 Elm St"


def test_get_effective_values_merges_persisted_corrections(tmp_path: Path):
    engine = create_db_engine(f"sqlite:///{tmp_path / 'review.db'}")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        session.add(
            ImportBatch(
                id="batch",
                filename="rows.csv",
                upload_timestamp=datetime.now(timezone.utc),
                status="pending",
            )
        )
        session.add(RawImportRow(id=1, batch_id="batch", row_index=0, raw_csv_data={"name": "Raw Name", "street address": "12 Main St"}))
        session.add(ReviewDecision(batch_id="batch", raw_import_row_id=1, decision="accept_issue", reviewed_values={"name": "Reviewed Name", "street address": "34 Elm St"}))
        session.commit()
        effective = get_effective_values("batch", 1, f"sqlite:///{tmp_path / 'review.db'}")
        assert effective["name"] == "Reviewed Name"
        assert effective["address"] == "34 Elm St"
    finally:
        session.close()


def test_fold_row_reviewed_values_uses_decision_order_and_row_scope():
    class Decision:
        def __init__(self, created_at, decision_id, row_id, review_item_id, values):
            self.created_at = created_at
            self.id = decision_id
            self.raw_import_row_id = row_id
            self.review_item_id = review_item_id
            self.reviewed_values = values

    decisions = [
        Decision(2, 2, 7, None, {"email": "new@example.com"}),
        Decision(1, 1, 7, None, {"email": "old@example.com", "phone": "555"}),
        Decision(3, 3, 7, 99, {"email": "item@example.com"}),
    ]
    assert fold_row_reviewed_values(decisions) == {7: {"email": "new@example.com", "phone": "555"}}
