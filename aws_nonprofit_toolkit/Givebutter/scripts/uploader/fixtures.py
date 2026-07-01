"""
DonorTrust v1 Phase 0 Fixture Data

Provides mock data for clickable prototype of all 8 screens.
No database, no persistence, no real logic.
"""

from datetime import datetime, timedelta
from uuid import uuid4

# ============================================================================
# IMPORT BATCH
# ============================================================================

IMPORT_BATCH = {
    'id': 'IMP-2025-0101-A',
    'filename': 'donors_q1_2025.csv',
    'uploaded_at': datetime.now() - timedelta(days=2),
    'record_count': 50,
    'status': 'In Review',
    'progress': 42,  # 42% complete
    'duplicates_pending': 3,
    'validation_issues': 8,
    'normalizations_pending': 6,
    'households_pending': 5,
}

# ============================================================================
# SAMPLE CONTACTS (for All Records / Validation Review)
# ============================================================================

CONTACTS = [
    {
        'id': 'TXN-001',
        'date': '2026-05-15',
        'name': 'John Smith',
        'email': 'john@example.com',
        'phone': '(415) 555-1234',
        'amount': '$500.00',
        'address': '123 Main St, Springfield, IL 62701',
        'issue_type': 'format-invalid',
        'issue_description': 'Phone number format invalid',
        'issue_field': 'phone',
    },
    {
        'id': 'TXN-002',
        'date': '2026-05-16',
        'name': 'Jane Doe',
        'email': 'jane.doe@email.com',
        'phone': '(415) 555-5678',
        'amount': '$1,250.00',
        'address': '456 Oak Ave, Springfield, IL 62702',
        'issue_type': 'missing-required',
        'issue_description': 'Missing campaign field',
    },
    {
        'id': 'TXN-003',
        'date': '2026-05-17',
        'name': 'Robert Smith',
        'email': 'rsmith@email.com',
        'phone': '(415) 555-1234',
        'amount': '$250.00',
        'address': '789 Elm St, Springfield IL',
        'issue_type': 'format-invalid',
        'issue_description': 'Address incomplete (missing ZIP)',
    },
    {
        'id': 'TXN-004',
        'date': '2026-05-18',
        'name': 'Mary Johnson',
        'email': 'mary.j@company.org',
        'phone': '(415) 555-9999',
        'amount': '$750.00',
        'address': '321 Pine Rd, Springfield, IL 62703',
        'issue_type': None,
        'issue_description': None,
    },
    {
        'id': 'TXN-005',
        'date': '2026-05-19',
        'name': 'Michael Brown',
        'email': 'mbrown@email.com',
        'phone': '(415) 555-8765',
        'amount': '$2,000.00',
        'address': '654 Maple Dr, Springfield, IL 62704',
        'issue_type': 'missing-required',
        'issue_description': 'Phone number missing',
        'issue_field': 'phone',
    },
]

# ============================================================================
# DUPLICATE CANDIDATES (for Possible Duplicates)
# ============================================================================

