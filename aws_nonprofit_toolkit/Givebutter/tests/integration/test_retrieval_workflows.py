"""Focused contracts for import-level and cross-import retrieval."""

from datetime import datetime, timezone
from pathlib import Path
import sys

import pytest
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.householder.database_models import Base, ImportBatch, ImportContact, RawImportRow, ReviewDecision, create_db_engine
from scripts.householder.retrieval_service import search_import_rows


@pytest.fixture
def retrieval_db(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'retrieval.db'}"
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    for batch_id, filename, name, email, phone, txn in (
        ('batch-a', 'january.csv', 'Smith One', 'smith.one@example.com', '+14155550101', 'TX-100'),
        ('batch-b', 'february.csv', 'Jones Two', 'jones.two@example.com', '+442071838750', 'TX-200'),
    ):
        session.add(ImportBatch(
            id=batch_id, filename=filename,
            upload_timestamp=datetime.now(timezone.utc), status='pending_review',
        ))
        session.flush()
        raw = RawImportRow(
            batch_id=batch_id, row_index=1,
            raw_csv_data={'name': name, 'email': email, 'phone': phone,
                          'transaction_id': txn, 'amount': '10.00', 'address': '1 Main St'},
        )
        session.add(raw)
        session.flush()
        session.add(ImportContact(
            batch_id=batch_id, raw_import_row_id=raw.id,
            first_name=name.split()[0], last_name=name.split()[1],
            email=email, phone=phone, address_line1='1 Main St', amount=10,
        ))
    session.commit()
    session.close()
    return database_url


def test_cross_import_search_identifies_source_and_composes_filters(retrieval_db):
    result = search_import_rows(
        {'GIVEBUTTER_DATABASE_URL': retrieval_db},
        query='smith',
        status='No issues',
        batch_id='batch-a',
    )
    assert len(result['results']) == 1
    row = result['results'][0]
    assert row['filename'] == 'january.csv'
    assert row['batch_id'] == 'batch-a'
    assert row['validation_url'] == f"/imports/batch-a/validation#validation-row-{row['row_id']}"
    assert row['disposition_label'] == 'No disposition'


def test_cross_import_search_supports_transaction_and_no_disposition(retrieval_db):
    result = search_import_rows(
        {'GIVEBUTTER_DATABASE_URL': retrieval_db},
        query='TX-200',
        disposition='none',
    )
    assert [row['batch_id'] for row in result['results']] == ['batch-b']


def test_search_route_renders_read_only_source_link(retrieval_db, monkeypatch):
    from scripts.uploader.app import app

    app.config.update(TESTING=True, GIVEBUTTER_DATABASE_URL=retrieval_db)
    monkeypatch.setenv('HOUSEHOLDER_REPOSITORY', 'database')
    with app.test_client() as client:
        response = client.get('/search?q=smith')

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert 'january.csv' in body
    assert 'Open original row' in body
    assert '/imports/batch-a/validation#validation-row-' in body
    assert 'raw imports remain in their original batches' in body


def test_search_route_honors_existing_auth_boundary(retrieval_db, monkeypatch):
    import scripts.uploader.app as app_module
    app = app_module.app

    app.config.update(TESTING=True, GIVEBUTTER_DATABASE_URL=retrieval_db)
    monkeypatch.setattr(app_module, 'ADMIN_TOKEN', 'retrieval-secret')
    with app.test_client() as client:
        assert client.get('/search').status_code == 401
        authorized = client.get('/search', headers={'Authorization': 'Bearer retrieval-secret'})
    assert authorized.status_code == 200


def test_cleared_disposition_does_not_match_reviewer_filter(retrieval_db):
    engine = create_db_engine(retrieval_db)
    session = sessionmaker(bind=engine)()
    session.add_all([
        ReviewDecision(
            batch_id='batch-a', raw_import_row_id=1, decision='row_status:accept_as_is',
            reviewed_values={'notes': 'accepted'}, reviewer='Old Reviewer',
        ),
        ReviewDecision(
            batch_id='batch-a', raw_import_row_id=1, decision='row_status:clear_decision',
            reviewed_values={}, reviewer='Old Reviewer',
        ),
    ])
    session.commit()
    session.close()

    result = search_import_rows(
        {'GIVEBUTTER_DATABASE_URL': retrieval_db}, reviewer='Old Reviewer'
    )
    assert result['results'] == []
