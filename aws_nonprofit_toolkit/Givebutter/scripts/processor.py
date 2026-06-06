#!/usr/bin/env python3
"""
Givebutter CSV processor with validation, dedup, and tier assignment.

Reads Givebutter export CSV, validates records against rules and reference list,
detects duplicates, and outputs processed CSV with validation results.
"""

import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import pandas as pd
from difflib import SequenceMatcher
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROCESSOR_VERSION = "2.5"  # Updated with Date/Transaction ID as required fields
BASE_DIR = Path(__file__).resolve().parents[1]  # Givebutter/
RULES_FILE = BASE_DIR / "config" / "rules" / "rules_v2.4.json"
REFERENCE_FILE = BASE_DIR / "config" / "reference_list.json"

# Static Platform Headers (never change, case-sensitive)
# These are the exact column names that Givebutter always generates
CORE_HEADERS = {
    # Transaction metadata
    'transaction_id': 'Transaction ID',
    'payout_id': 'Payout ID',
    'status': 'Status',
    'date': 'Date',

    # Donor identity
    'name': 'Name',
    'email': 'Email',
    'phone': 'Phone',

    # Address
    'address_1': 'Address 1',
    'address_2': 'Address 2',
    'city': 'City',
    'state': 'State',
    'zip': 'Zip',
    'country': 'Country',

    # Financial
    'amount': 'Amount',
    'processing_fee': 'Processing Fee',
    'givebutter_fee': 'Givebutter Fee',
    'fees_covered': 'Fees Covered',
    'payment_method': 'Payment Method',

    # Campaign
    'campaign': 'Campaign Title',

    # Tracking
    'utm_source': 'utm_source',
    'utm_medium': 'utm_medium',

    # Custom form fields (will be in FUZZY_HEADERS as fallbacks)
    'in_honor_of': 'In Honor Of',
    'dedication_message': 'Dedication Message',
    'ticket_title': 'Ticket Title',
    'ticket_quantity': 'Ticket Quantity',
    'item_quantity': 'Item Quantity',
}

# Fuzzy Match Fallbacks (catches variations in custom/alternate field names)
# Use these for slight variations in column naming that might occur
FUZZY_HEADERS = {
    'transaction_id': ['Donation ID', 'Gift ID', 'Contribution ID', 'donation_id', 'gift_id'],
    'name': ['Full Name', 'Donor Name', 'Donor', 'First and Last Name', 'donor_name', 'full_name'],
    'email': ['Email Address', 'Primary Email', 'Contact Email', 'Email (Primary)', 'email_address', 'primary_email'],
    'phone': ['Phone Number', 'Contact Phone', 'Phone (Primary)', 'Mobile Phone', 'phone_number', 'contact_phone'],
    'date': ['Donation Date', 'donation_date', 'Gift Date', 'Date Received', 'gift_date', 'date_received'],
    'zip': ['Zipcode', 'Postal Code', 'ZIP Code', 'Postal', 'postal_code', 'zip_code'],
    'address_1': ['Street Address', 'Address Line 1', 'Street', 'street_address', 'address_line_1'],
    'address_2': ['Address Line 2', 'Apt/Suite', 'address_line_2'],
    'campaign': ['Fund', 'Campaign', 'Gift Fund', 'Donation Fund', 'campaign_title'],
    'payment_method': ['Payment Type', 'Method', 'payment_type'],
}


def load_rules() -> Dict:
    """Load validation rules from config."""
    try:
        logger.info(f"Loading rules from: {RULES_FILE}")
        with open(RULES_FILE) as f:
            rules = json.load(f)
            logger.info(f"✓ Rules loaded successfully")
            return rules
    except FileNotFoundError:
        logger.warning(f"Rules file not found at {RULES_FILE}")
        return {}


def load_reference_list() -> Dict:
    """Load reference list from config."""
    try:
        logger.info(f"Loading reference list from: {REFERENCE_FILE}")
        with open(REFERENCE_FILE) as f:
            reference = json.load(f)

            # Log key configuration values
            valid_range = reference.get('amount_statistics', {}).get('valid_range', [])
            high_threshold = reference.get('high_dollar_threshold', 'Not set')
            logger.info(f"✓ Reference list loaded")
            logger.info(f"  Amount valid range: ${valid_range[0] if valid_range else '?'} - ${valid_range[1] if len(valid_range) > 1 else '?'}")
            logger.info(f"  High-dollar threshold: ${high_threshold}")

            return reference
    except FileNotFoundError:
        logger.warning(f"Reference list not found at {REFERENCE_FILE}")
        return {}


