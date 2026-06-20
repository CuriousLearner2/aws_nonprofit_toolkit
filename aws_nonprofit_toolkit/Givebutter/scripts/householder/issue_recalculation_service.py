"""
Issue Recalculation Service for v1.1 Review Screen Refinement

Recalculates validation issues for a row using effective values (raw + corrections).
Does not mutate raw source data or ReviewItem.payload_json.
Returns updated list of issues for display in Issues column.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .database_models import (
    ImportBatch, RawImportRow, ReviewItem, ReviewItemSubject
)
from .autosave_service import get_effective_values
from .phone_validation_service import is_valid_phone
import os

# Top 30 recognized email domains - strict validation applied to these
RECOGNIZED_EMAIL_DOMAINS = {
    # Major global providers
    'gmail.com',
    'yahoo.com',
    'outlook.com',
    'hotmail.com',
    'aol.com',
    'icloud.com',
    'mail.com',
    'gmx.com',
    'web.de',
    'protonmail.com',
    'proton.me',
    'zoho.com',
    'fastmail.com',
    'mailbox.org',
    'posteo.de',
    # Regional variants
    'yahoo.co.uk', 'yahoo.ca', 'yahoo.fr', 'yahoo.de', 'yahoo.it',
    'outlook.co.uk', 'outlook.fr', 'outlook.de',
    'hotmail.co.uk', 'hotmail.fr', 'hotmail.de',
    # International providers
    'mail.ru',
    'yandex.com',
    'qq.com',
    'sina.com',
    '163.com',
}

# Common typo domains - maps incorrect domain to correct domain
COMMON_TYPO_DOMAINS = {
    'gamil.com': 'gmail.com',      # i-l swap
    'gmial.com': 'gmail.com',      # letter swap
    'gmal.com': 'gmail.com',       # missing i
    'gmai.com': 'gmail.com',       # incomplete
    'yahooo.com': 'yahoo.com',     # extra o
    'yaho.com': 'yahoo.com',       # missing o
    'hotmial.com': 'hotmail.com',  # letter swap
    'hotmal.com': 'hotmail.com',   # missing i
}


def recalculate_row_issues(
    batch_id: str,
    raw_import_row_id: int,
    database_url: Optional[str] = None,
    proposed_values: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Recalculate validation issues for a row using effective values.

    Workflow:
    1. Get effective values (raw + latest corrections)
    2. Run validation rules on effective values
    3. Compare with existing ReviewItems
    4. Return updated issue list (may be empty if corrections resolved issues)

    Does NOT mutate RawImportRow, ReviewItem, or ReviewDecision.

    Args:
        batch_id: Import batch ID
        raw_import_row_id: RawImportRow.id
        database_url: Database connection URL (optional)
        proposed_values: Optional proposed corrections to validate against (used when autosave validation fails)

    Returns:
        List of issues: [{"issue_id": int, "issue_type": str, "description": str, "severity": str}, ...]

    Raises:
        ValueError: If batch or row not found
    """
    if database_url is None:
        database_url = os.environ.get('GIVEBUTTER_DATABASE_URL', 'sqlite:///./givebutter.db')

    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # Verify batch and row exist
        batch = session.query(ImportBatch).filter_by(id=batch_id).first()
        if not batch:
            raise ValueError(f"Import batch '{batch_id}' not found")

        raw_row = session.query(RawImportRow).filter_by(id=raw_import_row_id).first()
        if not raw_row:
            raise ValueError(f"Raw import row {raw_import_row_id} not found")

        # Get effective values (raw + corrections)
        # If proposed_values provided, merge them in (for validation of unsaved corrections)
        effective_values = get_effective_values(batch_id, raw_import_row_id, database_url)
        if proposed_values:
            effective_values.update(proposed_values)

        # Get raw data for comparison
        raw_data = raw_row.raw_csv_data or {}

        # Get all existing validation issues for this row
        # Check both import_raw_row (Phase 1B raw data) and import_contact_snapshot (demo data)
        existing_issues = session.query(ReviewItem).join(
            ReviewItemSubject,
            ReviewItem.id == ReviewItemSubject.review_item_id
        ).filter(
            ReviewItem.batch_id == batch_id,
            ReviewItem.item_type == 'validation',
            ReviewItemSubject.subject_type.in_(['import_raw_row', 'import_contact_snapshot']),
            ReviewItemSubject.subject_id == raw_import_row_id
        ).all()

        # For each existing issue, check if it's still valid given the effective values
        current_issues = []

        for issue in existing_issues:
            payload = issue.payload_json or {}
            issue_field = payload.get('field')  # e.g., 'email'
            issue_reason = payload.get('reason')  # e.g., 'possible_typo'
            severity = payload.get('severity', 'warning')

            # Get the corrected value for this field (if any)
            effective_value = effective_values.get(issue_field)
            raw_value = raw_data.get(issue_field)

            # Check if issue is still valid with the effective value
            # Logic: if a correction was made to the field, we assume the issue is resolved

            if is_issue_resolved(issue_field, effective_value, issue_reason, raw_value):
                # Issue is resolved, don't include it
                continue
            else:
                # Issue remains unresolved
                description = payload.get('description', f"Issue with {issue_field}")

                # Add suggestion if it's a common typo domain
                if issue_field == 'email' and issue_reason in ('typo', 'possible_typo', 'format'):
                    suggestion = _get_email_suggestion(effective_value)
                    if suggestion:
                        description += f" Did you mean {suggestion}?"

                current_issues.append({
                    'issue_id': issue.id,
                    'issue_type': issue.item_type,
                    'field': issue_field,
                    'description': description,
                    'severity': severity,
                    'overridden': _is_issue_overridden(batch, raw_import_row_id, issue_field)
                })

        # Additionally, validate effective values to detect NEW issues not in ReviewItems
        # ONLY if proposed_values were provided (i.e., autosave with corrections)
        # This catches validation errors introduced by autosave corrections
        if proposed_values:
            existing_fields = {issue.get('field') for issue in current_issues if issue.get('field')}
            new_validation_issues = _validate_effective_values(effective_values)
            for new_issue in new_validation_issues:
                if new_issue.get('field') not in existing_fields:
                    current_issues.append(new_issue)

        return current_issues

    finally:
        session.close()