DUPLICATE_CANDIDATES = [
    {
        'id': 'DUP-001',
        'contact_a': {
            'id': 'P-001',
            'name': 'John Smith',
            'email': 'john@example.com',
            'phone': '(415) 555-1234',
            'address': '123 Main St, Springfield, IL 62701',
        },
        'contact_b': {
            'id': 'P-006',
            'name': 'John Smith',
            'email': 'jsmith@email.com',
            'phone': '(415) 555-1234',
            'address': '123 Main Street, Springfield, IL 62701',
        },
        'supporting_evidence': [
            'Full name match',
            'Phone match',
            'Address match (minor formatting)',
        ],
        'conflicting_evidence': [
            'Different email addresses',
        ],
        'status': 'Pending',
    },
    {
        'id': 'DUP-002',
        'contact_a': {
            'id': 'P-003',
            'name': 'robert smith',
            'email': 'rsmith@email.com',
            'phone': '(415) 555-1234',
            'address': '789 Elm St, Springfield IL',
        },
        'contact_b': {
            'id': 'P-007',
            'name': 'Robert Smith',
            'email': 'rsmith@email.com',
            'phone': '(415) 555-1234',
            'address': '789 Elm Street, Springfield, IL 62705',
        },
        'supporting_evidence': [
            'Full name match',
            'Email match',
            'Phone match',
            'Address match',
        ],
        'conflicting_evidence': [],
        'status': 'Pending',
    },
    {
        'id': 'DUP-003',
        'contact_a': {
            'id': 'P-008',
            'name': 'Sarah Williams',
            'email': 'sarahw@example.com',
            'phone': '(555) 666-7777',
            'address': '999 Cedar Ln, Springfield, IL 62706',
        },
        'contact_b': {
            'id': 'P-009',
            'name': 'Sara Williams',
            'email': 'sara.williams@email.com',
            'phone': '(555) 666-7777',
            'address': '999 Cedar Lane, Springfield, IL 62706',
        },
        'supporting_evidence': [
            'Similar name (Sara vs Sarah)',
            'Phone match',
            'Address match',
        ],
        'conflicting_evidence': [
            'Different email addresses',
            'Spelling variation in first name',
        ],
        'status': 'Pending',
    },
]

# ============================================================================
# NORMALIZATION SUGGESTIONS (for Normalization Review)
# ============================================================================

NORMALIZATION_SUGGESTIONS = [
    {
        'id': 'NORM-001',
        'contact_name': 'John Smith',
        'field_name': 'Name',
        'original_value': 'john smith',
        'suggested_value': 'John Smith',
        'normalization_type': 'Capitalization Fix',
        'status': 'Pending',
    },
    {
        'id': 'NORM-002',
        'contact_name': 'Robert Smith',
        'field_name': 'Phone',
        'original_value': '415-555-1234',
        'suggested_value': '(415) 555-1234',
        'normalization_type': 'Format Standardization',
        'status': 'Pending',
    },
    {
        'id': 'NORM-003',
        'contact_name': 'Jane Doe',
        'field_name': 'Email',
        'original_value': 'jane.doe@email.com',
        'suggested_value': 'jane.doe@email.com',
        'normalization_type': 'No Change Needed',
        'status': 'Pending',
    },
    {
        'id': 'NORM-004',
        'contact_name': 'Sarah Williams',
        'field_name': 'Address',
        'original_value': '999 Cedar Ln, Springfield, IL 62706',
        'suggested_value': '999 Cedar Lane, Springfield, IL 62706',
        'normalization_type': 'Abbreviation Expansion',
        'status': 'Pending',
    },
    {
        'id': 'NORM-005',
        'contact_name': 'Michael Brown',
        'field_name': 'Name',
        'original_value': 'MICHAEL BROWN',
        'suggested_value': 'Michael Brown',
        'normalization_type': 'Case Normalization',
        'status': 'Pending',
    },
    {
        'id': 'NORM-006',
        'contact_name': 'Mary Johnson',
        'field_name': 'Phone',
        'original_value': '(212) 555-9999',
        'suggested_value': '(212) 555-9999',
        'normalization_type': 'No Change Needed',
        'status': 'Pending',
    },
]

# ============================================================================
# HOUSEHOLD SUGGESTIONS (for Households Review)
# ============================================================================