def build_header_mapping(df_columns) -> Dict[str, str]:
    """
    Build mapping of logical header names to actual CSV column names.

    Implements two-tier matching strategy:
    1. STRICT matching against exact case-sensitive static platform headers
    2. FUZZY fallback matching for custom/alternate field names (case-insensitive)

    All unmapped columns pass through untouched (custom fields, tracking data).

    Args:
        df_columns: DataFrame column names

    Returns:
        Dict mapping logical keys (name, email, phone, etc.) to actual column names
    """
    # Strip whitespace from all column names
    clean_columns = {col.strip(): col for col in df_columns}
    # Case-insensitive lookup: lowercase -> original case
    lowercase_columns = {col.strip().lower(): col.strip() for col in df_columns}

    mapping = {}

    # Try strict matches first
    for key, strict_name in CORE_HEADERS.items():
        if strict_name in clean_columns:
            mapping[key] = clean_columns[strict_name]
        else:
            # Try fuzzy matches (case-insensitive)
            fuzzy_options = FUZZY_HEADERS.get(key, [])
            for fuzzy_name in fuzzy_options:
                if fuzzy_name.lower() in lowercase_columns:
                    mapping[key] = lowercase_columns[fuzzy_name.lower()]
                    break

    return mapping


def extract_digits(phone: str) -> str:
    """Extract only digits from phone string."""
    if pd.isna(phone) or str(phone).strip() == '':
        return ''
    return re.sub(r'\D', '', str(phone))


def validate_transaction_id(record: Dict, header_map: Dict) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Validate transaction ID is present (required field).

    Args:
        record: Full record dict
        header_map: Mapping of logical field names to actual column names

    Returns: (tier, reason, suggestion)
    """
    txn_col = header_map.get('transaction_id')
    if not txn_col:
        return ('FAIL', "Transaction ID column not found in input", "Include Transaction ID/Donation ID column in export")

    txn_id = record.get(txn_col)
    if pd.isna(txn_id) or str(txn_id).strip() == '':
        return ('FAIL', "Transaction ID field is empty", "Verify transaction ID for each record")

    return ('PASS', None, None)


def validate_date(record: Dict, header_map: Dict) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Validate donation date is present (required field).

    Args:
        record: Full record dict
        header_map: Mapping of logical field names to actual column names

    Returns: (tier, reason, suggestion)
    """
    date_col = header_map.get('date')
    if not date_col:
        return ('FAIL', "Date column not found in input", "Include Date/Donation Date column in export")

    date_val = record.get(date_col)
    if pd.isna(date_val) or str(date_val).strip() == '':
        return ('FAIL', "Date field is empty", "Verify donation date for each record")

    return ('PASS', None, None)


