#!/usr/bin/env python3
"""
Givebutter export → household records with fuzzy matching, nickname resolution, and conflict detection.
"""
import csv
import re
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

# Nickname mappings
NICKNAMES = {
    'bob': 'robert', 'bobby': 'robert', 'rob': 'robert', 'r.': 'robert',
    'jen': 'jennifer', 'jenny': 'jennifer', 'j.': 'jennifer',
    'dave': 'david', 'dav': 'david',
    'tom': 'thomas', 'tommy': 'thomas', 't.': 'thomas',
    'liz': 'elizabeth', 'bess': 'elizabeth', 'beth': 'elizabeth',
    'bill': 'william', 'will': 'william', 'liam': 'william',
    'jim': 'james', 'jimmy': 'james',
    'dick': 'richard', 'rick': 'richard',
    'dan': 'daniel',
    'ron': 'ronald',
    'mike': 'michael', 'mick': 'michael',
    'sam': 'samuel',
}

def normalize_email(email):
    """Lowercase and clean email."""
    return email.lower().strip() if email else ""

def normalize_phone(phone):
    """Strip all non-digits from phone."""
    if not phone:
        return ""
    return re.sub(r'\D', '', phone)

def normalize_address(address):
    """Fuzzy normalize address: St→Street, Ave→Avenue, Apt→Apartment, etc."""
    if not address:
        return ""
    addr = address.strip()
    # Common abbreviations
    addr = re.sub(r'\bSt\.?\b', 'Street', addr, flags=re.IGNORECASE)
    addr = re.sub(r'\bAve\.?\b', 'Avenue', addr, flags=re.IGNORECASE)
    addr = re.sub(r'\bRd\.?\b', 'Road', addr, flags=re.IGNORECASE)
    addr = re.sub(r'\bDr\.?\b', 'Drive', addr, flags=re.IGNORECASE)
    addr = re.sub(r'\bLn\.?\b', 'Lane', addr, flags=re.IGNORECASE)
    addr = re.sub(r'\bApt\.?\b|#', 'Apt', addr, flags=re.IGNORECASE)
    addr = re.sub(r'\bSF\b', 'San Francisco', addr, flags=re.IGNORECASE)
    addr = re.sub(r'\bCA\b', 'California', addr, flags=re.IGNORECASE)
    # Remove extra whitespace and punctuation
    addr = re.sub(r'[^\w\s]', '', addr)
    addr = ' '.join(addr.split()).upper()
    return addr

def normalize_name(name):
    """Normalize name: lowercase, trim, remove extra spaces."""
    if not name:
        return ""
    return ' '.join(name.strip().split()).lower()

def resolve_nickname(first_name):
    """Resolve nicknames to canonical names."""
    normalized = normalize_name(first_name)
    canonical = NICKNAMES.get(normalized, normalized)
    return canonical.title() if canonical else ""

def string_similarity(a, b):
    """Return similarity ratio 0-1."""
    if not a or not b:
        return 0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def extract_house_number(addr):
    """Extract house number from address."""
    if not addr:
        return None
    match = re.match(r'^(\d+)', addr.strip())
    return match.group(1) if match else None


def fuzzy_match_address(addr1, addr2, threshold=0.85):
    """Fuzzy match addresses. House numbers must match exactly before comparing streets."""
    if not addr1 or not addr2:
        return False

    # Extract house numbers
    house1 = extract_house_number(addr1)
    house2 = extract_house_number(addr2)

    # House numbers must match exactly (or both missing)
    if house1 and house2 and house1 != house2:
        return False

    norm1 = normalize_address(addr1)
    norm2 = normalize_address(addr2)
    similarity = string_similarity(norm1, norm2)
    return similarity >= threshold

def get_email_domain(email):
    """Extract domain from email."""
    if not email or '@' not in email:
        return None
    return email.lower().split('@')[1]


def get_phone_area(phone):
    """Extract area code (first 3 digits) from phone."""
    if not phone:
        return None
    digits = re.sub(r'\D', '', phone)
    return digits[:3] if len(digits) >= 3 else None