HOUSEHOLD_SUGGESTIONS = [
    {
        'id': 'HH-001',
        'suggested_name': 'Smith Family',
        'address': '123 Main St, Springfield, IL 62701',
        'confidence': '98%',
        'proposed_members': ['John Smith (TXN-001)', 'Robert Smith (TXN-003)'],
        'evidence': [
            'Shared last name: Smith',
            'Same address: 123 Main St',
            'Email domain patterns match',
            'Phone number prefix matches',
        ],
        'conflicts': [],
        'status': 'Pending',
    },
    {
        'id': 'HH-002',
        'suggested_name': 'Williams Family',
        'address': '999 Cedar Ln, Springfield, IL 62706',
        'confidence': '95%',
        'proposed_members': ['Sarah Williams (P-008)', 'Sara Williams (P-009)'],
        'evidence': [
            'Similar names (Sarah/Sara)',
            'Matching addresses',
            'Matching phone numbers: (555) 666-7777',
            'Same zip code: 62706',
        ],
        'conflicts': ['Email addresses differ: sarahw vs sara.williams'],
        'status': 'Pending',
    },
    {
        'id': 'HH-003',
        'suggested_name': 'Johnson Household',
        'address': '321 Pine Rd, Springfield, IL 62703',
        'confidence': '92%',
        'proposed_members': ['Mary Johnson (TXN-004)'],
        'evidence': [
            'Single contact at address 321 Pine Rd',
            'Phone and email well-formatted',
            'No related records found',
        ],
        'conflicts': [],
        'status': 'Pending',
    },
    {
        'id': 'HH-004',
        'suggested_name': 'Doe Family',
        'address': '456 Oak Ave, Springfield, IL 62702',
        'confidence': '87%',
        'proposed_members': ['Jane Doe (TXN-002)'],
        'evidence': [
            'Single contact at address',
            'No related family members in import batch',
        ],
        'conflicts': [],
        'status': 'Pending',
    },
    {
        'id': 'HH-005',
        'suggested_name': 'Brown Household',
        'address': '654 Maple Dr, Springfield, IL 62704',
        'confidence': '92%',
        'proposed_members': ['Michael Brown (TXN-005)'],
        'evidence': [
            'Single contact at address',
            'Valid contact information',
        ],
        'conflicts': [],
        'status': 'Pending',
    },
]

# ============================================================================
# AUDIT LOG ENTRIES (for Audit Log)
# ============================================================================

AUDIT_LOG_ENTRIES = [
    {
        'timestamp': datetime.now() - timedelta(hours=2),
        'reviewer': 'Sarah Lee',
        'action': 'marked as Same Person',
        'target': '#P-001',
        'notes': 'Email variation consistent with household pattern',
        'audit_status': 'Validation Passed',
    },
    {
        'timestamp': datetime.now() - timedelta(hours=1, minutes=30),
        'reviewer': 'Sarah Lee',
        'action': 'rejected Household Link',
        'target': '#HH-002',
        'notes': 'Different email providers, likely separate individuals',
        'audit_status': 'Needs Review',
    },
    {
        'timestamp': datetime.now() - timedelta(hours=1),
        'reviewer': 'James Martinez',
        'action': 'confirmed Household #HH-001',
        'target': 'HH-001',
        'notes': 'Smith family confirmed via manual lookup',
        'audit_status': 'Validation Passed',
    },
    {
        'timestamp': datetime.now() - timedelta(minutes=45),
        'reviewer': 'Sarah Lee',
        'action': 'deferred normalization decision',
        'target': '#NORM-004',
        'notes': 'Waiting for confirmation from donor before address change',
        'audit_status': 'Needs Review',
    },
    {
        'timestamp': datetime.now() - timedelta(minutes=15),
        'reviewer': 'System',
        'action': 'System Logged batch import',
        'target': IMPORT_BATCH['id'],
        'notes': '50 records imported from donors_q1_2025.csv',
        'audit_status': 'System Logged',
    },
]

# ============================================================================
# EXPORT CARDS (for Export Console)
# ============================================================================

