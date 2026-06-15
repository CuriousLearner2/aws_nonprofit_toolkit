# Email Validation Architecture

## Overview

The Householder v1.1 email validation uses a **two-tier approach** to balance accuracy with usability:

1. **Tier 1: Recognized Domains** — Strict validation for common email providers
2. **Tier 2: Unrecognized Domains** — Lenient validation for corporate/regional emails

---

## Common Typo Domains (Detected First)

Before checking recognized or unrecognized domains, we check for known typo domains that are commonly misspelled:

```python
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
```

**Behavior:**
- Input: `jane.smith@gamil.com` → ❌ Flagged as typo
- Suggestion: "Did you mean gmail.com?"
- Input: `jane.smith@gmail.com` (with raw `jane.smith@gamil.com`) → ✅ Issue resolved (correction made)

This check applies to **ALL emails**, regardless of whether the domain is recognized or not.

---

## Tier 1: Recognized Domains (Strict Validation)

### Top 30 Recognized Email Domains

```python
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
    'mail.ru',      # Russia
    'yandex.com',   # Russia
    'qq.com',       # China
    'sina.com',     # China
    '163.com',      # China
}
```

### Typo Detection

For recognized domains, we catch these known typos:

| Pattern | Example | Caught As |
|---------|---------|-----------|
| gmial | gmial.com | Gmail typo (letter swap) |
| gmal | gmal.com | Gmail typo (missing i) |
| yahooo | yahooo.com | Yahoo typo (extra o) |
| hotmial | hotmial.com | Hotmail typo (letter swap) |
| gmai | gmai.com | Incomplete Gmail |

**Behavior:**
- Input: `jane.smith@gmial.com` with raw value `jane.smith@gmial.com` (no correction)
- Result: ❌ Issue not resolved (typo detected, no correction made)
- Input: `jane.smith@gmail.com` with raw value `jane.smith@gmial.com` (corrected)
- Result: ✅ Issue resolved (typo corrected to valid format)

---

## Tier 2: Unrecognized Domains (Lenient Validation)

Any domain NOT in RECOGNIZED_EMAIL_DOMAINS is accepted if it has valid canonical format.

### Valid Unrecognized Domains

```
user@mycompany.com         ✅ Corporate email
user@mail.cz               ✅ Regional provider
user@university.edu        ✅ University email
user@company.co.uk         ✅ Multi-part domain
john.doe@startup.io        ✅ Modern TLD
```

**Behavior:**
- Input: `jane.smith@mail.cz` (Czech provider, not recognized)
- Result: ✅ Accepted without issues (format valid, domain allowed)

---

## Canonical Format Validation

ALL emails, recognized or not, must satisfy the canonical format:
`localpart@domain.tld`

### Format Requirements

1. **Exactly one @** — Separates local part from domain
2. **Non-empty local part** — At least one character before @
3. **Non-empty domain** — At least one character after @
4. **At least one dot in domain** — Separates domain name from TLD
5. **Non-empty TLD** — At least one character after final dot

### Invalid Formats (Rejected)

```
@@gmail.com           ❌ Double @ symbol
@gmail.com            ❌ Missing local part
user@                 ❌ Missing domain
user@gmail            ❌ Missing TLD (no dot)
usergmail.com         ❌ Missing @ symbol
user..name@gmail.com  ❌ Consecutive dots in local part
```

---

## Implementation

### Code Location

File: `scripts/householder/issue_recalculation_service.py`

Functions:
- `is_issue_resolved()` — Validates email format and detects typos
- `_get_email_suggestion()` — Returns suggested correction for typo domains
- `recalculate_row_issues()` — Builds issue list with suggestions

### Validation Flow

```
Email received: jane.smith@gamil.com

1. Check canonical format
   ✓ Has exactly one @
   ✓ Has local part
   ✓ Has domain with dot
   
2. Extract domain: gamil.com

3. Check common typo domains FIRST
   ✓ YES: gamil.com is in COMMON_TYPO_DOMAINS → gmail.com
   
4. Check if typo was corrected
   ✓ Raw value is 'jane.smith@gamil.com' (no correction)
   
5. Generate suggestion
   ✓ "Did you mean gmail.com?"
   
6. Result: ❌ Issue not resolved (typo detected)
```

