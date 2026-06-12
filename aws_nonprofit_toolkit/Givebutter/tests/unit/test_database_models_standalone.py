"""
Standalone tests for database models (no pytest conftest dependency).

Verifies that Option C database models (polymorphic review-items with subject references)
are correctly defined and isolated.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.householder.database_models import (
    Base,
    ImportBatch,
    RawImportRow,
    ImportContact,
    ReviewItem,
    ReviewItemSubject,
    ReviewDecision,
    AuditLogRecord,
)


def test_all_models_exist():
    """Verify all model classes exist (Option C: 7 models)."""
    models = [
        ImportBatch, RawImportRow, ImportContact,
        ReviewItem, ReviewItemSubject, ReviewDecision, AuditLogRecord
    ]
    for model in models:
        assert model is not None, f"{model.__name__} is None"
        assert hasattr(model, '__tablename__'), f"{model.__name__} has no __tablename__"
    print("✓ All 7 Option C models exist with correct structure")


def test_typed_suggestion_models_removed():
    """Verify that old typed suggestion models no longer exist."""
    import scripts.householder.database_models as db_module
    assert not hasattr(db_module, 'NormalizationSuggestion'), "NormalizationSuggestion should be removed"
    assert not hasattr(db_module, 'DuplicateCandidateRecord'), "DuplicateCandidateRecord should be removed"
    assert not hasattr(db_module, 'HouseholdSuggestion'), "HouseholdSuggestion should be removed"
    print("✓ Old typed suggestion models removed")


def test_table_names():
    """Verify table names are correct (Option C: 7 tables)."""
    expected = {
        ImportBatch: 'import_batches',
        RawImportRow: 'raw_import_rows',
        ImportContact: 'import_contacts',
        ReviewItem: 'review_items',
        ReviewItemSubject: 'review_item_subjects',
        ReviewDecision: 'review_decisions',
        AuditLogRecord: 'audit_log',
    }
    for model, table_name in expected.items():
        assert model.__tablename__ == table_name, \
            f"{model.__name__} table name is {model.__tablename__}, expected {table_name}"
    print("✓ All 7 table names correct")


def test_review_item_columns():
    """Verify ReviewItem has all required columns."""
    required_columns = [
        'id', 'batch_id', 'item_type', 'status', 'confidence', 'payload_json', 'created_at'
    ]
    for col in required_columns:
        assert hasattr(ReviewItem, col), f"ReviewItem missing column: {col}"
    print("✓ ReviewItem has all required columns")


def test_review_item_subject_columns():
    """Verify ReviewItemSubject has all required columns."""
    required_columns = [
        'id', 'review_item_id', 'subject_type', 'subject_id', 'role', 'created_at'
    ]
    for col in required_columns:
        assert hasattr(ReviewItemSubject, col), f"ReviewItemSubject missing column: {col}"
    print("✓ ReviewItemSubject has all required columns")


def test_review_decision_columns():
    """Verify ReviewDecision references review_items (not decision_type/target_id)."""
    assert hasattr(ReviewDecision, 'review_item_id'), "ReviewDecision should reference review_items"
    assert not hasattr(ReviewDecision, 'target_id'), "ReviewDecision should not have target_id"
    assert not hasattr(ReviewDecision, 'decision_type'), "ReviewDecision should not have decision_type"
    assert hasattr(ReviewDecision, 'decision'), "ReviewDecision should have decision"
    print("✓ ReviewDecision references review_items correctly")


def test_audit_log_columns():
    """Verify AuditLogRecord references review_items (not target_type/target_id)."""
    assert hasattr(AuditLogRecord, 'item_id'), "AuditLogRecord should reference review_items"
    assert not hasattr(AuditLogRecord, 'target_type'), "AuditLogRecord should not have target_type"
    assert not hasattr(AuditLogRecord, 'target_id'), "AuditLogRecord should not have target_id"
    assert hasattr(AuditLogRecord, 'action_type'), "AuditLogRecord should have action_type"
    print("✓ AuditLogRecord references review_items correctly")


def test_polymorphic_subject_types_documented():
    """Verify ReviewItemSubject docstring documents Phase 1B and future subject_type values."""
    docstring = ReviewItemSubject.__doc__
    assert docstring is not None, "ReviewItemSubject should have docstring"
    assert 'import_raw_row' in docstring, "Phase 1B subject_type should be documented"
    assert 'import_contact_snapshot' in docstring, "Phase 1B subject_type should be documented"
    assert 'prior_import_row' in docstring, "Future subject_type should be documented"
    assert 'existing_contact' in docstring, "Future subject_type should be documented"
    assert 'existing_household' in docstring, "Future subject_type should be documented"
    print("✓ Polymorphic subject_types documented in docstring")


def test_models_not_imported_by_services():
    """Verify database models are not imported by services."""
    import_service_path = Path(__file__).resolve().parents[2] / \
        'scripts/householder/import_service.py'
    source = import_service_path.read_text()
    assert 'database_models' not in source, \
        "import_service should not import database_models"
    print("✓ Database models not imported by services")


def test_models_not_imported_by_app():
    """Verify database models are not imported by Flask app."""
    app_path = Path(__file__).resolve().parents[2] / \
        'scripts/uploader/app.py'
    source = app_path.read_text()
    assert 'database_models' not in source, \
        "app.py should not import database_models"
    print("✓ Database models not imported by app.py")


def test_base_metadata():
    """Verify Base.metadata includes all 7 models."""
    table_names = {table.name for table in Base.metadata.tables.values()}
    expected_tables = {
        'import_batches',
        'raw_import_rows',
        'import_contacts',
        'review_items',
        'review_item_subjects',
        'review_decisions',
        'audit_log',
    }
    assert expected_tables.issubset(table_names), \
        f"Base.metadata missing tables. Has: {table_names}, expected: {expected_tables}"
    assert len(table_names) >= len(expected_tables), \
        f"Base.metadata has wrong count. Has: {len(table_names)}, expected: {len(expected_tables)}"
    print(f"✓ Base.metadata has all {len(expected_tables)} expected tables")


def test_migration_file_exists():
    """Verify migration file exists."""
    versions_dir = Path(__file__).resolve().parents[2] / 'alembic/versions'
    migration_files = [f for f in versions_dir.glob('*.py') if not f.name.startswith('_')]
    assert len(migration_files) >= 1, "No migration files found"
    print(f"✓ Migration file exists: {migration_files[0].name}")


def test_models_use_pure_sqlalchemy():
    """Verify models use pure SQLAlchemy."""
    db_models_path = Path(__file__).resolve().parents[2] / \
        'scripts/householder/database_models.py'
    source = db_models_path.read_text()
    assert 'flask_sqlalchemy' not in source.lower(), \
        "database_models should use pure SQLAlchemy, not Flask-SQLAlchemy"
    print("✓ Models use pure SQLAlchemy (no Flask-SQLAlchemy coupling)")


def test_database_repository_exists_and_isolated():
    """Verify DatabaseImportRepository exists and is isolated from routes/services."""
    # Verify class exists
    from scripts.householder.database_repository import DatabaseImportRepository
    assert DatabaseImportRepository is not None
    assert hasattr(DatabaseImportRepository, 'list_imports')

    # Verify it's not imported by routes
    app_source = Path(__file__).resolve().parents[2] / 'scripts/uploader/app.py'
    app_content = app_source.read_text()
    assert 'DatabaseImportRepository' not in app_content, \
        "Routes should not import DatabaseImportRepository yet"

    # Verify it's not imported by services
    duplicates_service = Path(__file__).resolve().parents[2] / 'scripts/householder/duplicates_service.py'
    service_content = duplicates_service.read_text()
    assert 'DatabaseImportRepository' not in service_content, \
        "Services should not import DatabaseImportRepository yet"

    print("✓ DatabaseImportRepository exists and is properly isolated")


def run_all_tests():
    """Run all tests."""
    tests = [
        test_all_models_exist,
        test_typed_suggestion_models_removed,
        test_table_names,
        test_review_item_columns,
        test_review_item_subject_columns,
        test_review_decision_columns,
        test_audit_log_columns,
        test_polymorphic_subject_types_documented,
        test_models_not_imported_by_services,
        test_models_not_imported_by_app,
        test_base_metadata,
        test_migration_file_exists,
        test_models_use_pure_sqlalchemy,
        test_no_database_repository_exists,
    ]

    print("\n=== Option C Database Models Tests (Polymorphic Review-Items) ===\n")
    failed = 0
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n=== Results ===")
    passed = len(tests) - failed
    print(f"Passed: {passed}/{len(tests)}")
    if failed == 0:
        print("All tests passed! ✓")
    else:
        print(f"Failed: {failed}")
        sys.exit(1)


if __name__ == '__main__':
    run_all_tests()
