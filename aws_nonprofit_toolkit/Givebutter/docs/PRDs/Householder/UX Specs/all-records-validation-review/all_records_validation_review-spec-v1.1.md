# Householder v1.1 — Review Screen UX Refinement Implementation

## Objective

Implement the review-screen refinement with inline editable row fields, autosave, Row Status derivation, Issues recalculation, and Approval with Overrides—all while maintaining raw data immutability.

## Required UX Behavior

The main review table should use this structure:

```
Txn ID | Date | Name | Email | Phone | Amount | Address | Row Status | Issues | Actions
```

### Read-only columns:

```
Txn ID
Row Status
Issues
```

### Editable columns:

```
Date
Name
Email
Phone
Amount
Address
```

### Actions may include:

```
Inspect
More
```

A primary Save Row button is not required for normal operation.

## Autosave Behavior

Autosave should trigger when the user:

```
clicks away from a field
tabs away
presses Enter
moves to another row
clicks another button or navigation item
```

The user should not need to press Enter.

Autosave should:

1. Persist corrected/export values separately from raw source data.
2. Recalculate issues for that row.
3. Refresh the read-only Issues column.
4. Refresh the read-only Row Status column.
5. Show a brief save state such as:
   * Saving…
   * Saved
   * Could not save

If autosave fails, do not silently discard the user's typed value.

## Row Status

Add a read-only Row Status column with these values:

```
No issues
Warning
Blocking
Overridden
```

Row Status should be system-derived.

### Behavior:

```
No issues = no currently detected issues
Warning = only warning/non-blocking issues remain
Blocking = one or more unresolved blocking issues remain
Overridden = file was approved with overrides and this row had remaining issues explicitly accepted
```

Before file approval, do not show Overridden.

After **Approve with Overrides**, affected rows should change to:

```
Row Status: Overridden
Issues: <issue name> — Overridden
```

If a row later has a new unresolved blocking issue, Blocking should take priority over Overridden.

## Issues Column

Restore or preserve the read-only Issues column.

The reviewer must be able to see all inferred row issues without clicking Inspect.

### Examples:

```
Missing phone
Invalid email
Email typo
Phone format
Possible duplicate
Possible household
Warning
Blocking
Missing phone — Overridden
Email typo — Overridden
```

The Issues column must remain read-only.

Reviewers should never manually edit, delete, or clear issue badges.

Issues should be derived from:

```
raw source values
+ saved reviewer corrections
= effective row values
→ system-derived issue badges
```

If a correction resolves an issue, the badge disappears after autosave and revalidation.

## Approval Flow

Add or refine the batch/file-level action:

```
Approve File
```

If no issues remain, approval may proceed directly.

If any issues remain, show a confirmation modal:

```
This file still has unresolved issues.

Rows with remaining issues:
• Row 1 — Missing phone
• Row 5 — Possible duplicate
• Row 8 — Email typo

Approving means you accept these remaining issues as-is for export.

[Cancel] [Approve with Overrides]
```

The confirmation button must say:

```
Approve with Overrides
```

not simply "Continue."

## Approval with Overrides

When the reviewer clicks **Approve with Overrides**, the system should:

1. Approve the file/batch.
2. Mark all remaining issue badges as overridden.
3. Change affected rows' Row Status to Overridden.
4. Preserve the original issue type.
5. Preserve row references and transaction IDs where available.
6. Create an audit record for approval with overrides.
7. Include enough detail to reconstruct exactly what was overridden.

### Example audit detail:

```json
{
  "action": "batch_approved_with_overrides",
  "overrides": [
    {
      "row_number": 1,
      "transaction_id": "TX001",
      "issue": "Missing phone"
    },
    {
      "row_number": 5,
      "transaction_id": "TX005",
      "issue": "Possible duplicate"
    }
  ]
}
```

## Export Behavior

Export should use effective row values:

```
reviewer correction if present
otherwise raw source value
```

Export must not mutate raw source data.

If the reviewer approved with overrides, export may proceed with remaining issue values as-is.

If the existing export format already supports review notes or metadata, it may include notes such as:

```
Missing phone overridden
Email typo overridden
```

Do not introduce a new export format unless explicitly approved.

## Partial Review / Switching Files

If the reviewer edits some rows and switches to another file:

```
The partially reviewed file remains in review/processing.
Saved corrections persist.
Remaining issue badges persist.
Row Status values persist or are derived again.
The file is not approved, rejected, flagged, moved to follow-up, or exported unless the reviewer explicitly takes that action.
```

## Inspect Behavior

Inspect should remain available, but it should not be required for routine correction.

Inspect may show:

```
full row details
original CSV value
current corrected/export value
audit trail
issue explanations
source traceability
```

## Guardrails

Do not add or introduce:

```
CRM/Givebutter API calls
credentials
writeback
auth/RBAC
bulk actions
background jobs
new export formats
raw source-data mutation
contact merge
contact deletion
household_id assignment
cross-import matching
master contacts
master households
```

The core rule remains:

```
Raw data stays unchanged.
Reviewer corrections are stored separately.
Export uses corrected values where present.
```

## Tests Required

Add or update tests for:

1. Review table renders Row Status column.
2. Row Status column is read-only.
3. Row Status shows No issues when no issues exist.
4. Row Status shows Warning when only non-blocking issues exist.
5. Row Status shows Blocking when blocking issues exist.
6. Row Status changes to Overridden after Approval with Overrides.
7. Review table renders Issues column.
8. Issues column is read-only.
9. Transaction ID is read-only.
10. Date, Name, Email, Phone, Amount, and Address are editable.
11. Autosave occurs on blur/click-away.
12. Autosave persists corrected/export values separately from raw source data.
13. Raw source values are not changed.
14. Revalidation removes resolved issue badges.
15. Remaining issue badges persist.
16. Approve File without issues approves directly.
17. Approve File with remaining issues shows modal.
18. Approve with Overrides records override details.
19. Overridden issue badges are displayed after approval.
20. Audit log records approval with overrides.
21. Export uses corrected/export values.
22. Partial review state survives navigation away and back.
23. Existing Inspect behavior still works.
24. Full test suite passes.

## Required Test Command

Run:

```bash
pytest tests/unit tests/integration -q
```

Expected baseline:

```
1206 passing (1202 baseline + 4 new from v1.0 inline edits)
```

If the result differs, stop and report the exact output.

---

**Spec Version:** v1.1  
**Status:** Pre-Implementation Phase Complete  
**Date:** 2026-06-13
