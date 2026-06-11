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
        'id': 'P-001',
        'transaction_id': 'TXN-2025-001',
        'date': '2025-01-01',
        'name': 'John Smith',
        'email': 'john@example.com',
        'phone': '(555) 123-4567',
        'amount': '$500.00',
        'address': '123 Main St, Springfield, IL 62701',
        'validation_status': 'Validation Passed',  # green
        'action': 'View',
    },
    {
        'id': 'P-002',
        'transaction_id': 'TXN-2025-002',
        'date': '2025-01-02',
        'name': 'Jane Doe',
        'email': 'jane.doe@email.com',
        'phone': '(555) 987-6543',
        'amount': '$1,250.00',
        'address': '456 Oak Ave, Springfield, IL 62702',
        'validation_status': 'Needs Review',  # amber
        'action': 'Review Issues',
    },
    {
        'id': 'P-003',
        'transaction_id': 'TXN-2025-003',
        'date': '2025-01-03',
        'name': 'robert smith',  # case issue
        'email': 'rsmith@email.com',
        'phone': '555-123-4567',  # format issue
        'amount': '$250.00',
        'address': '789 Elm St, Springfield IL',  # incomplete
        'validation_status': 'Conflict Flagged',  # red
        'action': 'Review Issues',
    },
    {
        'id': 'P-004',
        'transaction_id': 'TXN-2025-004',
        'date': '2025-01-04',
        'name': 'Mary Johnson',
        'email': 'mary.j@company.org',
        'phone': '(555) 555-5555',
        'amount': '$750.00',
        'address': '321 Pine Rd, Springfield, IL 62703',
        'validation_status': 'Validation Passed',
        'action': 'View',
    },
    {
        'id': 'P-005',
        'transaction_id': 'TXN-2025-005',
        'date': '2025-01-05',
        'name': 'Michael Brown',
        'email': 'mbrown@email.com',
        'phone': '(555) 444-3333',
        'amount': '$2,000.00',
        'address': '654 Maple Dr, Springfield, IL 62704',
        'validation_status': 'Validation Passed',
        'action': 'View',
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
            'phone': '(555) 123-4567',
            'address': '123 Main St, Springfield, IL 62701',
        },
        'contact_b': {
            'id': 'P-006',
            'name': 'John Smith',
            'email': 'jsmith@email.com',
            'phone': '(555) 123-4567',
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
            'phone': '555-123-4567',
            'address': '789 Elm St, Springfield IL',
        },
        'contact_b': {
            'id': 'P-007',
            'name': 'Robert Smith',
            'email': 'rsmith@email.com',
            'phone': '(555) 123-4567',
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
        'contact_name': 'john smith',
        'field': 'name',
        'current_value': 'john smith',
        'suggested_value': 'John Smith',
        'reason': 'Capitalization standardization',
        'confidence': '99%',
        'status': 'Pending',
    },
    {
        'id': 'NORM-002',
        'contact_name': 'robert smith',
        'field': 'phone',
        'current_value': '555-123-4567',
        'suggested_value': '(555) 123-4567',
        'reason': 'Phone format standardization',
        'confidence': '95%',
        'status': 'Pending',
    },
    {
        'id': 'NORM-003',
        'contact_name': 'Jane Doe',
        'field': 'email',
        'current_value': 'jane.doe@email.com',
        'suggested_value': 'jane.doe@email.com',
        'reason': 'Already normalized',
        'confidence': '100%',
        'status': 'Pending',
    },
    {
        'id': 'NORM-004',
        'contact_name': 'Sarah Williams',
        'field': 'address',
        'current_value': '999 Cedar Ln, Springfield, IL 62706',
        'suggested_value': '999 Cedar Lane, Springfield, IL 62706',
        'reason': 'Address abbreviation expansion',
        'confidence': '92%',
        'status': 'Pending',
    },
    {
        'id': 'NORM-005',
        'contact_name': 'Michael Brown',
        'field': 'name',
        'current_value': 'MICHAEL BROWN',
        'suggested_value': 'Michael Brown',
        'reason': 'All caps to title case',
        'confidence': '98%',
        'status': 'Pending',
    },
    {
        'id': 'NORM-006',
        'contact_name': 'Mary Johnson',
        'field': 'phone',
        'current_value': '(555) 555-5555',
        'suggested_value': '(555) 555-5555',
        'reason': 'Already normalized',
        'confidence': '100%',
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
        'confidence': '98%',
        'proposed_members': ['John Smith (P-001)', 'Robert Smith (P-003)', 'Sarah Smith (P-010)'],
        'evidence': [
            'Shared last name: Smith',
            'Similar addresses: Main St area',
            'Email domain patterns match',
        ],
        'conflicts': [],
        'status': 'Pending',
    },
    {
        'id': 'HH-002',
        'suggested_name': 'Williams Family',
        'confidence': '95%',
        'proposed_members': ['Sarah Williams (P-008)', 'Sara Williams (P-009)'],
        'evidence': [
            'Similar names and addresses',
            'Matching phone numbers',
            'Same zip code',
        ],
        'conflicts': ['Email addresses differ'],
        'status': 'Pending',
    },
    {
        'id': 'HH-003',
        'suggested_name': 'Doe Family',
        'confidence': '87%',
        'proposed_members': ['Jane Doe (P-002)', 'John Doe (P-011)'],
        'evidence': [
            'Shared last name',
            'Nearby addresses',
        ],
        'conflicts': ['Different email domains'],
        'status': 'Pending',
    },
    {
        'id': 'HH-004',
        'suggested_name': 'Johnson Household',
        'confidence': '92%',
        'proposed_members': ['Mary Johnson (P-004)', 'James Johnson (P-012)'],
        'evidence': [
            'Same last name',
            'Matching phone number pattern',
            'Same address',
        ],
        'conflicts': [],
        'status': 'Pending',
    },
    {
        'id': 'HH-005',
        'suggested_name': 'Brown Individual',
        'confidence': '0%',
        'proposed_members': ['Michael Brown (P-005)'],
        'evidence': [],
        'conflicts': ['No matches found'],
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
