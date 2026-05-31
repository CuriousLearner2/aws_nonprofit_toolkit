#!/usr/bin/env python3
"""
Givebutter CSV processor with validation, dedup, and tier assignment.

Reads Givebutter export CSV, validates records against rules and reference list,
detects duplicates, and outputs processed CSV with validation results.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import pandas as pd
from difflib import SequenceMatcher
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[1]  # Givebutter/
RULES_FILE = BASE_DIR / "config" / "rules" / "rules_v2.4.json"
REFERENCE_FILE = BASE_DIR / "config" / "reference_list.json"


def load_rules() -> Dict:
    """Load validation rules from config."""
    try:
        with open(RULES_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: Rules file not found at {RULES_FILE}")
        return {}


def load_reference_list() -> Dict:
    """Load reference list from config."""
    try:
        with open(REFERENCE_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: Reference list not found at {REFERENCE_FILE}")
        return {}


def extract_digits(phone: str) -> str:
    """Extract only digits from phone string."""
    if pd.isna(phone) or str(phone).strip() == '':
        return ''
    return re.sub(r'\D', '', str(phone))


def validate_phone(phone: str, rules: Dict) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Validate phone number against USA standards and rules.

    Returns: (tier, reason, suggestion)
      - tier: 'PASS', 'FAIL', or 'WARNING'
      - reason: explanation if FAIL
      - suggestion: modification if WARNING
    """
    if pd.isna(phone) or str(phone).strip() == '':
        return ('PASS', None, None)  # Frontend validates required; absence is OK here

    phone_str = str(phone).strip()
    digits = extract_digits(phone_str)

    # Check against invalid patterns
    invalid_patterns = rules.get('invalid_phone_patterns', [])
    for pattern_obj in invalid_patterns:
        pattern = pattern_obj.get('pattern')
        reason = pattern_obj.get('reason', 'Invalid phone')
        if re.match(pattern, digits):
            return ('FAIL', f"Invalid: {reason}", None)

    # Check for unusual formatting BEFORE validating digit count
    has_unusual_format = '.' in phone_str or phone_str.count('-') > 2 or phone_str.count('(') > 1

    # Check digit count
    if len(digits) == 10:
        # Valid US 10-digit number
        area_code = digits[:3]
        if area_code.startswith('0') or area_code.startswith('1'):
            return ('WARNING', None, "Area code should not start with 0 or 1")

        # If unusual format, suggest standard
        if has_unusual_format:
            suggestion = f"Unusual format. Consider: ({digits[:3]}) {digits[3:6]}-{digits[6:]}"
            return ('WARNING', None, suggestion)

        return ('PASS', None, None)

    elif len(digits) == 11 and digits.startswith('1'):
        # Valid: 1 + 10-digit number
        normalized = digits[1:]
        area_code = normalized[:3]
        if area_code.startswith('0') or area_code.startswith('1'):
            return ('WARNING', None, f"Area code should not start with 0 or 1. Normalized: ({normalized[:3]}) {normalized[3:6]}-{normalized[6:]}")

        # If format is unusual (e.g., 15550123948), suggest standard format
        if has_unusual_format or phone_str != f"+1 {normalized[:3]}-{normalized[3:6]}-{normalized[6:]}":
            suggestion = f"Format: ({normalized[:3]}) {normalized[3:6]}-{normalized[6:]}"
            return ('WARNING', None, suggestion)
        return ('PASS', None, None)

    elif len(digits) < 10:
        return ('FAIL', "Phone too short (less than 10 digits)", None)

    elif len(digits) > 11:
        return ('FAIL', f"Phone too long ({len(digits)} digits)", None)

    return ('PASS', None, None)


