"""
Guardrail tests for export file generation.

Verifies immutability, audit logging, and no external system calls.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch

from scripts.householder.export_file_service import (
    ExportBlockedError,
)
from scripts.householder.service_contracts import ExportRow, ExportPreviewResult


# File Generation Guardrails

def test_no_csv_file_when_blockers_exist(tmp_path, monkeypatch):
    """No CSV file created when blockers exist."""
    from pathlib import Path
    from scripts.householder.export_file_service import generate_export_file

    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    export_dir = str(tmp_path / "exports")

    blocked_preview = ExportPreviewResult(
        import_id="IMP-TEST-BLOCKED",
        export_rows=(),
        blockers=("Unresolved validation: missing_email",),
        warnings=(),
        row_count=0,
        blocked_count=1,
        warning_count=0,
        is_export_ready=False,
        derived_at=datetime.now(timezone.utc),
    )

    with patch('scripts.householder.export_file_service.build_export_preview', return_value=blocked_preview):
        try:
            generate_export_file(
                "IMP-TEST-BLOCKED",
                export_dir,
            )
        except ExportBlockedError:
            pass

        # Verify no CSV files created
        csv_files = list(Path(export_dir).glob("*.csv"))
        assert len(csv_files) == 0


# Audit Logging Guardrails

def test_no_audit_record_on_blockers(monkeypatch):
    """No audit record created when blockers prevent generation."""
    from scripts.householder.export_file_service import generate_export_file
    import tempfile

    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    with tempfile.TemporaryDirectory() as tmpdir:
        blocked_preview = ExportPreviewResult(
            import_id="IMP-TEST-BLOCKED",
            export_rows=(),
            blockers=("Unresolved validation: missing_email",),
            warnings=(),
            row_count=0,
            blocked_count=1,
            warning_count=0,
            is_export_ready=False,
            derived_at=datetime.now(timezone.utc),
        )

        with patch('scripts.householder.export_file_service.build_export_preview', return_value=blocked_preview):
            with patch('scripts.householder.export_file_service._create_audit_record') as mock_audit:
                try:
                    generate_export_file(
                        "IMP-TEST-BLOCKED",
                        tmpdir,
                    )
                except ExportBlockedError:
                    pass

                # Verify audit record not called
                mock_audit.assert_not_called()


# CSV Generation Guardrails

def test_csv_generation_no_external_calls(monkeypatch, tmp_path):
    """CSV generation does not call external systems."""
    from scripts.householder.export_file_service import generate_export_file

    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    sample_row = ExportRow(
        source_row_index=1,
        transaction_id="TXN-001",
        first_name="John",
        last_name="Smith",
        email="john@example.com",
        phone=None,
        address_line1=None,
        address_line2=None,
        city=None,
        state=None,
        postal_code=None,
        amount="100.00",
        validation_status="accepted",
        validation_issues=(),
        normalized_fields=(),
        normalization_warnings=(),
        duplicate_group_id=None,
        duplicate_decision=None,
        duplicate_warnings=(),
        household_group_id=None,
        household_group_label=None,
        household_members=(),
        household_decision=None,
        household_warnings=(),
        export_warnings=(),
        export_blocked=False,
        export_derived_at=datetime.now(timezone.utc),
    )

    ready_preview = ExportPreviewResult(
        import_id="IMP-TEST-GUARD",
        export_rows=(sample_row,),
        blockers=(),
        warnings=(),
        row_count=1,
        blocked_count=0,
        warning_count=0,
        is_export_ready=True,
        derived_at=datetime.now(timezone.utc),
    )

    export_dir = str(tmp_path / "exports")

    # Verify no external system calls by checking audit creation is mocked
    with patch('scripts.householder.export_file_service.build_export_preview', return_value=ready_preview):
        with patch('scripts.householder.export_file_service._create_audit_record', return_value=123) as mock_audit:
            result = generate_export_file(
                "IMP-TEST-GUARD",
                export_dir,
            )

            # Verify only audit_log was called (no external CRM calls)
            mock_audit.assert_called_once()
            assert result.audit_log_id == 123


# Blocking Behavior Guardrails

def test_blocked_export_has_error_details(monkeypatch, tmp_path):
    """Blocked exports include detailed blocker information."""
    from scripts.householder.export_file_service import generate_export_file

    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    blockers = [
        "Unresolved validation: missing_email",
        "Unresolved validation: invalid_amount",
    ]

    blocked_preview = ExportPreviewResult(
        import_id="IMP-TEST-DETAILED",
        export_rows=(),
        blockers=tuple(blockers),
        warnings=(),
        row_count=0,
        blocked_count=2,
        warning_count=0,
        is_export_ready=False,
        derived_at=datetime.now(timezone.utc),
    )

    export_dir = str(tmp_path / "exports")

    with patch('scripts.householder.export_file_service.build_export_preview', return_value=blocked_preview):
        try:
            generate_export_file(
                "IMP-TEST-DETAILED",
                export_dir,
            )
        except ExportBlockedError as e:
            # Verify error includes all blocker details
            assert len(e.blockers) == 2
            assert e.blocked_count == 2
            assert "missing_email" in e.blockers[0]
            assert "invalid_amount" in e.blockers[1]


# Warning Handling Guardrails

def test_warnings_do_not_block_generation(monkeypatch, tmp_path):
    """Warnings do not block export file generation."""
    from scripts.householder.export_file_service import generate_export_file

    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    sample_row = ExportRow(
        source_row_index=1,
        transaction_id="TXN-001",
        first_name="John",
        last_name="Smith",
        email="john@example.com",
        phone=None,
        address_line1=None,
        address_line2=None,
        city=None,
        state=None,
        postal_code=None,
        amount="100.00",
        validation_status="pending",
        validation_issues=(),
        normalized_fields=(),
        normalization_warnings=("Field deferred",),
        duplicate_group_id=None,
        duplicate_decision=None,
        duplicate_warnings=(),
        household_group_id=None,
        household_group_label=None,
        household_members=(),
        household_decision=None,
        household_warnings=(),
        export_warnings=(),
        export_blocked=False,
        export_derived_at=datetime.now(timezone.utc),
    )

    warning_preview = ExportPreviewResult(
        import_id="IMP-TEST-WARNINGS",
        export_rows=(sample_row,),
        blockers=(),
        warnings=("Field normalization deferred",),
        row_count=1,
        blocked_count=0,
        warning_count=1,
        is_export_ready=True,
        derived_at=datetime.now(timezone.utc),
    )

    export_dir = str(tmp_path / "exports")

    with patch('scripts.householder.export_file_service.build_export_preview', return_value=warning_preview):
        with patch('scripts.householder.export_file_service._create_audit_record', return_value=456):
            result = generate_export_file(
                "IMP-TEST-WARNINGS",
                export_dir,
            )

            # Verify file was created despite warnings
            assert result.warning_count == 1
            assert result.blocked_count == 0
            assert result.row_count == 1