EXPORT_CARDS = [
    {
        'id': 'EXPORT-REVIEWED',
        'name': 'Reviewed Export',
        'status': 'Generated',
        'description': 'CSV reflecting reviewer-confirmed duplicate decisions and household groupings in export staging',
        'files_ready': 1,
        'last_generated': datetime.now() - timedelta(hours=1),
        'size': '8.2 KB',
        'action': 'Download Reviewed CSV',
    },
    {
        'id': 'EXPORT-HOUSEHOLD',
        'name': 'Household Export',
        'status': 'Ready',
        'description': 'Confirmed household groupings with member composition',
        'files_ready': 1,
        'last_generated': datetime.now() - timedelta(hours=1),
        'size': '5.4 KB',
        'action': 'Download Household CSV',
    },
    {
        'id': 'EXPORT-BACKLOG',
        'name': 'Backlog Export',
        'status': 'Pending Review',
        'description': 'Records with unresolved suggestions or pending reviewer decisions',
        'files_ready': 0,
        'last_generated': None,
        'size': '—',
        'caution': 'For internal review only. Contains unresolved suggestions or pending reviewer decisions.',
        'action': 'Download Backlog CSV',
    },
    {
        'id': 'EXPORT-RAW',
        'name': 'Raw Export',
        'status': 'Ready',
        'description': 'Original data unchanged; no reviewer modifications',
        'files_ready': 1,
        'last_generated': datetime.now() - timedelta(hours=2),
        'size': '12.8 KB',
        'caution': 'Original uploaded CSV exactly as received. No reviewer decisions or staged changes included.',
        'action': 'Download Raw CSV',
    },
]

# ============================================================================
# IMPORTS LIST (for /imports and upload page)
# ============================================================================

IMPORTS_LIST = [
    IMPORT_BATCH,
    {
        'id': 'IMP-2024-1201-B',
        'filename': 'donors_q4_2024.csv',
        'uploaded_at': datetime.now() - timedelta(days=30),
        'record_count': 125,
        'status': 'Complete',
        'progress': 100,
    },
    {
        'id': 'IMP-2024-1001-A',
        'filename': 'holiday_campaign_2024.csv',
        'uploaded_at': datetime.now() - timedelta(days=60),
        'record_count': 89,
        'status': 'Complete',
        'progress': 100,
    },
]

# ============================================================================
# QUEUE STATUS SUMMARY (for Import Dashboard)
# ============================================================================

QUEUE_STATUS = {
    'duplicates_pending': 3,
    'validation_issues': 8,
    'normalizations_pending': 6,
    'households_pending': 5,
}


# ============================================================================
# FALLBACK VALIDATION TEST DATA (for test_validation_service.py)
# ============================================================================
# Rows with issue_type=None to test fixture-mode fallback validation logic.
# These are NOT part of the main CONTACTS fixture batch; they're for unit tests only.
# Tests that use these should create their own fixture batch or mock the repository.

NEGATIVE_AMOUNT_ROW = {
    'id': 'TXN-TEST-NEG',
    'date': '2026-05-20',
    'name': 'Test Negative Amount',
    'email': 'valid@example.com',
    'phone': '(415) 555-1234',
    'amount': '-100.00',
    'address': '789 Test St, Springfield, IL 62701',
    'issue_type': None,
    'issue_description': None,
}

INVALID_EMAIL_ROW = {
    'id': 'TXN-TEST-BAD-EMAIL',
    'date': '2026-05-21',
    'name': 'Test Invalid Email',
    'email': 'not-an-email',
    'phone': '(415) 555-1234',
    'amount': '$500.00',
    'address': '790 Test St, Springfield, IL 62701',
    'issue_type': None,
    'issue_description': None,
}

MISSING_AMOUNT_ROW = {
    'id': 'TXN-TEST-NO-AMT',
    'date': '2026-05-22',
    'name': 'Test Missing Amount',
    'email': 'valid@example.com',
    'phone': '(415) 555-1234',
    'amount': '',
    'address': '791 Test St, Springfield, IL 62701',
    'issue_type': None,
    'issue_description': None,
}

VALID_ROW_NO_ISSUE = {
    'id': 'TXN-TEST-VALID',
    'date': '2026-05-23',
    'name': 'Test Valid Row',
    'email': 'valid@example.com',
    'phone': '(415) 555-1234',
    'amount': '$250.00',
    'address': '792 Test St, Springfield, IL 62701',
    'issue_type': None,
    'issue_description': None,
}
