# Givebutter CSV Validation Requirements

## Required Fields
These fields **MUST** be present and non-empty. Missing or empty required fields result in **FAIL** tier for the record.

| Field | Behavior | Notes |
|-------|----------|-------|
| **Name** | Required | Minimum 2 characters, max 100 characters. Checked against reference patterns. |
| **Email** | Required | Must contain valid email format (@ symbol). Checked for typos and domain variations. |
| **Amount** | Required | Must be numeric > 0. Checked against typical donation ranges. |

## Optional Fields
These fields are **optional**. Missing columns result in **WARNING** tier (soft flag for reviewer), not FAIL.

| Field | Behavior | Notes |
|-------|----------|-------|
| **Phone** | Optional | If present, must be 10-11 digits (US format). Checked against invalid patterns. If missing, reviewer gets "Add phone numbers" suggestion. |

## Not Actively Validated
These fields are accepted but not actively validated for presence or content.

| Field | Notes |
|-------|-------|
| **Address** (Address 1, City, State) | Skipped if any address component is missing. Address validation only runs if all three present. |
| **Date** | Accepted via fuzzy matching (Date, Donation Date, Gift Date, Date Received) but not validated for format/presence. |
| **Campaign** | Accepted via fuzzy matching but not validated. |
| **Custom Fields** | All unmapped columns pass through unchanged. |

## Validation Tier Logic

### FAIL (Hard Error)
Record cannot be accepted without fixing:
- Required field missing or empty
- Invalid format (e.g., email without @)
- Data validation fails (e.g., amount ≤ 0)

### WARNING (Soft Flag)
Record accepted but flagged for reviewer attention:
- Optional field missing (e.g., phone)
- Possible data quality issue (e.g., email typo, amount outside typical range)
- Duplicate detection

### PASS
No issues found. Record ready for review decision.

## Header Mapping Strategy

The processor uses **two-tier column matching**:

1. **Strict Match** — Exact case-sensitive match to Givebutter core headers
   - `Name`, `Email`, `Amount`, `Date`, etc.

2. **Fuzzy Match** — Case-insensitive match to common variations
   - `name` (lowercase), `Donor Name`, `Full Name` all match `Name`
   - `email`, `Email Address`, `Contact Email` all match `Email`
   - `amount`, `AMOUNT` all match `Amount`
   - `donation_date`, `Donation Date`, `Gift Date` all match `Date`

## CSV Header Examples

Valid headers that will be recognized:

```csv
# Exact core headers
Name,Email,Amount,Date,Campaign Title,Phone

# Fuzzy variations (all work)
Donor Name,Email Address,Amount,Donation Date,Campaign,Phone Number
donor_name,email,amount,donation_date,campaign,phone
Full Name,Primary Email,AMOUNT,gift_date,Fund,Contact Phone
```

## Testing CSV Format Variations

When creating test CSVs, verify:
- ✅ Lowercase headers work (case-insensitive fuzzy match)
- ✅ Mixed case headers work (fuzzy match)
- ✅ Missing optional columns (phone) → WARNING
- ✅ Missing required columns (name, email, amount) → FAIL
- ✅ Email typos flagged during review (not at upload)
- ✅ Amount validation happens in review queue

See `tests/e2e/test_e2e_csv_format_variations.py` for examples.