def validate_phone(record: Dict, header_map: Dict, rules: Dict) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Validate phone number against USA standards and rules.

    Args:
        record: Full record dict
        header_map: Mapping of logical field names to actual column names
        rules: Validation rules

    Returns: (tier, reason, suggestion)
      - tier: 'PASS', 'FAIL', or 'WARNING'
      - reason: explanation if FAIL
      - suggestion: modification if WARNING
    """
    phone_col = header_map.get('phone')
    if not phone_col:
        return ('WARNING', "Phone number not found", "Add phone numbers to your donations export")

    phone = record.get(phone_col)
    if pd.isna(phone) or str(phone).strip() == '':
        return ('WARNING', "Phone number is empty", None)  # Frontend validates required; absence is notable

    phone_str = str(phone).strip()
    digits = extract_digits(phone_str)

    # Check against invalid patterns
    invalid_patterns = rules.get('invalid_phone_patterns', [])
    for pattern_obj in invalid_patterns:
        pattern = pattern_obj.get('pattern')
        reason = pattern_obj.get('reason', 'Invalid phone')
        if re.match(pattern, digits):
            return ('FAIL', f"Invalid: {reason}", "Please use a valid phone number")

    # Check for unusual formatting BEFORE validating digit count
    has_unusual_format = '.' in phone_str or phone_str.count('-') > 2 or phone_str.count('(') > 1

    # Check digit count
    if len(digits) == 10:
        # Valid US 10-digit number
        area_code = digits[:3]
        if area_code.startswith('0') or area_code.startswith('1'):
            return ('WARNING', "Area code should not start with 0 or 1", None)

        # If unusual format, suggest standard
        if has_unusual_format:
            suggestion = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
            return ('WARNING', "Unusual phone format", f"Consider: {suggestion}")

        return ('PASS', None, None)

    elif len(digits) == 11 and digits.startswith('1'):
        # Valid: 1 + 10-digit number (bare or formatted)
        normalized = digits[1:]
        area_code = normalized[:3]
        if area_code.startswith('0') or area_code.startswith('1'):
            suggestion = f"({normalized[:3]}) {normalized[3:6]}-{normalized[6:]}"
            return ('WARNING', "Area code should not start with 0 or 1", f"Try: {suggestion}")

        # Accept bare 11-digit numbers (e.g., 15551234567) without formatting requirement
        # Only warn if has unusual formatting (multiple dots, many dashes, etc.)
        if has_unusual_format:
            suggestion = f"({normalized[:3]}) {normalized[3:6]}-{normalized[6:]}"
            return ('WARNING', "Unusual phone format", f"Consider: {suggestion}")
        return ('PASS', None, None)

    elif len(digits) < 10:
        return ('FAIL', "Phone too short (less than 10 digits)", None)

    elif len(digits) > 11:
        return ('FAIL', f"Phone too long ({len(digits)} digits)", None)

    return ('PASS', None, None)


def validate_email(record: Dict, header_map: Dict, rules: Dict, reference: Dict) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Validate email against typo rules and reference patterns.

    Args:
        record: Full record dict
        header_map: Mapping of logical field names to actual column names
        rules: Validation rules
        reference: Reference list patterns

    Returns: (tier, reason, suggestion)
    """
    email_col = header_map.get('email')
    if not email_col:
        return ('FAIL', "Email column not found in input", None)

    email = record.get(email_col)
    if pd.isna(email) or str(email).strip() == '':
        return ('FAIL', "Email field is empty", "Verify email address for each record")

    email_str = str(email).strip().lower()

    # Check for typo patterns
    email_typos = {t['from']: t['to'] for t in rules.get('email_typos', [])}

    if '@' in email_str:
        user_part, domain = email_str.rsplit('@', 1)

        # Domain must not be empty
        if not domain:
            return ('FAIL', "Invalid email format (missing domain after @)", "Fix email format: add domain after @ symbol")

        # Check for exact typos first
        if domain in email_typos:
            correct_domain = email_typos[domain]
            suggestion = f"{user_part}@{correct_domain}"
            return ('WARNING', "Email typo detected", f"Consider: {suggestion}")

        # Fuzzy match against common domains (only if not exact match)
        common_domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'aol.com', 'protonmail.com', 'icloud.com']
        if domain not in common_domains:  # Skip fuzzy matching for exact matches
            for common_domain in common_domains:
                similarity = SequenceMatcher(None, domain, common_domain).ratio()
                if similarity >= 0.85:  # 85% match threshold
                    suggestion = f"{user_part}@{common_domain}"
                    return ('WARNING', f"Email domain '{domain}' is similar to '{common_domain}'", f"Consider: {suggestion}")

        # Check domain against reference list
        valid_domains = reference.get('email_domains', [])
        valid_tlds = reference.get('email_tlds', [])

        if valid_domains and domain not in valid_domains:
            # Check TLD at least
            tld = domain.split('.')[-1]
            if valid_tlds and tld not in valid_tlds:
                return ('WARNING', None, f"Domain '{domain}' not in reference list")

        return ('PASS', None, None)

    return ('FAIL', "Invalid email format (missing @)", "Fix email format: add @ symbol")