**Alternative flow with correction:**

```
Email: jane.smith@gmail.com
Raw: jane.smith@gamil.com

1. Extract domain: gmail.com

2. Check common typo domains
   ✓ gmail.com NOT in COMMON_TYPO_DOMAINS
   
3. Check if domain recognized
   ✓ YES: gmail.com is in RECOGNIZED_EMAIL_DOMAINS
   
4. No invalid patterns detected

5. Result: ✅ Issue resolved (typo corrected to valid domain)
```

---

## Scenarios

### Scenario 1: Common Typo Domain

```
Raw value: jane.smith@gamil.com (typo - i-l swap)
User enters: jane.smith@gamil.com (no correction)
Issue: ❌ Detected - "Possible typo. Did you mean gmail.com?"
Row Status: Warning

After correction:
User enters: jane.smith@gmail.com
Issue: ✅ No issues (correction accepted)
Row Status: No issues
```

### Scenario 2: Recognized Domain with Typo

```
Raw value: jane.smith@gmial.com (typo in database)
User correction: jane.smith@gmail.com
Issue before: ❌ Invalid Format - "Possible typo. Did you mean gmail.com?"
Issue after: ✅ No issues (typo detected and corrected)
```

### Scenario 2: Recognized Domain, No Correction

```
Raw value: jane.smith@gmial.com (typo)
User keeps: jane.smith@gmial.com (no correction)
Issue: ❌ Still flagged (typo detected, correction not made)
```

### Scenario 3: Unrecognized Domain (Corporate)

```
Raw value: john@test.com
User correction: john@mycompany.com
Issue: ✅ No issues (format valid, domain allowed even if not recognized)
```

### Scenario 4: Invalid Format

```
User enters: jane.smith@@gmail.com (double @)
Issue: ❌ Invalid format detected
```

---

## Test Coverage

All scenarios tested in: `tests/integration/test_phase2_backend_api.py`

Test function: `TestIssueRecalculation::test_is_issue_resolved_logic()`

### Test Cases

```python
# Recognized domain typo
is_issue_resolved('email', 'user@gmial.com', 'possible_typo', 
                 raw_value='user@gmial.com') → False (no correction)
is_issue_resolved('email', 'user@gmail.com', 'possible_typo',
                 raw_value='user@gmial.com') → True (corrected)

# Unrecognized domain
is_issue_resolved('email', 'user@mycompany.com', 'possible_typo',
                 raw_value='user@test.com') → True (format valid)

# Invalid format
is_issue_resolved('email', 'user@@gmail.com', 'possible_typo',
                 raw_value='user@gmial.com') → False (invalid format)
```

---

## Design Rationale

### Why Two Tiers?

1. **Accuracy**: Common email providers have known typos we can reliably detect
2. **Usability**: Doesn't reject legitimate corporate/international emails
3. **Maintainability**: Only 30 domains need strict validation rules
4. **Scalability**: Format validation catches all truly malformed emails

### Why Format Validation?

The canonical email format check ensures basic validity for ALL domains:
- Catches obvious mistakes (missing @, double @, etc.)
- Works for any domain (recognized or not)
- Simple to understand and maintain
- Non-controversial (technically correct)

### Why Not a Full RFC 5321 Parser?

Full RFC 5321 email validation is complex and allows unusual formats like:
- `"john..doe"@example.com` (quoted local part with consecutive dots)
- `user+tag@example.com` (plus addressing)
- `mailbox@[192.168.1.1]` (IP address domain)

For a donation system, the canonical format is sufficient and more user-friendly.

---

## Future Enhancements

1. **Whitelist-based approach** — Add common domains by region/industry
2. **DNS validation** — Verify domain MX records exist (requires external lookup)
3. **Regex refinement** — Add more typo patterns as user reports come in
4. **Disposable email detection** — Flag known disposable email services