def is_issue_resolved(
    field: str,
    effective_value: Any,
    issue_reason: str,
    raw_value: Any = None,
) -> bool:
    """
    Check if an issue is resolved given the effective field value.

    Resolution logic:
    - Missing: resolved if value is now non-empty
    - Typo/format: requires raw_value for comparison; resolved if value differs AND format is valid

    Args:
        field: Field name (e.g., 'email', 'phone')
        effective_value: Current effective value for the field
        issue_reason: Issue type (e.g., 'missing', 'typo', 'format')
        raw_value: Original raw value (optional, for comparison)

    Returns:
        True if issue appears resolved, False otherwise
    """
    if not field:
        return False

    # Convert to string for validation
    effective_str = str(effective_value).strip() if effective_value else ''

    if issue_reason == 'missing':
        # Issue resolved if now non-empty
        return bool(effective_str)
    elif issue_reason in ('typo', 'format', 'possible_typo'):
        # For typo/format issues: MUST have raw_value to determine if correction was made
        if raw_value is None:
            # Cannot determine if corrected without raw value
            return False

        if not effective_str:
            return False

        # Check if a correction was actually made
        raw_str = str(raw_value).strip() if raw_value else ''
        if effective_str == raw_str:
            # No correction made, issue not resolved
            return False

        # Basic validation for common issues
        if field == 'email':
            # Email validation: two-tier approach
            import re

            # Canonical format: something@something.something
            email_pattern = r'^[^@]+@[^@]+\.[^@]+$'
            if not re.match(email_pattern, effective_str.lower()):
                # Invalid canonical format (missing @, domain, or TLD)
                return False

            # Extract domain for recognized domain check
            try:
                domain = effective_str.lower().rsplit('@', 1)[1]
            except (IndexError, AttributeError):
                return False

            # Check for common typo domains FIRST (applies to all emails)
            if domain in COMMON_TYPO_DOMAINS:
                # This is a known typo domain - not resolved unless corrected to actual domain
                corrected_domain = COMMON_TYPO_DOMAINS[domain]
                # Only resolved if user corrected it to the right domain
                return raw_value is not None and corrected_domain in raw_value.lower()

            # Two-tier validation:
            # Tier 1: Recognized domains - strict validation (catch typos)
            if domain in RECOGNIZED_EMAIL_DOMAINS:
                invalid_typos = [
                    r'gmial(?:\.com)?',  # gmail typo: gmial
                    r'gmal(?:\.com)?',   # gmail typo: gmal (missing i)
                    r'yahooo(?:\.com)?', # yahoo typo: yahooo
                    r'hotmial(?:\.com)?',# hotmail typo: hotmial
                    r'\bgmai\b',         # gmai standalone (not part of gmail)
                ]
                has_invalid = any(re.search(pattern, effective_str.lower()) for pattern in invalid_typos)
                return not has_invalid
            else:
                # Tier 2: Unrecognized domains - lenient validation
                # If format is valid, accept it (likely corporate/regional email)
                return True
        elif field == 'phone':
            # Phone issue resolved if it's valid per phonenumbers library
            # Supports 131+ countries with intelligent parsing of various formats
            return is_valid_phone(effective_str)
        else:
            # For other fields, check if effective differs meaningfully from raw
            # (raw_value comparison already done above)
            return True
    else:
        return False  # Unknown reason, don't auto-resolve