def validate_amount(record: Dict, header_map: Dict, reference: Dict) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Validate amount against reference ranges and thresholds.

    Args:
        record: Full record dict
        header_map: Mapping of logical field names to actual column names
        reference: Reference list patterns

    Returns: (tier, reason, suggestion)
    """
    amount_col = header_map.get('amount')
    if not amount_col:
        return ('FAIL', "Amount column not found in input", "Include Amount column in export")

    amount = record.get(amount_col)
    if pd.isna(amount) or str(amount).strip() == '':
        return ('FAIL', "Amount field is empty", "Verify donation amount")

    try:
        amount_val = float(str(amount).replace('$', '').replace(',', '').strip())
    except ValueError:
        return ('FAIL', "Invalid amount format", "Enter valid numeric amount")

    if amount_val <= 0:
        return ('FAIL', "Amount must be greater than 0", "Enter positive amount value")

    # Check against reference ranges
    stats = reference.get('amount_statistics', {})
    valid_range = stats.get('valid_range', [1, 100000])

    if amount_val < valid_range[0]:
        return ('WARNING', f"Amount below typical range (${valid_range[0]})", None)

    if amount_val > valid_range[1]:
        return ('WARNING', f"Amount above typical range (${valid_range[1]})", None)

    # Note: high_dollar_threshold is stored but not used for WARNING tier
    # (reserved for future use in separate flagging system)

    return ('PASS', None, None)


def validate_address(record: Dict, header_map: Dict) -> Tuple[str, Optional[str]]:
    """
    Validate address fields.

    Args:
        record: Full record dict
        header_map: Mapping of logical field names to actual column names

    Returns: (tier, reason)
    """
    addr1_col = header_map.get('address_1')
    city_col = header_map.get('city')
    state_col = header_map.get('state')

    # If any required address column is missing, skip validation
    if not (addr1_col and city_col and state_col):
        return ('PASS', None)

    addr1 = str(record.get(addr1_col, '')).strip()
    city = str(record.get(city_col, '')).strip()
    state = str(record.get(state_col, '')).strip()

    # Frontend validates these, but check completeness
    if not addr1 or not city or not state:
        return ('WARNING', "Incomplete address (missing street, city, or state)")

    return ('PASS', None)


def validate_name(record: Dict, header_map: Dict, reference: Dict) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Validate name against reference patterns.

    Args:
        record: Full record dict
        header_map: Mapping of logical field names to actual column names
        reference: Reference list patterns

    Returns: (tier, reason, suggestion)
    """
    name_col = header_map.get('name')
    if not name_col:
        return ('FAIL', "Name column not found in input", "Include Name/Donor Name column in export")

    name = record.get(name_col)
    if pd.isna(name) or str(name).strip() == '':
        return ('FAIL', "Name field is empty", "Verify donor name for each record")

    name_str = str(name).strip()
    patterns = reference.get('name_patterns', {})

    min_len = patterns.get('min_length', 2)
    max_len = patterns.get('max_length', 100)

    if len(name_str) < min_len:
        return ('FAIL', f"Name too short (< {min_len} characters)", f"Enter name with at least {min_len} characters")

    if len(name_str) > max_len:
        return ('FAIL', f"Name too long (> {max_len} characters)", f"Shorten name to {max_len} characters or less")

    return ('PASS', None, None)


def normalize_for_comparison(value: str) -> str:
    """Normalize string for fuzzy matching (lowercase, remove extra spaces)."""
    if pd.isna(value):
        return ''
    return ' '.join(str(value).lower().split())


def fuzzy_match(str1: str, str2: str, threshold: float = 0.70) -> bool:
    """Check if two strings match above threshold using SequenceMatcher."""
    norm1 = normalize_for_comparison(str1)
    norm2 = normalize_for_comparison(str2)

    if not norm1 or not norm2:
        return False

    ratio = SequenceMatcher(None, norm1, norm2).ratio()
    return ratio >= threshold


