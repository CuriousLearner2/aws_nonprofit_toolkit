# Reviewer Workflow Guide

**Version:** 1.1  
**For:** Users making review decisions in Householder

---

## Review Pages & Decision Types

### 1. Validation Review
**Purpose:** Resolve data quality issues that prevent export

**What you'll see:**
- Records with validation errors (invalid email, missing required field, etc.)
- Error details explaining what's wrong
- Option to override (mark as valid) or confirm (mark as invalid)

**Decision types:**
- **Mark as Valid** — Override validation error, include in export
- **Mark as Invalid** — Confirm error is real, exclude from export
- **Defer** — Not sure; re-visit later

**Tips:**
- Invalid records are flagged; you must decide what to do
- Validation is about data format, not business logic
- Use notes to explain why you're overriding (e.g., "Email is legacy, customer confirmed valid")
- Defer is useful when uncertain; deferred issues may require confirmation before export
- Invalid records still appear in audit trail; not deleted

**Exit condition:** All validation items decided

---

### 2. Normalizations Review
**Purpose:** Accept or reject suggested data improvements

**What you'll see:**
- Records with normalization suggestions (email format, phone standardization, etc.)
- Current value vs. suggested value side-by-side
- Confidence score for suggestion

**Decision types:**
- **Accept** — Use suggested normalized value in export
- **Reject** — Keep original value in export

**Tips:**
- Accepted normalizations affect only the export; original data stays in database
- Rejecting is safe; original appears in export
- Low confidence suggestions might warrant rejection
- Use notes for edge cases (e.g., "International format; keep as-is")

**Exit condition:** All normalization items decided (or no normalizations exist)

---

### 3. Duplicates Review
**Purpose:** Identify which records represent the same person

**What you'll see:**
- Pairs of records that might be duplicates
- Side-by-side comparison of names, emails, addresses, phone numbers
- Evidence showing why system flagged as duplicate

**Decision types:**
- **Same Person** — Records represent same donor; mark as duplicate
- **Different People** — Records are different people; keep both
- **Defer** — Not sure; re-visit later

**Tips:**
- Duplicate decisions affect export deduplication
- Same Person designation means one record will be marked as duplicate in export
- You're not deleting either record; just marking relationship
- Defer is useful when uncertain; re-visit after other decisions
- Use notes to document your reasoning (e.g., "Same email address but different name—customer confirmed is spouse with different name")

**Exit condition:** All duplicate items decided

---

### 4. Households Review
**Purpose:** Confirm or reject suggested household groupings

**What you'll see:**
- Groups of records that appear related (same address, family name patterns, etc.)
- Summary of grouping basis (e.g., "3 records, same address, similar names")
- List of records in suggested household

**Decision types:**
- **Confirm** — Grouping is correct; appears in export as household
- **Reject** — Grouping doesn't make sense; don't group these records

**Tips:**
- Household grouping is metadata; doesn't change individual records
- Confirmed households appear in export (useful for CRM organization)
- Rejection removes grouping; records remain independent
- Use notes if rejecting (e.g., "Different families, same address temporarily")

**Exit condition:** All household items decided

---

## Navigation Tips

### From Dashboard
1. Click batch name to go to **Batch Dashboard**
2. Dashboard shows count of pending items in each queue
3. Click **Review [Queue Name]** button to enter that queue

### Within Review Queues
- **Item Navigation:** Previous/Next buttons move between items in queue
- **Back to Dashboard:** Return to batch dashboard
- **See Queue Status:** Always visible at top (e.g., "3 of 42 items decided")
- **Keyboard Shortcuts:** (If available) Check help in queue