def validate_email(email: str, rules: Dict, reference: Dict) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Validate email against typo rules and reference patterns.

    Returns: (tier, reason, suggestion)
    """
    if pd.isna(email) or str(email).strip() == '':
        return ('PASS', None, None)  # Frontend validates required

    email_str = str(email).strip().lower()

    # Check for typo patterns
    email_typos = {t['from']: t['to'] for t in rules.get('email_typos', [])}

    if '@' in email_str:
        user_part, domain = email_str.rsplit('@', 1)

        # Check for typos
        if domain in email_typos:
            correct_domain = email_typos[domain]
            suggestion = f"{user_part}@{correct_domain}"
            return ('WARNING', None, f"Email typo detected. Consider: {suggestion}")

        # Check domain against reference list
        valid_domains = reference.get('email_domains', [])
        valid_tlds = reference.get('email_tlds', [])

        if valid_domains and domain not in valid_domains:
            # Check TLD at least
            tld = domain.split('.')[-1]
            if valid_tlds and tld not in valid_tlds:
                return ('WARNING', None, f"Domain '{domain}' not in reference list")

        return ('PASS', None, None)

    return ('FAIL', "Invalid email format (missing @)", None)


def validate_amount(amount: str, reference: Dict) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Validate amount against reference ranges and thresholds.

    Returns: (tier, reason, suggestion)
    """
    if pd.isna(amount) or str(amount).strip() == '':
        return ('FAIL', "Missing amount", None)

    try:
        amount_val = float(str(amount).replace('$', '').replace(',', '').strip())
    except ValueError:
        return ('FAIL', "Invalid amount format", None)

    if amount_val <= 0:
        return ('FAIL', "Amount must be greater than 0", None)

    # Check against reference ranges
    stats = reference.get('amount_statistics', {})
    valid_range = stats.get('valid_range', [1, 100000])

    if amount_val < valid_range[0]:
        return ('WARNING', None, f"Amount below typical range (${valid_range[0]})")

    if amount_val > valid_range[1]:
        return ('WARNING', None, f"Amount above typical range (${valid_range[1]})")

    # Check high-dollar threshold (this will eventually be a separate flag)
    high_dollar = reference.get('high_dollar_threshold') or 1000
    if amount_val >= high_dollar:
        return ('WARNING', None, f"High-dollar donation (>= ${high_dollar})")

    return ('PASS', None, None)


def validate_address(address: Dict) -> Tuple[str, Optional[str]]:
    """
    Validate address fields.

    Returns: (tier, reason)
    """
    addr1 = str(address.get('Address 1', '')).strip()
    city = str(address.get('City', '')).strip()
    state = str(address.get('State', '')).strip()

    # Frontend validates these, but check completeness
    if not addr1 or not city or not state:
        return ('WARNING', "Incomplete address (missing street, city, or state)")

    return ('PASS', None)


def validate_name(name: str, reference: Dict) -> Tuple[str, Optional[str]]:
    """
    Validate name against reference patterns.

    Returns: (tier, reason)
    """
    if pd.isna(name) or str(name).strip() == '':
        return ('FAIL', "Missing name")

    name_str = str(name).strip()
    patterns = reference.get('name_patterns', {})

    min_len = patterns.get('min_length', 2)
    max_len = patterns.get('max_length', 100)

    if len(name_str) < min_len:
        return ('FAIL', f"Name too short (< {min_len} characters)")

    if len(name_str) > max_len:
        return ('FAIL', f"Name too long (> {max_len} characters)")

    return ('PASS', None)


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