def check_duplicates(record: Dict, all_records: List[Dict], header_map: Dict, rules: Dict) -> Tuple[bool, Optional[str]]:
    """
    Check for duplicate/household records based on email, phone, address, or fuzzy name.

    Args:
        record: Current record
        all_records: All records to check against
        header_map: Mapping of logical field names to actual column names
        rules: Validation rules

    Returns: (is_duplicate, duplicate_info)
    """
    threshold = rules.get('fuzzy_match_threshold', 0.70)

    email_col = header_map.get('email')
    phone_col = header_map.get('phone')
    name_col = header_map.get('name')
    addr1_col = header_map.get('address_1')
    city_col = header_map.get('city')
    state_col = header_map.get('state')
    txn_col = header_map.get('transaction_id')

    current_email = normalize_for_comparison(record.get(email_col, '')) if email_col else ''
    current_phone = extract_digits(str(record.get(phone_col, ''))) if phone_col else ''
    current_name = record.get(name_col, '') if name_col else ''
    current_addr1 = normalize_for_comparison(record.get(addr1_col, '')) if addr1_col else ''
    current_city = normalize_for_comparison(record.get(city_col, '')) if city_col else ''
    current_state = normalize_for_comparison(record.get(state_col, '')) if state_col else ''

    matches = []

    for other in all_records:
        other_txn = other.get(txn_col) if txn_col else None
        current_txn = record.get(txn_col) if txn_col else None
        if other_txn and current_txn and other_txn == current_txn:
            continue  # Skip self

        # Email exact match
        other_email = normalize_for_comparison(other.get(email_col, '')) if email_col else ''
        if current_email and current_email == other_email:
            matches.append(f"Email match: {other_txn or 'unknown'}")

        # Phone exact match
        other_phone = extract_digits(str(other.get(phone_col, ''))) if phone_col else ''
        if current_phone and current_phone == other_phone:
            matches.append(f"Phone match: {other_txn or 'unknown'}")

        # Address exact match
        other_addr1 = normalize_for_comparison(other.get(addr1_col, '')) if addr1_col else ''
        other_city = normalize_for_comparison(other.get(city_col, '')) if city_col else ''
        other_state = normalize_for_comparison(other.get(state_col, '')) if state_col else ''

        if current_addr1 and current_addr1 == other_addr1 and \
           current_city == other_city and current_state == other_state:
            matches.append(f"Address match: {other_txn or 'unknown'}")

        # Fuzzy name match
        other_name = other.get(name_col, '') if name_col else ''
        if fuzzy_match(current_name, other_name, threshold):
            matches.append(f"Name match ({threshold*100:.0f}%): {other_txn or 'unknown'}")

    if matches:
        return (True, "; ".join(matches))

    return (False, None)


def assign_tier(validation_results: Dict) -> str:
    """
    Assign validation tier based on validation results.

    - FAIL: Any field failed validation
    - WARNING: Any field has warning, no failures
    - PASS: All fields passed
    """
    for field, result in validation_results.items():
        if result.get('tier') == 'FAIL':
            return 'FAIL'

    for field, result in validation_results.items():
        if result.get('tier') == 'WARNING':
            return 'WARNING'

    return 'PASS'