### Checking Progress
- **Dashboard** shows total pending per category
- **Export Readiness** shows if batch is ready (all queues complete)
- **Audit Trail** shows all your decisions (and other reviewers')

---

## Common Decision Scenarios

### Scenario 1: Invalid Email But Customer Is Known
**Situation:** Validation shows invalid email format. You know the customer.

**Decision:** Mark as Valid (override), add note: "Email format unusual but customer confirmed valid"

**Result:** Record included in export; decision logged in audit trail

---

### Scenario 2: Unsure About Normalization
**Situation:** System suggests changing "john smithe" → "John Smith". You're not confident.

**Decision:** Reject normalization; original value stays in export

**Result:** Export uses "john smithe"; no risk from wrong correction

---

### Scenario 3: Two Records Look Like Same Person But Unsure
**Situation:** Records have similar names and address but slightly different phone.

**Decision:** Defer decision; re-visit after other reviews

**Result:** Item stays in queue; can return to it later

---

### Scenario 4: Clear Duplicate
**Situation:** Same email, very similar name, same address.

**Decision:** Mark as Same Person

**Result:** Both records stay in database; export notes this as duplicate; CRM can decide merge logic

---

### Scenario 5: Unrelated Household Grouping
**Situation:** System suggests 4 records as household; you recognize they're lodgers (different families).

**Decision:** Reject household

**Result:** Records remain independent; no grouping in export

---

## Decision Best Practices

### Do:
- ✓ Add notes explaining non-obvious decisions
- ✓ Take breaks if reviewing large batches
- ✓ Use Defer if uncertain (can revisit later)
- ✓ Check Export Preview before final export
- ✓ Reference audit trail to understand prior decisions

### Don't:
- ✗ Assume system is always right (override if you know better)
- ✗ Assume system is always wrong (trust it for clear cases)
- ✗ Leave decisions incomplete if uncertain (defer instead)
- ✗ Delete records or modify source data (not supported)
- ✗ Export before checking readiness (confirm no blockers)

---

## Using Notes

**When to add notes:**
- Overriding a validation error (explain why it's valid)
- Rejecting a normalization (explain why original is better)
- Marking duplicate as unclear (explain what would help confirm)
- Rejecting household grouping (explain why unrelated)

**Note format:**
```
Short explanation + Context

Example: "Email format unusual but customer confirmed valid in call 6/12/26"
Example: "International format; standardization not appropriate"
Example: "Different families, temporarily at same address"
```

Notes appear in:
- Individual decision records
- Audit trail
- Export summary (for reference)

---

## Reverting Decisions

If you realize you made a mistake:

1. Go to the item in its queue
2. The current decision is shown
3. Click "Change Decision" or similar
4. Make a new decision
5. New decision replaces old one in export (old decision still in audit trail)

**Audit trail shows both decisions:** You can see what you decided, when, and when you changed it.

---

## Export Preview & Verification

**Before generating CSV:**

1. Go to **Export Console**
2. Click **Preview** (read-only view of what will be exported)
3. Verify:
   - Correct number of records
   - Normalizations look right
   - Duplicates marked correctly
   - Households grouped as intended
4. If something looks wrong: Go back to review queues, change decisions, regenerate preview

**No commitment:** Preview doesn't generate files. You can preview multiple times.

---

## Audit Trail

**View:** Click batch name → **Audit Trail** tab

**Shows:**
- Who made each decision
- When (timestamp)
- What decision (e.g., "Marked as Valid", "Rejected Household")
- Why (notes from reviewer)

**Use:** Understand decision history, verify no accidental changes, learn from prior decisions

---

## Handling Large Batches

**Batch size 100+ records?** Typical review pace is:
- Validation: 5-10 min (if few errors)
- Normalizations: 10-15 min (depends on errors)
- Duplicates: 5-10 min (depends on overlap)
- Households: 5-10 min (depends on grouping)

**Tips for large batches:**
- Take breaks between queues
- Check dashboard progress regularly
- Use Defer for uncertain items
- Verify readiness before final export

---

## Getting Help During Review

| Question | Answer |
|----------|--------|
| What does this error mean? | Check validation message in queue |
| Should I accept this normalization? | If unsure, reject it (safer) |
| Are these really the same person? | If unsure, defer it (revisit later) |
| How many items are left? | Dashboard shows "X of Y decided" |
| Can I change my mind? | Yes, change decision; new one used in export |
| What happens if I don't decide? | Item stays pending; export blocked until decided |

---

## Workflow Completion

**Batch ready for export when:**
- ✓ All validation items decided
- ✓ All normalization items decided
- ✓ All duplicate items decided
- ✓ All household items decided
- ✓ Export Readiness Dashboard shows "✓ Export Ready"

**Next step:** Go to Export Console, generate CSV, download

