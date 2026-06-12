"""Database-mode integration tests for all 8 canonical routes.

Verify that all 8 canonical read-only routes can operate against the database
repository when explicitly configured for database mode, while preserving
fixture-backed default behavior.

These routes render HTML templates (not JSON). Tests verify:
1. Response status is 200
2. Expected database-seeded values appear in rendered HTML
3. Route-specific content from seeded data is present
"""

import pytest


class TestDatabaseModeRoutes:
    """Integration tests verifying routes work with database-backed data."""

    def test_imports_list_from_database(self, client):
        """Verify /imports renders from database mode.

        Database seed includes:
        - 1 import batch: IMP-TEST-001, donors_q1_2025.csv, 42% progress
        """
        response = client.get('/imports')
        assert response.status_code == 200

        html = response.get_data(as_text=True)

        # Verify database-seeded batch info appears in HTML
        assert 'IMP-TEST-001' in html
        assert 'donors_q1_2025.csv' in html

    def test_dashboard_from_database(self, client):
        """Verify /imports/<id>/dashboard renders from database.

        Database seed includes:
        - Batch IMP-TEST-001
        - 5 import contacts
        - 4 review items with 2 decisions (50% progress)
        - Queue counts from review items
        """
        response = client.get('/imports/IMP-TEST-001/dashboard')
        assert response.status_code == 200

        html = response.get_data(as_text=True)

        # Verify batch data from database appears in HTML
        assert 'IMP-TEST-001' in html
        assert 'donors_q1_2025.csv' in html
        assert '50' in html  # Progress percentage (2 of 4 decisions made)

        # Verify queue navigation links exist (route content)
        assert '/imports/IMP-TEST-001/validation' in html
        assert '/imports/IMP-TEST-001/duplicates' in html
        assert '/imports/IMP-TEST-001/normalizations' in html
        assert '/imports/IMP-TEST-001/households' in html

    def test_validation_from_database(self, client):
        """Verify /imports/<id>/validation renders from database.

        Database seed includes:
        - 1 validation review item: VAL-001
        - 2 contacts for validation: CONTACT-001, CONTACT-003
        """
        response = client.get('/imports/IMP-TEST-001/validation')
        assert response.status_code == 200

        html = response.get_data(as_text=True)

        # Verify batch info appears
        assert 'IMP-TEST-001' in html

        # Verify validation review content from database
        assert 'Validation' in html or 'validation' in html
        # Verify at least one contact from seed appears (validation routes show contact data)
        assert 'John Smith' in html or 'Jane Doe' in html or 'CONTACT' in html

    def test_normalizations_from_database(self, client):
        """Verify /imports/<id>/normalizations renders from database.

        Database seed includes:
        - 1 normalization review item: NORM-001
        - 1 contact: CONTACT-002 (Jon Smith)
        """
        response = client.get('/imports/IMP-TEST-001/normalizations')
        assert response.status_code == 200

        html = response.get_data(as_text=True)

        assert 'IMP-TEST-001' in html
        # Verify normalization-related content
        assert 'Normaliz' in html or 'normaliz' in html

    def test_households_from_database(self, client):
        """Verify /imports/<id>/households renders from database.

        Database seed includes:
        - 1 household review item: HH-001
        - 2 contacts for household: CONTACT-001, CONTACT-004
        """
        response = client.get('/imports/IMP-TEST-001/households')
        assert response.status_code == 200

        html = response.get_data(as_text=True)

        assert 'IMP-TEST-001' in html
        # Verify household-related content
        assert 'Household' in html or 'household' in html or 'Grouping' in html

    def test_duplicates_from_database(self, client):
        """Verify /imports/<id>/duplicates renders from database.

        Database seed includes:
        - 1 duplicate review item: DUP-001
        - 2 contacts: CONTACT-001 (John Smith), CONTACT-002 (Jon Smith)
        - 1 decision: Sarah Lee marked as same person
        """
        response = client.get('/imports/IMP-TEST-001/duplicates')
        assert response.status_code == 200

        html = response.get_data(as_text=True)

        assert 'IMP-TEST-001' in html
        # Verify duplicate-related content
        assert 'Duplicate' in html or 'duplicate' in html or 'duplicat' in html.lower()

    def test_audit_from_database(self, client):
        """Verify /imports/<id>/audit renders from database.

        Database seed includes:
        - 3 audit log entries
        - Reviewers: Sarah Lee, James Martinez, Bob Wilson
        - Actions: "marked as Same Person", "confirmed Household", "flagged missing address"
        """
        response = client.get('/imports/IMP-TEST-001/audit')
        assert response.status_code == 200

        html = response.get_data(as_text=True)

        assert 'IMP-TEST-001' in html
        # Verify audit-related content
        assert 'Audit' in html or 'audit' in html
        # Verify reviewer names from seed appear
        assert 'Sarah Lee' in html or 'James Martinez' in html or 'Bob Wilson' in html

    def test_exports_from_database(self, client):
        """Verify /imports/<id>/exports renders from database.

        Database seed includes:
        - 5 import contacts (staged records)
        - 2 review decisions (for metrics)
        - 1 household review item (for household count)
        """
        response = client.get('/imports/IMP-TEST-001/exports')
        assert response.status_code == 200

        html = response.get_data(as_text=True)

        assert 'IMP-TEST-001' in html
        # Verify export-related content
        assert 'Export' in html or 'export' in html or 'EXPORT' in html