def process_csv(input_file: str, output_file: str) -> None:
    """
    Process Givebutter export CSV through validation pipeline.

    Outputs single CSV with validation results and suggested modifications.
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Givebutter CSV Processor v{PROCESSOR_VERSION}")
    logger.info(f"{'='*60}")
    logger.info(f"Processing: {input_file}")

    # Load configs
    rules = load_rules()
    reference = load_reference_list()

    # Read input
    try:
        import csv
        # Use csv.reader for accurate column-to-value mapping (handles misaligned CSVs)
        # Explicitly use UTF-8 encoding to handle international characters
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = list(reader)

        # Normalize row lengths to match header count (handles trailing empty columns)
        normalized_rows = []
        for row in rows:
            if len(row) > len(headers):
                row = row[:len(headers)]  # Trim extra columns
            elif len(row) < len(headers):
                row = row + [''] * (len(headers) - len(row))  # Pad missing columns
            normalized_rows.append(row)

        # Construct dataframe from csv.reader results
        df = pd.DataFrame(normalized_rows, columns=headers, dtype=str)

        # Strip whitespace from all column headers
        df.columns = df.columns.str.strip()
        # Remove completely empty rows
        df = df.dropna(how='all')
        # Remove rows where all data columns are empty (keep header checking)
        df = df.dropna(thresh=3)
        # Reset index to match enumerate indices
        df = df.reset_index(drop=True)
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return

    # Build header mapping for robust column access
    header_map = build_header_mapping(df.columns)
    if not header_map:
        print("❌ Error: Could not locate required Givebutter columns")
        return

    logger.info(f"Found {len(df)} records")

    # Convert to list of dicts for processing
    records = df.to_dict('records')

    # Initialize output columns
    df['Validation_Tier'] = ''
    df['Issues'] = ''
    df['Suggested_Modifications'] = ''

    # Process each record
    for idx, record in enumerate(records):
        validation_results = {}
        issues = []
        required_suggestions = []  # Transaction ID, Date, Email, Amount, Name
        duplicate_suggestions = []
        address_suggestions = []
        optional_suggestions = []  # Phone, etc.

        # Validate transaction ID (required)
        tier, reason, suggestion = validate_transaction_id(record, header_map)
        validation_results['transaction_id'] = {'tier': tier, 'reason': reason}
        if reason:
            issues.append(f"Transaction ID: {reason}")
        if suggestion:
            required_suggestions.append(suggestion)

        # Validate date (required)
        tier, reason, suggestion = validate_date(record, header_map)
        validation_results['date'] = {'tier': tier, 'reason': reason}
        if reason:
            issues.append(f"Date: {reason}")
        if suggestion:
            required_suggestions.append(suggestion)

        # Validate email (required)
        tier, reason, suggestion = validate_email(record, header_map, rules, reference)
        validation_results['email'] = {'tier': tier, 'reason': reason}
        if reason:
            issues.append(f"Email: {reason}")
        if suggestion:
            required_suggestions.append(suggestion)

        # Validate amount (required)
        tier, reason, suggestion = validate_amount(record, header_map, reference)
        validation_results['amount'] = {'tier': tier, 'reason': reason}
        if reason:
            issues.append(f"Amount: {reason}")
        if suggestion:
            required_suggestions.append(suggestion)

        # Validate name (required)
        tier, reason, suggestion = validate_name(record, header_map, reference)
        validation_results['name'] = {'tier': tier, 'reason': reason}
        if reason:
            issues.append(f"Name: {reason}")
        if suggestion:
            required_suggestions.append(suggestion)

        # Check for duplicates
        is_dup, dup_info = check_duplicates(record, records, header_map, rules)
        if is_dup:
            issues.append(f"Duplicate: {dup_info}")
            validation_results['duplicate'] = {'tier': 'WARNING', 'reason': dup_info}
            duplicate_suggestions.append("Review duplicate entries")

        # Validate address (optional)
        tier, reason = validate_address(record, header_map)
        validation_results['address'] = {'tier': tier, 'reason': reason}
        if reason:
            issues.append(f"Address: {reason}")
        if reason:  # address validator doesn't return suggestion, but could add one
            address_suggestions.append("Complete address information (street, city, state)")

        # Validate phone (optional)
        tier, reason, suggestion = validate_phone(record, header_map, rules)
        validation_results['phone'] = {'tier': tier, 'reason': reason}
        if reason:
            issues.append(f"Phone: {reason}")
        if suggestion:
            optional_suggestions.append(suggestion)

        # Combine suggestions in priority order: required, duplicates, address, optional
        suggestions = required_suggestions + duplicate_suggestions + address_suggestions + optional_suggestions

        # Assign tier
        tier = assign_tier(validation_results)

        # Write results
        df.at[idx, 'Validation_Tier'] = tier
        # Limit issues to 5 for readability
        max_issues = issues[:5]
        df.at[idx, 'Issues'] = "; ".join(max_issues) if max_issues else "None"
        # Limit suggestions to 5 for readability (prioritized: required, duplicates, address, optional)
        max_suggestions = suggestions[:5]
        df.at[idx, 'Suggested_Modifications'] = "; ".join(max_suggestions) if max_suggestions else ""

        # Print progress
        status = "✓" if tier == 'PASS' else "⚠" if tier == 'WARNING' else "✗"
        name_col = header_map.get('name')
        display_name = record.get(name_col, 'Unknown') if name_col else 'Unknown'
        print(f"  {status} [{idx+1}/{len(records)}] {display_name} - {tier}")

    # Reorder columns: original Givebutter data first, validation results last
    orig_cols = [c for c in df.columns if c not in ['Validation_Tier', 'Issues', 'Suggested_Modifications']]
    new_order = orig_cols + ['Validation_Tier', 'Issues', 'Suggested_Modifications']
    df = df[new_order]

    # Write output with UTF-8 encoding to preserve international characters
    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"\n✅ Output written to: {output_file}")

    # Summary stats
    pass_count = len(df[df['Validation_Tier'] == 'PASS'])
    warn_count = len(df[df['Validation_Tier'] == 'WARNING'])
    fail_count = len(df[df['Validation_Tier'] == 'FAIL'])

    print(f"\n📊 Summary:")
    print(f"  PASS:    {pass_count} ({pass_count/len(df)*100:.1f}%)")
    print(f"  WARNING: {warn_count} ({warn_count/len(df)*100:.1f}%)")
    print(f"  FAIL:    {fail_count} ({fail_count/len(df)*100:.1f}%)")


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python processor.py <input_csv> [output_csv]")
        print("\nExample:")
        print("  python processor.py raw_export.csv processed_export.csv")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.replace('.csv', '_processed.csv')

    process_csv(input_file, output_file)
