#!/usr/bin/env python3
"""
Build reference list from operator-approved donation records.

This script scans the review/approved/ folder and extracts patterns
from approved donations to create a reference_list.json that can be
used to validate incoming records.

Usage:
    python3 scripts/build_reference_list.py
"""

import json
from pathlib import Path
import pandas as pd
from datetime import datetime, timezone
import statistics
import re

BASE_DIR = Path(__file__).resolve().parents[1]  # Givebutter/
APPROVED_DIR = BASE_DIR / "review" / "approved"
REFERENCE_FILE = BASE_DIR / "config" / "reference_list.json"

def extract_email_domain(email: str) -> str:
    """Extract domain from email."""
    if '@' not in email:
        return None
    return email.split('@')[-1].lower()

def extract_tld(domain: str) -> str:
    """Extract TLD from domain."""
    if not domain or '.' not in domain:
        return None
    # Handle multi-part TLDs like .co.uk
    parts = domain.split('.')
    if len(parts) >= 3 and parts[-2] in ['co', 'com', 'org']:
        return f"{parts[-2]}.{parts[-1]}"
    return parts[-1]

def validate_amount(amount_str: str) -> float:
    """Try to parse amount, return float or None."""
    try:
        cleaned = str(amount_str).replace('$', '').replace(',', '').strip()
        return float(cleaned)
    except:
        return None

def build_reference_list():
    """Scan approved records and build reference patterns."""

    approved_files = list(APPROVED_DIR.glob('*.csv'))

    if not approved_files:
        print(f"No approved records found in {APPROVED_DIR}")
        print("Creating empty reference list template...")
        print(f"Approved records will be added as operators move them to {APPROVED_DIR}")
        return load_default_reference()

    print(f"Found {len(approved_files)} approved record files")

    emails = []
    domains = set()
    tlds = set()
    amounts = []
    names = []

    for csv_file in approved_files:
        try:
            df = pd.read_csv(csv_file, dtype=str).fillna('')
            print(f"\n  Processing: {csv_file.name}")

            for idx, row in df.iterrows():
                # Extract email domain
                email = row.get('email', '').strip()
                if email and '@' in email:
                    domain = extract_email_domain(email)
                    if domain:
                        domains.add(domain)
                        tld = extract_tld(domain)
                        if tld:
                            tlds.add(tld)
                    emails.append(email)

                # Extract amount
                amount = validate_amount(row.get('amount', ''))
                if amount is not None and amount > 0:
                    amounts.append(amount)

                # Extract name
                name = row.get('name', '').strip()
                if name:
                    names.append(name)

        except Exception as e:
            print(f"  Error processing {csv_file.name}: {e}")
            continue

    # Build statistics
    reference = {
        "version": "1.0",
        "description": "Reference list built from operator-approved donation records",
        "generated_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "record_count": len(emails),

        "email_domains": sorted(list(domains)),
        "email_tlds": sorted(list(tlds)),

        "amount_statistics": {
            "min": round(min(amounts), 2) if amounts else None,
            "max": round(max(amounts), 2) if amounts else None,
            "mean": round(statistics.mean(amounts), 2) if amounts else None,
            "median": round(statistics.median(amounts), 2) if amounts else None,
            "p25": round(sorted(amounts)[len(amounts)//4], 2) if len(amounts) > 3 else None,
            "p75": round(sorted(amounts)[3*len(amounts)//4], 2) if len(amounts) > 3 else None,
            "p90": round(sorted(amounts)[9*len(amounts)//10], 2) if len(amounts) > 9 else None,
            "valid_range": [1, max(amounts) * 1.5] if amounts else [1, 100000]
        },

        "name_patterns": {
            "min_length": min(len(n) for n in names) if names else 2,
            "max_length": max(len(n) for n in names) if names else 100,
            "must_have_words": 1,
            "allowed_characters": "a-zA-Z0-9 .-'"
        },

        "notes": f"Built from {len(approved_files)} approved CSV files with {len(emails)} valid records"
    }

    return reference

def load_default_reference():
    """Load or create default reference list."""
    if REFERENCE_FILE.exists():
        with open(REFERENCE_FILE) as f:
            return json.load(f)

    return {
        "version": "1.0",
        "description": "Default reference list (no approved records yet)",
        "generated_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "record_count": 0,
        "email_domains": [],
        "email_tlds": ["com", "org", "net", "edu", "gov"],
        "amount_statistics": {
            "min": 1,
            "max": 100000,
            "mean": None,
            "median": None,
            "p25": None,
            "p75": None,
            "p90": None,
            "valid_range": [1, 100000]
        },
        "name_patterns": {
            "min_length": 2,
            "max_length": 100,
            "must_have_words": 1,
            "allowed_characters": "a-zA-Z0-9 .-'"
        },
        "notes": "Default patterns. Update by moving approved records to review/approved/"
    }

def save_reference_list(reference: dict):
    """Save reference list to config file."""
    with open(REFERENCE_FILE, 'w') as f:
        json.dump(reference, f, indent=2)
    print(f"\n✓ Reference list saved to {REFERENCE_FILE}")
    print(f"  Records: {reference['record_count']}")
    print(f"  Email domains: {len(reference['email_domains'])}")
    print(f"  Email TLDs: {len(reference['email_tlds'])}")
    if reference['record_count'] > 0:
        stats = reference['amount_statistics']
        print(f"  Amount range: ${stats['min']} - ${stats['max']}")

if __name__ == '__main__':
    print("Building reference list from approved records...\n")
    reference = build_reference_list()
    save_reference_list(reference)