def merge_donors(donors):
    """Group donors into households using fuzzy matching."""
    households = {}  # household_id -> list of donor dicts
    household_id = 0
    id_to_household = {}  # donor_id -> household_id

    for donor in donors:
        if donor['donation_id'] in id_to_household:
            continue

        # Start new household
        household = [donor]
        household_id += 1
        households[household_id] = household
        id_to_household[donor['donation_id']] = household_id

        # Find matches in remaining unassigned donors
        for other in donors:
            if other['donation_id'] in id_to_household:
                continue

            # Check if same person
            same_email = (donor['email'] and other['email'] and
                         normalize_email(donor['email']) == normalize_email(other['email']))
            same_phone = (donor['phone'] and other['phone'] and
                         normalize_phone(donor['phone']) == normalize_phone(other['phone']))

            # Check name + address match
            same_first_canonical = (resolve_nickname(donor['first_name']).lower() ==
                                   resolve_nickname(other['first_name']).lower())
            same_last = (normalize_name(donor['last_name']) ==
                        normalize_name(other['last_name']))
            same_address = fuzzy_match_address(
                f"{donor['address']} {donor['city']} {donor['state']}",
                f"{other['address']} {other['city']} {other['state']}"
            )

            # Same person: email match, phone match, or name+address match
            is_same_person = (same_email or same_phone or
                            (same_first_canonical and same_last and same_address))

            # Spouse: same last name AND same address AND (shared email domain OR shared phone area)
            same_email_domain = (get_email_domain(donor['email']) and
                                get_email_domain(donor['email']) == get_email_domain(other['email']))
            same_phone_area = (get_phone_area(donor['phone']) and
                              get_phone_area(donor['phone']) == get_phone_area(other['phone']))

            is_spouse = (not is_same_person and same_last and same_address and
                        (same_email_domain or same_phone_area) and
                        resolve_nickname(donor['first_name']).lower() !=
                        resolve_nickname(other['first_name']).lower())

            if is_same_person or is_spouse:
                household.append(other)
                id_to_household[other['donation_id']] = household_id

    return households


def get_original_first_names(donors):
    """Extract all unique first name variations from donors."""
    first_names = []
    for d in donors:
        if d.get('first_name', '').strip():
            first_names.append(d['first_name'].strip())
    return '; '.join(list(dict.fromkeys(first_names)))


def get_original_last_names(donors):
    """Extract all unique last name variations from donors."""
    last_names = []
    for d in donors:
        if d.get('last_name', '').strip():
            last_names.append(d['last_name'].strip())
    return '; '.join(list(dict.fromkeys(last_names)))


def address_similarity(addr1, addr2):
    """Calculate address similarity 0-1."""
    if not addr1 or not addr2:
        return 0
    norm1 = normalize_address(addr1)
    norm2 = normalize_address(addr2)
    return string_similarity(norm1, norm2)


def detect_moved_donor(donors):
    """
    Detect if donors are same person who moved.
    Return (is_moved, donor_list) where is_moved indicates address change.
    """
    if len(donors) < 2:
        return False, []

    # Must have same email or phone
    same_email = len(set(normalize_email(d['email']) for d in donors if d['email'])) == 1
    same_phone = len(set(normalize_phone(d['phone']) for d in donors if d['phone'])) == 1

    if not (same_email or same_phone):
        return False, []

    # Check if addresses are different
    addresses = [f"{d['address']} {d['city']} {d['state']}" for d in donors if d['address']]
    if len(set(addresses)) <= 1:
        return False, []

    # Check if address similarities are low (moved, not roommates)
    similarities = []
    for i, addr1 in enumerate(addresses):
        for addr2 in addresses[i+1:]:
            similarities.append(address_similarity(addr1, addr2))

    avg_similarity = sum(similarities) / len(similarities) if similarities else 1.0
    is_moved = avg_similarity < 0.7  # Different enough to be a move

    return is_moved, donors if is_moved else []


def check_name_discrepancy(primary_name, donors, threshold=2):
    """
    Check if any donor's name differs from primary by >threshold characters.
    Returns (has_discrepancy, discrepant_name).
    """
    primary_normalized = primary_name.lower().replace(' ', '')

    for donor in donors:
        donor_name = f"{donor.get('first_name', '')} {donor.get('last_name', '')}".strip()
        donor_normalized = donor_name.lower().replace(' ', '')

        max_len = max(len(primary_normalized), len(donor_normalized))
        if max_len == 0:
            continue

        diff = abs(len(primary_normalized) - len(donor_normalized))
        diff += sum(1 for a, b in zip(primary_normalized, donor_normalized) if a != b)

        if diff > threshold:
            return True, donor_name

    return False, None


