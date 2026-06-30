"""
Unit tests for export preview service.

Tests verify that export preview correctly interprets reviewer decisions
without mutating source data.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.householder.export_preview_service import build_export_preview
from scripts.householder.database_models import (
    Base, ImportBatch, RawImportRow, ImportContact, ReviewItem, ReviewDecision
)
from sqlalchemy.orm import sessionmaker
from scripts.householder.database_models import create_db_engine


@pytest.fixture
def temp_db():
    """Create temporary SQLite database for testing."""
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()

    database_url = f'sqlite:///{db_path}'
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)

    yield database_url, engine

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def seeded_batch(temp_db):
    """Create a batch with contacts and review items."""
    database_url, engine = temp_db
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create batch
    batch = ImportBatch(
        id='IMP-2025-0101-A',
        filename='test.csv',
        upload_timestamp=datetime.now(timezone.utc),
    )
    session.add(batch)
    session.flush()

    # Create raw row
    row = RawImportRow(
        batch_id='IMP-2025-0101-A',
        row_index=1,
        raw_csv_data={
            'Name': 'John Smith',
            'Email': 'john@example.com',
            'Phone': '555-1234',
            'Amount': '100.00',
            'Address': '123 Main St',
            'transaction_id': 'TXN-001'
        },
    )
    session.add(row)
    session.flush()

    # Create contact
    contact = ImportContact(
        batch_id='IMP-2025-0101-A',
        raw_import_row_id=row.id,
        first_name='John',
        last_name='Smith',
        email='john@example.com',
        phone='555-1234',
        address_line1='123 Main St',
        city='Springfield',
        state='IL',
        postal_code='62701',
        amount=100.00,
    )
    session.add(contact)
    session.commit()

    contact_id = contact.id
    batch_id = batch.id
    session.close()

    yield database_url, contact_id, batch_id


class TestExportPreviewServiceValidation:
    """Test export preview service validation."""

    def test_invalid_batch_raises_error(self):
        """Test that invalid batch ID raises ValueError."""
        with pytest.raises(ValueError, match="database configuration"):
            build_export_preview('INVALID-ID')

    def test_missing_database_config_raises_error(self):
        """Test that missing database configuration raises ValueError."""
        with pytest.raises(ValueError, match="database configuration"):
            build_export_preview(
                import_id='IMP-2025-0101-A',
                config={},
            )


class TestExportPreviewBasicStructure:
    """Test export preview basic structure and row generation."""

    def test_returns_one_row_per_contact(self, seeded_batch):
        """Test that preview returns one row per contact."""
        database_url, contact_id, batch_id = seeded_batch

        result = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})

        assert result.row_count == 1
        assert len(result.export_rows) == 1

    def test_no_decisions_uses_original_values(self, seeded_batch):
        """Test that with no decisions, preview uses original contact values."""
        database_url, contact_id, batch_id = seeded_batch

        result = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})
        row = result.export_rows[0]

        assert row.first_name == 'John'
        assert row.last_name == 'Smith'
        assert row.email == 'john@example.com'
        assert row.phone == '555-1234'
        assert row.address_line1 == '123 Main St'
        assert row.city == 'Springfield'
        assert row.state == 'IL'
        assert row.postal_code == '62701'


class TestExportPreviewNormalizationDecisions:
    """Test normalization decision interpretation."""

    def test_accept_normalization_overrides_field(self, seeded_batch, temp_db):
        """Test that accept_normalization overrides derived export value."""
        database_url, contact_id, batch_id = seeded_batch

        Session = sessionmaker(bind=temp_db[1])
        session = Session()

        # Create normalization review item
        norm_item = ReviewItem(
            batch_id=batch_id,
            item_type='normalization',
            payload_json={'field': 'email', 'raw_value': 'john@example.com', 'normalized_value': 'john.smith@example.com'},
        )
        session.add(norm_item)
        session.flush()

        # Create accept decision
        decision = ReviewDecision(
            batch_id=batch_id,
            review_item_id=norm_item.id,
            decision='accept_normalization',
            reviewed_values={'field': 'email', 'normalized_value': 'john.smith@example.com'},
        )
        session.add(decision)
        session.commit()
        session.close()

        result = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})
        row = result.export_rows[0]

        assert row.email == 'john.smith@example.com'
        assert 'email' in row.normalized_fields

    def test_reject_normalization_keeps_original(self, seeded_batch, temp_db):
        """Test that reject_normalization keeps original value."""
        database_url, contact_id, batch_id = seeded_batch

        Session = sessionmaker(bind=temp_db[1])
        session = Session()

        norm_item = ReviewItem(
            batch_id=batch_id,
            item_type='normalization',
            payload_json={'field': 'email', 'raw_value': 'john@example.com', 'normalized_value': 'JOHN@EXAMPLE.COM'},
        )
        session.add(norm_item)
        session.flush()

        decision = ReviewDecision(
            batch_id=batch_id,
            review_item_id=norm_item.id,
            decision='reject_normalization',
        )
        session.add(decision)
        session.commit()
        session.close()

        result = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})
        row = result.export_rows[0]

        assert row.email == 'john@example.com'
        assert 'email' not in row.normalized_fields

    def test_defer_normalization_keeps_original_and_warns(self, seeded_batch, temp_db):
        """Test that defer normalization keeps original and adds warning."""
        database_url, contact_id, batch_id = seeded_batch

        Session = sessionmaker(bind=temp_db[1])
        session = Session()

        norm_item = ReviewItem(
            batch_id=batch_id,
            item_type='normalization',
            payload_json={'field': 'email', 'raw_value': 'john@example.com', 'normalized_value': 'john.smith@example.com'},
        )
        session.add(norm_item)
        session.flush()

        decision = ReviewDecision(
            batch_id=batch_id,
            review_item_id=norm_item.id,
            decision='defer',
            reviewed_values={'field': 'email'},
        )
        session.add(decision)
        session.commit()
        session.close()

        result = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})
        row = result.export_rows[0]

        assert row.email == 'john@example.com'
        assert any('normalization deferred' in w.lower() for w in row.normalization_warnings)

    def test_pending_normalization_keeps_original_and_warns(self, seeded_batch, temp_db):
        """Test that pending normalization keeps original and adds warning."""
        database_url, contact_id, batch_id = seeded_batch

        Session = sessionmaker(bind=temp_db[1])
        session = Session()

        norm_item = ReviewItem(
            batch_id=batch_id,
            item_type='normalization',
            payload_json={'field': 'email', 'raw_value': 'john@example.com', 'normalized_value': 'john.smith@example.com'},
        )
        session.add(norm_item)
        session.commit()
        session.close()

        result = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})
        row = result.export_rows[0]

        assert row.email == 'john@example.com'
        assert any('unresolved' in w.lower() for w in row.normalization_warnings)


class TestExportPreviewValidationDecisions:
    """Test validation decision interpretation."""

    def test_accept_issue_removes_blocker(self, seeded_batch, temp_db):
        """Test that accept_issue removes blocker status."""
        database_url, contact_id, batch_id = seeded_batch

        Session = sessionmaker(bind=temp_db[1])
        session = Session()

        val_item = ReviewItem(
            batch_id=batch_id,
            item_type='validation',
            payload_json={'issue_type': 'missing_email'},
        )
        session.add(val_item)
        session.flush()

        decision = ReviewDecision(
            batch_id=batch_id,
            review_item_id=val_item.id,
            decision='accept_issue',
        )
        session.add(decision)
        session.commit()
        session.close()

        result = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})
        row = result.export_rows[0]

        assert row.validation_status == 'accepted'
        assert not row.export_blocked

    def test_dismiss_issue_removes_blocker(self, seeded_batch, temp_db):
        """Test that dismiss_issue removes blocker status."""
        database_url, contact_id, batch_id = seeded_batch

        Session = sessionmaker(bind=temp_db[1])
        session = Session()

        val_item = ReviewItem(
            batch_id=batch_id,
            item_type='validation',
            payload_json={'issue_type': 'missing_email'},
        )
        session.add(val_item)
        session.flush()

        decision = ReviewDecision(
            batch_id=batch_id,
            review_item_id=val_item.id,
            decision='dismiss_issue',
        )
        session.add(decision)
        session.commit()
        session.close()

        result = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})
        row = result.export_rows[0]

        assert row.validation_status == 'dismissed'
        assert not row.export_blocked

    def test_defer_validation_adds_warning(self, seeded_batch, temp_db):
        """Test that defer validation adds warning."""
        database_url, contact_id, batch_id = seeded_batch

        Session = sessionmaker(bind=temp_db[1])
        session = Session()

        val_item = ReviewItem(
            batch_id=batch_id,
            item_type='validation',
            payload_json={'issue_type': 'invalid_email'},
        )
        session.add(val_item)
        session.flush()

        decision = ReviewDecision(
            batch_id=batch_id,
            review_item_id=val_item.id,
            decision='defer',
        )
        session.add(decision)
        session.commit()
        session.close()

        result = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})
        row = result.export_rows[0]

        assert row.validation_status == 'deferred'
        assert any('unresolved' in w.lower() for w in row.export_warnings)

    def test_pending_critical_validation_creates_blocker(self, seeded_batch, temp_db):
        """Test that pending critical validation creates blocker."""
        database_url, contact_id, batch_id = seeded_batch

        Session = sessionmaker(bind=temp_db[1])
        session = Session()

        val_item = ReviewItem(
            batch_id=batch_id,
            item_type='validation',
            payload_json={'issue_type': 'missing_email'},
        )
        session.add(val_item)
        session.commit()
        session.close()

        result = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})
        row = result.export_rows[0]

        assert row.validation_status == 'blocked'
        assert row.export_blocked
        assert len(result.blockers) > 0

    def test_pending_advisory_validation_creates_warning(self, seeded_batch, temp_db):
        """Test that pending advisory validation creates warning."""
        database_url, contact_id, batch_id = seeded_batch

        Session = sessionmaker(bind=temp_db[1])
        session = Session()

        val_item = ReviewItem(
            batch_id=batch_id,
            item_type='validation',
            payload_json={'issue_type': 'suspicious_pattern'},
        )
        session.add(val_item)
        session.commit()
        session.close()

        result = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})
        row = result.export_rows[0]

        assert row.validation_status == 'pending'
        assert not row.export_blocked
        assert any('unresolved' in w.lower() for w in row.export_warnings)


class TestExportPreviewDuplicateDecisions:
    """Test duplicate decision interpretation."""

    def test_same_person_creates_derived_group_id(self, seeded_batch, temp_db):
        """Test that same_person decision creates derived group ID."""
        database_url, contact_id, batch_id = seeded_batch

        Session = sessionmaker(bind=temp_db[1])
        session = Session()

        dup_item = ReviewItem(
            batch_id=batch_id,
            item_type='duplicate',
            payload_json={'candidate_contact_ids': [contact_id, contact_id + 1]},
        )
        session.add(dup_item)
        session.flush()

        decision = ReviewDecision(
            batch_id=batch_id,
            review_item_id=dup_item.id,
            decision='same_person',
            reviewed_values={'candidate_contact_ids': [contact_id, contact_id + 1]},
        )
        session.add(decision)
        session.commit()
        session.close()

        result = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})
        row = result.export_rows[0]

        assert row.duplicate_group_id is not None
        assert row.duplicate_group_id.startswith('DUP-GROUP-')
        assert row.duplicate_decision == 'same_person'

    def test_different_people_creates_no_group(self, seeded_batch, temp_db):
        """Test that different_people decision creates no group."""
        database_url, contact_id, batch_id = seeded_batch

        Session = sessionmaker(bind=temp_db[1])
        session = Session()

        dup_item = ReviewItem(
            batch_id=batch_id,
            item_type='duplicate',
            payload_json={},
        )
        session.add(dup_item)
        session.flush()

        decision = ReviewDecision(
            batch_id=batch_id,
            review_item_id=dup_item.id,
            decision='different_people',
        )
        session.add(decision)
        session.commit()
        session.close()

        result = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})
        row = result.export_rows[0]

        assert row.duplicate_group_id is None
        assert row.duplicate_decision == 'different_people'

    def test_defer_duplicate_creates_warning(self, seeded_batch, temp_db):
        """Test that defer duplicate creates warning."""
        database_url, contact_id, batch_id = seeded_batch

        Session = sessionmaker(bind=temp_db[1])
        session = Session()

        dup_item = ReviewItem(
            batch_id=batch_id,
            item_type='duplicate',
            payload_json={},
        )
        session.add(dup_item)
        session.flush()

        decision = ReviewDecision(
            batch_id=batch_id,
            review_item_id=dup_item.id,
            decision='defer',
        )
        session.add(decision)
        session.commit()
        session.close()

        result = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})
        row = result.export_rows[0]

        assert row.duplicate_decision == 'deferred'
        assert any('unresolved' in w.lower() for w in row.duplicate_warnings)


class TestExportPreviewHouseholdDecisions:
    """Test household decision interpretation."""

    def test_confirm_household_creates_derived_label(self, seeded_batch, temp_db):
        """Test that confirm_household creates derived household label/group."""
        database_url, contact_id, batch_id = seeded_batch

        Session = sessionmaker(bind=temp_db[1])
        session = Session()

        hh_item = ReviewItem(
            batch_id=batch_id,
            item_type='household',
            payload_json={'candidate_contact_ids': [contact_id]},
        )
        session.add(hh_item)
        session.flush()

        decision = ReviewDecision(
            batch_id=batch_id,
            review_item_id=hh_item.id,
            decision='confirm_household',
            reviewed_values={
                'candidate_household_id': 'HH-123',
                'suggested_household_label': 'Smith Household',
                'candidate_contact_ids': [contact_id],
            },
        )
        session.add(decision)
        session.commit()
        session.close()

        result = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})
        row = result.export_rows[0]

        assert row.household_group_id == 'HH-123'
        assert row.household_group_label == 'Smith Household'
        assert row.household_decision == 'confirmed'

    def test_reject_household_creates_no_group(self, seeded_batch, temp_db):
        """Test that reject_household creates no household grouping."""
        database_url, contact_id, batch_id = seeded_batch

        Session = sessionmaker(bind=temp_db[1])
        session = Session()

        hh_item = ReviewItem(
            batch_id=batch_id,
            item_type='household',
            payload_json={},
        )
        session.add(hh_item)
        session.flush()

        decision = ReviewDecision(
            batch_id=batch_id,
            review_item_id=hh_item.id,
            decision='reject_household',
        )
        session.add(decision)
        session.commit()
        session.close()

        result = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})
        row = result.export_rows[0]

        assert row.household_group_id is None
        assert row.household_group_label is None
        assert row.household_decision == 'rejected'

    def test_defer_household_creates_warning(self, seeded_batch, temp_db):
        """Test that defer household creates warning."""
        database_url, contact_id, batch_id = seeded_batch

        Session = sessionmaker(bind=temp_db[1])
        session = Session()

        hh_item = ReviewItem(
            batch_id=batch_id,
            item_type='household',
            payload_json={},
        )
        session.add(hh_item)
        session.flush()

        decision = ReviewDecision(
            batch_id=batch_id,
            review_item_id=hh_item.id,
            decision='defer',
        )
        session.add(decision)
        session.commit()
        session.close()

        result = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})
        row = result.export_rows[0]

        assert row.household_decision == 'deferred'
        assert any('unresolved' in w.lower() for w in row.household_warnings)


class TestExportPreviewReadiness:
    """Test export readiness status."""

    def test_blocker_count_is_correct(self, seeded_batch, temp_db):
        """Test that blocker count is calculated correctly."""
        database_url, contact_id, batch_id = seeded_batch

        Session = sessionmaker(bind=temp_db[1])
        session = Session()

        val_item = ReviewItem(
            batch_id=batch_id,
            item_type='validation',
            payload_json={'issue_type': 'missing_email'},
        )
        session.add(val_item)
        session.commit()
        session.close()

        result = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})

        assert result.blocked_count == 1

    def test_warning_count_is_correct(self, seeded_batch, temp_db):
        """Test that warning count is calculated correctly."""
        database_url, contact_id, batch_id = seeded_batch

        Session = sessionmaker(bind=temp_db[1])
        session = Session()

        val_item = ReviewItem(
            batch_id=batch_id,
            item_type='validation',
            payload_json={'issue_type': 'suspicious_pattern'},
        )
        session.add(val_item)
        session.commit()
        session.close()

        result = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})

        assert result.warning_count > 0

    def test_is_export_ready_false_when_blockers_exist(self, seeded_batch, temp_db):
        """Test that is_export_ready is false when blockers exist."""
        database_url, contact_id, batch_id = seeded_batch

        Session = sessionmaker(bind=temp_db[1])
        session = Session()

        val_item = ReviewItem(
            batch_id=batch_id,
            item_type='validation',
            payload_json={'issue_type': 'missing_email'},
        )
        session.add(val_item)
        session.commit()
        session.close()

        result = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})

        assert result.is_export_ready is False

    def test_is_export_ready_true_when_no_blockers(self, seeded_batch):
        """Test that is_export_ready is true when no blockers exist."""
        database_url, contact_id, batch_id = seeded_batch

        result = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})

        assert result.is_export_ready is True


class TestExportPreviewMalformedPayloads:
    """Test handling of malformed decision/review payloads."""

    def test_malformed_decision_produces_warning_not_error(self, seeded_batch, temp_db):
        """Test that malformed decision payload produces warning rather than error."""
        database_url, contact_id, batch_id = seeded_batch

        Session = sessionmaker(bind=temp_db[1])
        session = Session()

        norm_item = ReviewItem(
            batch_id=batch_id,
            item_type='normalization',
            payload_json={'invalid': 'structure'},  # Missing required fields
        )
        session.add(norm_item)
        session.flush()

        decision = ReviewDecision(
            batch_id=batch_id,
            review_item_id=norm_item.id,
            decision='accept_normalization',
            reviewed_values={'invalid': 'structure'},
        )
        session.add(decision)
        session.commit()
        session.close()

        # Should not raise an error
        result = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})
        row = result.export_rows[0]

        # Original value should be preserved
        assert row.email == 'john@example.com'


class TestExportPreviewDeferredHouseholds:
    """Test deferred household counting and tracking."""

    def test_deferred_household_count_zero_if_all_confirmed(self, seeded_batch, temp_db):
        """Test that deferred_household_count is 0 when all household decisions are confirmed."""
        database_url, contact_id, batch_id = seeded_batch

        Session = sessionmaker(bind=temp_db[1])
        session = Session()

        # Create household review item
        hh_item = ReviewItem(
            batch_id=batch_id,
            item_type='household',
            payload_json={'suggested_label': 'Smith Family', 'basis': 'shared_address'},
        )
        session.add(hh_item)
        session.flush()

        # Create confirm_household decision
        decision = ReviewDecision(
            batch_id=batch_id,
            review_item_id=hh_item.id,
            decision='confirm_household',
            reviewed_values={'candidate_household_id': 'HH-001', 'candidate_contact_ids': [contact_id]},
        )
        session.add(decision)
        session.commit()
        session.close()

        result = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})

        assert result.deferred_household_count == 0

    def test_deferred_household_count_matches_defer_decisions(self, seeded_batch, temp_db):
        """Test that deferred_household_count counts household items with defer decisions."""
        database_url, contact_id, batch_id = seeded_batch

        Session = sessionmaker(bind=temp_db[1])
        session = Session()

        # Create household review item
        hh_item = ReviewItem(
            batch_id=batch_id,
            item_type='household',
            payload_json={'suggested_label': 'Smith Family', 'basis': 'shared_address'},
        )
        session.add(hh_item)
        session.flush()

        # Create defer decision
        decision = ReviewDecision(
            batch_id=batch_id,
            review_item_id=hh_item.id,
            decision='defer',
        )
        session.add(decision)
        session.commit()
        session.close()

        result = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})

        assert result.deferred_household_count == 1

    def test_deferred_household_count_with_no_decisions(self, seeded_batch, temp_db):
        """Test that household items with no decisions count as deferred."""
        database_url, contact_id, batch_id = seeded_batch

        Session = sessionmaker(bind=temp_db[1])
        session = Session()

        # Create household review item without a decision
        hh_item = ReviewItem(
            batch_id=batch_id,
            item_type='household',
            payload_json={'suggested_label': 'Smith Family', 'basis': 'shared_address'},
        )
        session.add(hh_item)
        session.commit()
        session.close()

        result = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})

        assert result.deferred_household_count == 1

    def test_deferred_household_count_with_mixed_decisions(self, seeded_batch, temp_db):
        """Test deferred count with mixed household decisions (confirmed, rejected, deferred)."""
        database_url, contact_id, batch_id = seeded_batch

        Session = sessionmaker(bind=temp_db[1])
        session = Session()

        # Create first household item with confirm decision (counts as 0)
        hh_item1 = ReviewItem(
            batch_id=batch_id,
            item_type='household',
            payload_json={'suggested_label': 'Smith Family', 'basis': 'shared_address'},
        )
        session.add(hh_item1)
        session.flush()

        decision1 = ReviewDecision(
            batch_id=batch_id,
            review_item_id=hh_item1.id,
            decision='confirm_household',
            reviewed_values={'candidate_household_id': 'HH-001', 'candidate_contact_ids': [contact_id]},
        )
        session.add(decision1)

        # Create second household item with reject decision (counts as 0)
        hh_item2 = ReviewItem(
            batch_id=batch_id,
            item_type='household',
            payload_json={'suggested_label': 'Other Family', 'basis': 'shared_name'},
        )
        session.add(hh_item2)
        session.flush()

        decision2 = ReviewDecision(
            batch_id=batch_id,
            review_item_id=hh_item2.id,
            decision='reject_household',
        )
        session.add(decision2)

        # Create third household item with defer decision (counts as 1)
        hh_item3 = ReviewItem(
            batch_id=batch_id,
            item_type='household',
            payload_json={'suggested_label': 'Third Family', 'basis': 'shared_phone'},
        )
        session.add(hh_item3)
        session.flush()

        decision3 = ReviewDecision(
            batch_id=batch_id,
            review_item_id=hh_item3.id,
            decision='defer',
        )
        session.add(decision3)

        # Create fourth household item with no decision (counts as 1)
        hh_item4 = ReviewItem(
            batch_id=batch_id,
            item_type='household',
            payload_json={'suggested_label': 'Fourth Family', 'basis': 'shared_email'},
        )
        session.add(hh_item4)
        session.commit()
        session.close()

        result = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})

        assert result.deferred_household_count == 2  # One defer decision + one no decision


class TestExportPreviewValidationPayloadFormats:
    """Test validation blocker detection with real and legacy payload formats."""

    def test_validation_blocker_detected_with_real_ingestion_payload(self, seeded_batch, temp_db):
        """Real ingestion format with 'issue' field should be detected as blocker."""
        database_url, contact_id, batch_id = seeded_batch

        Session = sessionmaker(bind=temp_db[1])
        session = Session()

        # Real ingestion format with 'issue' field (not 'issue_type')
        val_item = ReviewItem(
            batch_id=batch_id,
            item_type='validation',
            payload_json={
                'field': 'email',
                'issue': 'missing_email',  # Real ingestion format
                'suggestion': None,
                'validation_tier': 'critical'
            },
        )
        session.add(val_item)
        session.commit()
        session.close()

        result = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})
        row = result.export_rows[0]

        assert row.validation_status == 'blocked'
        assert row.export_blocked
        assert len(result.blockers) > 0

    def test_validation_resolved_with_real_ingestion_payload(self, seeded_batch, temp_db):
        """Real ingestion format with decision should not block."""
        database_url, contact_id, batch_id = seeded_batch

        Session = sessionmaker(bind=temp_db[1])
        session = Session()

        val_item = ReviewItem(
            batch_id=batch_id,
            item_type='validation',
            payload_json={
                'field': 'email',
                'issue': 'missing_email',  # Real ingestion format
                'suggestion': None,
                'validation_tier': 'critical'
            },
        )
        session.add(val_item)
        session.flush()

        # Accept the issue
        decision = ReviewDecision(
            batch_id=batch_id,
            review_item_id=val_item.id,
            decision='accept_issue',
        )
        session.add(decision)
        session.commit()
        session.close()

        result = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})
        row = result.export_rows[0]

        assert row.validation_status == 'accepted'
        assert not row.export_blocked

    def test_validation_blocker_detected_with_legacy_format(self, seeded_batch, temp_db):
        """Legacy test format with 'issue_type' field still works (backward compat)."""
        database_url, contact_id, batch_id = seeded_batch

        Session = sessionmaker(bind=temp_db[1])
        session = Session()

        # Legacy format with 'issue_type' field
        val_item = ReviewItem(
            batch_id=batch_id,
            item_type='validation',
            payload_json={'issue_type': 'invalid_email'},  # Legacy format
        )
        session.add(val_item)
        session.commit()
        session.close()

        result = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})
        row = result.export_rows[0]

        assert row.validation_status == 'blocked'
        assert row.export_blocked
        assert len(result.blockers) > 0

    def test_validation_unknown_payload_handled_safely(self, seeded_batch, temp_db):
        """Unknown payload format should not crash."""
        database_url, contact_id, batch_id = seeded_batch

        Session = sessionmaker(bind=temp_db[1])
        session = Session()

        # Empty/unknown payload
        val_item = ReviewItem(
            batch_id=batch_id,
            item_type='validation',
            payload_json={},  # No issue or issue_type field
        )
        session.add(val_item)
        session.commit()
        session.close()

        # Should not crash
        result = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})
        row = result.export_rows[0]

        # Unknown issue type should not be treated as critical blocker
        assert row.validation_status == 'pending'
        assert not row.export_blocked