def _validate_effective_values(effective_values: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Validate effective values to detect NEW validation issues.

    This function runs validation rules on the effective values to catch
    validation errors introduced by autosave corrections that don't have
    pre-existing ReviewItems.

    Args:
        effective_values: Dictionary of effective field values (raw + corrections)

    Returns:
        List of new validation issues found: [{"field": str, "description": str, "severity": str}, ...]
    """
    issues = []
    import re

    # Validate email if present
    if 'email' in effective_values:
        email_value = effective_values.get('email')
        if email_value:
            email_str = str(email_value).strip()
            email_issue = _validate_email(email_str)
            if email_issue:
                issues.append(email_issue)

    # Validate phone if present
    if 'phone' in effective_values:
        phone_value = effective_values.get('phone')
        if phone_value:
            phone_str = str(phone_value).strip()
            if phone_str and not is_valid_phone(phone_str):
                issues.append({
                    'field': 'phone',
                    'description': 'Invalid phone format',
                    'severity': 'error',
                    'is_new': True
                })

    # Validate amount if present (must validate even if falsy like 0, "", etc.)
    if 'amount' in effective_values:
        amount_value = effective_values.get('amount')
        amount_str = '' if amount_value is None else str(amount_value).strip()
        amount_issue = _validate_amount(amount_str)
        if amount_issue:
            issues.append(amount_issue)

    return issues


def _validate_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Validate email address and return issue if invalid.

    Applies two-tier validation:
    - Tier 1: Recognized domains - strict validation
    - Tier 2: Unrecognized domains - lenient validation

    Args:
        email: Email address to validate

    Returns:
        Issue dict if invalid, None if valid
    """
    import re

    if not email:
        return None

    email_lower = email.lower()

    # Canonical format: something@something.something
    email_pattern = r'^[^@]+@[^@]+\.[^@]+$'
    if not re.match(email_pattern, email_lower):
        return {
            'field': 'email',
            'description': 'Invalid email format',
            'severity': 'error',
            'is_new': True
        }

    # Extract domain
    try:
        domain = email_lower.rsplit('@', 1)[1]
    except (IndexError, AttributeError):
        return {
            'field': 'email',
            'description': 'Invalid email format',
            'severity': 'error',
            'is_new': True
        }

    # Check for common typo domains
    if domain in COMMON_TYPO_DOMAINS:
        return {
            'field': 'email',
            'description': f'Possible typo: did you mean {COMMON_TYPO_DOMAINS[domain]}?',
            'severity': 'warning',
            'is_new': True
        }

    # Two-tier validation for recognized domains
    if domain in RECOGNIZED_EMAIL_DOMAINS:
        # Strict validation: check for common typos
        invalid_typos = [
            r'gmial(?:\.com)?',   # gmail typo: gmial
            r'gmal(?:\.com)?',    # gmail typo: gmal (missing i)
            r'yahooo(?:\.com)?',  # yahoo typo: yahooo
            r'hotmial(?:\.com)?', # hotmail typo: hotmial
            r'\bgmai\b',          # gmai standalone
        ]
        has_invalid = any(re.search(pattern, email_lower) for pattern in invalid_typos)
        if has_invalid:
            return {
                'field': 'email',
                'description': 'Invalid email format',
                'severity': 'error',
                'is_new': True
            }

    # All validation passed
    return None


def _validate_amount(amount: str) -> Optional[Dict[str, Any]]:
    """
    Validate amount field and return issue if invalid.

    Checks for:
    - Empty/missing values
    - Non-numeric values (after removing $ and ,)
    - Amount <= 0

    Args:
        amount: Amount value to validate (string, may be empty)

    Returns:
        Issue dict if invalid, None if valid
    """
    # Empty or whitespace-only amount is invalid
    if not amount or not amount.strip():
        return {
            'field': 'amount',
            'description': 'Amount is required',
            'severity': 'error',
            'is_new': True
        }

    try:
        amount_val = float(amount.replace('$', '').replace(',', '').strip())
        if amount_val <= 0:
            return {
                'field': 'amount',
                'description': 'Amount must be greater than 0',
                'severity': 'error',
                'is_new': True
            }
    except ValueError:
        return {
            'field': 'amount',
            'description': 'Invalid amount format',
            'severity': 'error',
            'is_new': True
        }

    return None


def _get_email_suggestion(email: str) -> Optional[str]:
    """
    Check if email has a common typo domain and return suggestion.

    Args:
        email: Email address to check

    Returns:
        Suggested correct domain, or None if no typo detected
    """
    if not email:
        return None

    try:
        domain = email.lower().rsplit('@', 1)[1]
        if domain in COMMON_TYPO_DOMAINS:
            return COMMON_TYPO_DOMAINS[domain]
    except (IndexError, AttributeError):
        pass

    return None


def _is_issue_overridden(
    batch,
    raw_import_row_id: int,
    field: str,
) -> bool:
    """
    Check if an issue was overridden during batch approval.

    Args:
        batch: ImportBatch object
        raw_import_row_id: RawImportRow.id
        field: Field name

    Returns:
        True if batch was approved with overrides for this field on this row
    """
    if batch.approval_status != 'approved_with_overrides':
        return False

    if not batch.override_details:
        return False

    overrides = batch.override_details.get('overrides', [])
    for override in overrides:
        if override.get('raw_import_row_id') == raw_import_row_id:
            # Found override for this row
            # If field matches, mark as overridden
            override_field = override.get('field')
            if override_field == field or not override_field:
                return True

    return False
