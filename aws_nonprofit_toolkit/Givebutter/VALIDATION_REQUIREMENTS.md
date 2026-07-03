# Givebutter CSV Validation Requirements

## Required Fields
These fields **MUST** be present and non-empty. Missing or empty required fields result in **FAIL** tier for the record.

| Field | Behavior | Notes |
|-------|----------|-------|
| **Transaction ID** | Required | Unique identifier for each donation record. Used for duplicate detection. |
| **Date** | Required | Donation/transaction date. Accepted via fuzzy matching (Date, Donation Date, Gift Date, Date Received). |
| **Name** | Required | Minimum 2 characters, max 100 characters. Checked against reference patterns. |
| **Email** | Required | Must contain valid email format: user@domain (@ symbol required, domain cannot be empty). Checked for typos and domain variations. |
| **Amount** | Required | Must be numeric > 0. Checked against typical donation ranges. |

## Optional Fields
These fields are **optional**. Missing columns result in **WARNING** tier (soft flag for reviewer), not FAIL.

| Field | Behavior | Notes |
|-------|----------|-------|
| **Phone** | Optional | If present, must be 10-11 digits (US format). Checked against invalid patterns. If missing, reviewer gets "Add phone numbers" suggestion. |

## Not Actively Validated
These fields are accepted but not actively validated for content (though some are required for presence).

| Field | Notes |
|-------|-------|
| **Address** (Address 1, City, State) | Skipped if any address component is missing. Address validation only runs if all three present. |
| **Campaign** | Accepted via fuzzy matching (Campaign Title, Fund, Campaign, Gift Fund) but content not validated. |
| **Custom Fields** | All unmapped columns pass through unchanged. |

## Validation Review Contract
Validation Review is a review/edit surface, not a second full import revalidator.

- The review screen dynamically validates `amount`, `email`, and `phone` as fields are edited.
- `date` and `address` validation remain at the processor/import stage.
- `campaign` is not part of the dynamic Validation Review model.
- Any future decision to add dynamic `date` or `address` validation on the review screen must be made explicitly and updated across the review UI, autosave validation, export/approval gating, and the relevant tests.

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

## Operator Approval Overrides

When reviewing records in the UI, operators can approve records even if they have FAIL tier validation issues. However, an **override confirmation** is required:

1. User selects "Approved" decision for a FAIL tier record
2. User clicks "Save Decisions"
3. System detects FAIL records being approved
4. **Confirmation dialog appears** showing:
   - Record name
   - Validation failure details
   - Warning: "You are approving [record] despite validation failures"
5. User must confirm to proceed
   - **Confirm**: Record is approved with noted failures
   - **Cancel**: Approval is not saved, user can modify decision

This allows operators to override validation when necessary (e.g., verified duplicate that should be merged) while ensuring they're aware of the data quality implications.

## Suggestion Display Priority

The processor generates suggestions for validation failures and displays them prioritized by impact:

1. **Required Field Failures** (1st priority)
   - Transaction ID, Date, Email, Amount, Name
   - FAIL tier errors that must be resolved

2. **Duplicate Detection** (2nd priority)
   - Records matching existing entries
   - "Review duplicate entries" suggestion

3. **Address Issues** (3rd priority)
   - Incomplete address information (if address fields present in CSV)
   - "Complete address information (street, city, state)" suggestion

4. **Optional Field Issues** (4th priority)
   - Phone format or missing optional data
   - Low-priority recommendations

**Display Limits**: Maximum 5 issues and 5 suggestions are displayed per record to maintain readability. Prioritization ensures critical FAIL-tier failures always appear before optional field warnings.

## Header Mapping Strategy

The processor uses **two-tier column matching**:

1. **Strict Match** — Exact case-sensitive match to Givebutter core headers
   - `Name`, `Email`, `Amount`, `Date`, `Phone`, `Transaction ID`, etc.

2. **Fuzzy Match** — Case-insensitive match to common variations (in addition to strict matches)
   - **Transaction ID**: `Donation ID`, `Gift ID`, `Contribution ID`, `donation_id`, `gift_id`
   - **Name**: `Donor Name`, `Full Name`, `Donor`, `First and Last Name`, `donor_name`, `full_name`
   - **Email**: `Email Address`, `Primary Email`, `Contact Email`, `email_address`, `primary_email`
   - **Phone**: `Phone Number`, `Contact Phone`, `phone_number`, `contact_phone`
   - **Date**: `Donation Date`, `donation_date`, `Gift Date`, `Date Received`, `gift_date`, `date_received`
   - **Amount**: Only core header `Amount` (strict match, no fuzzy fallback)
   - **Campaign**: `Fund`, `Campaign`, `Gift Fund`, `Donation Fund`, `campaign_title`

## CSV Header Examples

Valid headers that will be recognized:

```csv
# Exact core headers (case-sensitive, must match exactly)
Name,Email,Amount,Date,Transaction ID,Phone,Campaign Title

# Fuzzy variations (case-insensitive, support underscores and spaces)
Donor Name,Email Address,Amount,Donation Date,Donation ID,Phone Number,Campaign
donor_name,email_address,Amount,donation_date,donation_id,phone_number,campaign_title
Full Name,Primary Email,Amount,Gift Date,Gift ID,Contact Phone,Fund
```

**Note**: `Amount` requires exact case match (no fuzzy fallback). Use `Amount` not `amount` or `AMOUNT`.

## Testing CSV Format Variations

When creating test CSVs, verify:
- ✅ Lowercase headers work (case-insensitive fuzzy match)
- ✅ Mixed case headers work (fuzzy match)
- ✅ Missing optional columns (phone) → WARNING
- ✅ Missing required columns (name, email, amount) → FAIL
- ✅ Email typos flagged during review (not at upload)
- ✅ Amount validation happens in review queue

See `tests/e2e/test_e2e_csv_format_variations.py` for examples.