def build_enhanced_output(households):
    """
    Convert households to output records with confidence scores,
    original names, and review flags.
    """
    output = []
    review_queue = []

    for hh_id, donors in households.items():
        # Smart confidence scoring based on merge reason
        if len(donors) == 1:
            confidence = 1.0
        else:
            emails = [normalize_email(d['email']) for d in donors if d['email']]
            unique_emails = set(emails)

            phones = [d.get('phone', '').strip() for d in donors if d.get('phone')]
            unique_phones = set(phones)

            last_names = [d['last_name'] for d in donors if d['last_name']]
            unique_last = set(last_names)

            first_names_canonical = [resolve_nickname(d['first_name']).lower()
                                    for d in donors if d['first_name']]
            unique_first_canonical = set(first_names_canonical)

            same_address = all(
                fuzzy_match_address(
                    f"{donors[0]['address']} {donors[0]['city']} {donors[0]['state']}",
                    f"{d['address']} {d['city']} {d['state']}"
                ) for d in donors[1:]
            ) if len(donors) > 1 and donors[0]['address'] else False

            same_email_domain = (get_email_domain(donors[0]['email']) and
                                all(get_email_domain(d['email']) == get_email_domain(donors[0]['email'])
                                    for d in donors[1:] if d['email']))
            same_phone_area = (get_phone_area(donors[0]['phone']) and
                              all(get_phone_area(d['phone']) == get_phone_area(donors[0]['phone'])
                                  for d in donors[1:] if d['phone']))

            is_spouse = (len(unique_last) == 1 and len(unique_first_canonical) > 1 and
                        same_address and (same_email_domain or same_phone_area))

            # PRIORITY: Phone > Email > Spouse > Uncertain
            # Phone matches OVERRIDE email conflicts
            phones_normalized = [normalize_phone(d['phone']) for d in donors if d['phone']]
            unique_phones_normalized = set(phones_normalized) - {''}

            if len(unique_phones_normalized) == 1 and unique_phones_normalized:
                confidence = 0.95  # Same phone OVERRIDES everything
            elif len(unique_emails) == 1 and unique_emails != {""} and unique_emails != {''}:
                confidence = 0.90  # Same email
            elif is_spouse:
                confidence = 0.70  # Spouse
            else:
                confidence = 0.45  # Uncertain

        email_counts = defaultdict(int)
        for d in donors:
            if d['email']:
                email_counts[normalize_email(d['email'])] += 1
        best_email = max(email_counts, key=email_counts.get) if email_counts else ""

        last_names = [d['last_name'] for d in donors if d['last_name']]
        most_common_last = max(set(last_names), key=last_names.count) if last_names else ""

        first_names = [d['first_name'] for d in donors if d['first_name']]
        longest_first = max(first_names, key=len) if first_names else ""
        longest_first = ' '.join(longest_first.strip().split()).title()
        primary_name = f"{longest_first} {most_common_last}".strip()

        original_first_names = get_original_first_names(donors)
        original_last_names = get_original_last_names(donors)

        total_lifetime = sum(float(d['amount']) for d in donors if d['amount'])
        donation_count = len(donors)
        matched_ids = ','.join([d['donation_id'] for d in donors])

        emails = [normalize_email(d['email']) for d in donors if d['email']]
        unique_emails = set(emails)
        conflict = "email_mismatch" if len(unique_emails) > 1 else ""

        has_discrepancy, discrepant_name = check_name_discrepancy(primary_name, donors, threshold=2)

        record = {
            'household_id': f"HH_{hh_id:04d}",
            'primary_name': primary_name,
            'original_first_names': original_first_names,
            'original_last_names': original_last_names,
            'best_email': best_email,
            'total_lifetime': f"${total_lifetime:.2f}",
            'donation_count': donation_count,
            'matched_ids': matched_ids,
            'confidence_score': f"{confidence:.2f}",
            'conflict_flag': conflict,
            'name_discrepancy': "YES" if has_discrepancy else ""
        }

        output.append(record)

        if has_discrepancy or confidence < 0.6 or conflict:
            review_queue.append({
                'household_id': f"HH_{hh_id:04d}",
                'primary_name': primary_name,
                'reason': ', '.join(filter(None, [
                    "name_discrepancy" if has_discrepancy else None,
                    f"low_confidence({confidence:.2f})" if confidence < 0.6 else None,
                    conflict if conflict else None
                ])),
                'original_first_names': original_first_names,
                'original_last_names': original_last_names,
                'matched_ids': matched_ids,
                'confidence_score': f"{confidence:.2f}"
            })

    return (
        sorted(output, key=lambda x: float(x['total_lifetime'].replace('$', '')), reverse=True),
        sorted(review_queue, key=lambda x: float(x['confidence_score']))
    )


if __name__ == "__main__":
    input_file = Path(__file__).parent / "Nonprofit-donor-tech-stack.spreadsheet"
    output_file = Path(__file__).parent / "household_records.csv"
    review_file = Path(__file__).parent / "review_queue.csv"

    # Read input
    donors = []
    with open(input_file) as f:
        reader = csv.DictReader(f)
        donors = list(reader)

    print(f"📊 Read {len(donors)} donation records")

    # Merge into households
    households = merge_donors(donors)
    print(f"🏠 Consolidated into {len(households)} households")

    # Generate enhanced output
    output, review_queue = build_enhanced_output(households)

    # Write main output
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'household_id', 'primary_name', 'original_first_names', 'original_last_names',
            'best_email', 'total_lifetime', 'donation_count', 'matched_ids',
            'confidence_score', 'conflict_flag', 'name_discrepancy'
        ])
        writer.writeheader()
        writer.writerows(output)

    print(f"✓ Output: {output_file}")

    # Write review queue
    if review_queue:
        with open(review_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'household_id', 'primary_name', 'reason', 'original_first_names',
                'original_last_names', 'matched_ids', 'confidence_score'
            ])
            writer.writeheader()
            writer.writerows(review_queue)
        print(f"⚠️  Review queue: {review_file} ({len(review_queue)} items)")
    else:
        print(f"✅ No review items needed")

    print(f"\nTop 5 households by lifetime value:")
    for row in output[:5]:
        print(f"  {row['household_id']}: {row['primary_name']} " +
              f"(conf={row['confidence_score']}, {row['donation_count']} donations, {row['total_lifetime']})")