def check_duplicates(record: Dict, all_records: List[Dict], rules: Dict) -> Tuple[bool, Optional[str]]:
    """
    Check for duplicate/household records based on email, phone, address, or fuzzy name.

    Returns: (is_duplicate, duplicate_info)
    """
    threshold = rules.get('fuzzy_match_threshold', 0.70)

    current_email = normalize_for_comparison(record.get('Email', ''))
    current_phone = extract_digits(str(record.get('Phone', '')))
    current_name = record.get('Name', '')
    current_addr1 = normalize_for_comparison(record.get('Address 1', ''))
    current_city = normalize_for_comparison(record.get('City', ''))
    current_state = normalize_for_comparison(record.get('State', ''))

    matches = []

    for other in all_records:
        if other.get('Transaction ID') == record.get('Transaction ID'):
            continue  # Skip self

        # Email exact match
        other_email = normalize_for_comparison(other.get('Email', ''))
        if current_email and current_email == other_email:
            matches.append(f"Email match: {other.get('Transaction ID')}")

        # Phone exact match
        other_phone = extract_digits(str(other.get('Phone', '')))
        if current_phone and current_phone == other_phone:
            matches.append(f"Phone match: {other.get('Transaction ID')}")

        # Address exact match
        other_addr1 = normalize_for_comparison(other.get('Address 1', ''))
        other_city = normalize_for_comparison(other.get('City', ''))
        other_state = normalize_for_comparison(other.get('State', ''))

        if current_addr1 and current_addr1 == other_addr1 and \
           current_city == other_city and current_state == other_state:
            matches.append(f"Address match: {other.get('Transaction ID')}")

        # Fuzzy name match
        if fuzzy_match(current_name, other.get('Name', ''), threshold):
            matches.append(f"Name match ({threshold*100:.0f}%): {other.get('Transaction ID')}")

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
    print(f"\n📋 Processing: {input_file}")

    # Load configs
    rules = load_rules()
    reference = load_reference_list()

    # Read input
    try:
        df = pd.read_csv(input_file, dtype=str)
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return

    print(f"Found {len(df)} records")

    # Convert to list of dicts for processing
    records = df.to_dict('records')

    # Initialize output columns
    df['Validation_Tier'] = ''
    df['Issues'] = ''
    df['Suggested_Modifications'] = ''

    # Process each record
    for idx, record in enumerate(records):
        validation_results = {}
        suggestions = []
        issues = []

        # Validate email
        tier, reason, suggestion = validate_email(record.get('Email', ''), rules, reference)
        validation_results['email'] = {'tier': tier, 'reason': reason}
        if reason:
            issues.append(f"Email: {reason}")
        if suggestion:
            suggestions.append(suggestion)

        # Validate phone
        tier, reason, suggestion = validate_phone(record.get('Phone', ''), rules)
        validation_results['phone'] = {'tier': tier, 'reason': reason}
        if reason:
            issues.append(f"Phone: {reason}")
        if suggestion:
            suggestions.append(suggestion)

        # Validate amount
        tier, reason, suggestion = validate_amount(record.get('Amount', ''), reference)
        validation_results['amount'] = {'tier': tier, 'reason': reason}
        if reason:
            issues.append(f"Amount: {reason}")
        if suggestion:
            suggestions.append(suggestion)

        # Validate address
        tier, reason = validate_address(record)
        validation_results['address'] = {'tier': tier, 'reason': reason}
        if reason:
            issues.append(f"Address: {reason}")

        # Validate name
        tier, reason = validate_name(record.get('Name', ''), reference)
        validation_results['name'] = {'tier': tier, 'reason': reason}
        if reason:
            issues.append(f"Name: {reason}")

        # Check for duplicates
        is_dup, dup_info = check_duplicates(record, records, rules)
        if is_dup:
            issues.append(f"Duplicate: {dup_info}")
            validation_results['duplicate'] = {'tier': 'WARNING', 'reason': dup_info}

        # Assign tier
        tier = assign_tier(validation_results)

        # Write results
        df.at[idx, 'Validation_Tier'] = tier
        df.at[idx, 'Issues'] = "; ".join(issues) if issues else "None"
        df.at[idx, 'Suggested_Modifications'] = "; ".join(suggestions) if suggestions else ""

        # Print progress
        status = "✓" if tier == 'PASS' else "⚠" if tier == 'WARNING' else "✗"
        print(f"  {status} [{idx+1}/{len(records)}] {record.get('Name', 'Unknown')} - {tier}")

    # Reorder columns: put validation results first, keep original data after
    orig_cols = [c for c in df.columns if c not in ['Validation_Tier', 'Issues', 'Suggested_Modifications']]
    new_order = ['Validation_Tier', 'Issues', 'Suggested_Modifications'] + orig_cols
    df = df[new_order]

    # Write output
    df.to_csv(output_file, index=False)
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
