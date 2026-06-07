# Givebutter Processor - Feature Overview for Testing Agents

## What This App Does

**Purpose**: Validate donation records from Givebutter exports before importing into a nonprofit's database.

**Problem It Solves**:
- Donors typo their emails (`gmai.com` instead of `gmail.com`) → undeliverable receipts
- Phone numbers are missing → impossible to contact donors
- Data is inconsistent → reconciliation nightmares
- Duplicate records appear → inflated donor counts

**Solution**: Three-step workflow to catch & fix data quality issues BEFORE import.

---

## The 3-Step Operator Workflow

### Step 1: Upload CSV
Operator uploads Givebutter export file (100s of donation records).

**System does**:
- Reads CSV
- Validates each field (email format, phone digits, amount range, etc.)
- Assigns validation tier (PASS/WARNING/FAIL)
- Creates processing file with validation metadata

**Test Case 1 exercises this**: Upload → Verify file appears in queue with tier counts

---

### Step 2: Review & Edit Records
Operator opens review interface, sees all records with validation issues flagged.

**Key Features**:

#### **2A: Inline Editing** (NEW)
- Click any data field → edit directly in table
- Real-time validation (red error if invalid)
- Auto-recalculate tier when issues are fixed
- Example: Add missing phone → WARNING becomes PASS

**Why it matters**: Operator doesn't need separate tools; fixes happen at point of discovery.

**Test Case 2 exercises this**: Edit phone field → Watch tier auto-update from WARNING to PASS

---

#### **2B: Fuzzy Email Domain Matching** (NEW)
- System catches email typos that aren't in hardcoded list
- Examples: `gmai.com`, `gmial.com`, `icloud.co`, `outlook.co`
- Suggests correction: "Consider: john@gmail.com"
- Aggressive flagging (70% threshold): Better to flag & let operator override than miss typos

**Why it matters**: Email is critical for donor contact. Typos in email = lost donors.

**Test Case 4 exercises this**: Email typo detected → Suggestion shown → Operator fixes → Tier updates

---

#### **2C: Editable Tier Dropdown** (NEW)
- Operator can OVERRIDE the validation tier
- Examples:
  - WARNING record with typo fixed inline? Change to PASS
  - FAIL record that operator knows is valid? Change to PASS
  - Record with subtle issues spotted? Change to FAIL
- Tier changes auto-save to CSV

**Why it matters**: Validators are conservative; operators have domain knowledge. Tier override gives operators final say.

**Test Case 3 exercises this**: Click tier dropdown (red FAIL) → Change to PASS (green) → Color updates → Persists on reload

---

#### **2D: Three-Tier System**
- **PASS** (Green): Record is clean, ready to import
- **WARNING** (Yellow): Has issues but might be OK (typos, missing optional fields, high dollar amount)
- **FAIL** (Red): Critical issues (invalid email, missing phone, etc.)

Color-coded for quick scanning. Operator can override any tier based on judgment.

---

### Step 3: Make Decisions & Submit
For each record, operator decides: **Approved**, **Follow-up** (with notes), or **Rejected**.

**Bulk Actions** (NEW):
- "All: Approved" button sets all records to Approved at once
- Smart confirmation:
  - ≤5 FAIL/WARNING records: Individual dialogs (one by one)
  - >5 FAIL/WARNING records: Single summary dialog (bulk confirm)
- Why? Prevents accidental bulk approvals; scales for large batches

**Test Case 5 exercises this**: Click "All: Approved" → Confirmation dialog → All decisions saved → "Done" completes workflow

---

## Architecture: How Data Flows

```
CSV Upload
    ↓
[Processor validates each record]
    ├─ Email: Check format, fuzzy-match domains
    ├─ Phone: Check 10-11 digit USA format, test patterns
    ├─ Amount: Range check, high-dollar flag
    ├─ Name: Length check, special characters
    └─ Address: Basic validation
    ↓
[Processing file created with validation metadata]
    └─ Columns: Original data + Validation_Tier + Issues + Suggested_Modifications + Operator_Decision + Operator_Notes
    ↓
[Operator Reviews via Web Interface]
    ├─ Sees validation tier (color-coded dropdown)
    ├─ Can inline-edit ANY field
    ├─ Can override tier (dropdown)
    ├─ Can set decision (dropdown)
    └─ Can add notes (text field)
    ↓
[All changes auto-save to processing CSV]
    ├─ Field edits → recalculated tier
    ├─ Decision changes → saved immediately
    ├─ Tier overrides → saved immediately
    └─ Notes → saved on blur
    ↓
[Operator clicks "Done"]
    ↓
[Output CSVs generated]
    ├─ approved/*.csv (Decision = Approved)
    ├─ followup/*.csv (Decision = Follow-up)
    └─ rejected/*.csv (Decision = Rejected)
```

---

## How Each Test Case Maps to Features

| Test Case | Feature | What Gets Tested |
|-----------|---------|------------------|
| **Test 1: Upload CSV** | Core workflow | CSV processing, tier assignment, queue display |
| **Test 2: Inline Edit + Auto-Update** | Inline editing + Tier recalc | Click-to-edit, validation, auto-tier, persistence |
| **Test 3: Tier Override** | Editable tier dropdown | Manual override, color coding, persistence, override confirmation |
| **Test 4: Email Fuzzy Match** | Fuzzy domain matching | Typo detection, suggestions, inline fix, tier update |
| **Test 5: Bulk Actions** | Operator workflow completion | Bulk decision, confirmation logic, done button, file archival |

---

## Key Technical Behaviors to Verify

### Auto-Save Architecture
- **Immediate persistence**: Field edits, decision changes, tier overrides all save within seconds
- **CSV file updated**: Changes persisted to disk (not just UI)
- **No "Save" button needed**: Unlike traditional forms, everything saves automatically
- **Re-openable**: If operator closes and reopens file, all changes are still there

**Test verification**: Edit phone field → Close browser → Reopen file → Phone value still there

---

### Validation & Tier Auto-Update
- When operator fixes an issue via inline edit, tier should recalculate immediately
- **CRITICAL RULE**: Tier only becomes PASS when ALL issues are resolved, not just some
- Example 1 (single issue):
  - Record with "WARNING: missing phone" → Operator adds phone → Tier changes "WARNING (yellow) → PASS (green)"
- Example 2 (multiple issues):
  - Record with "WARNING: missing phone + email typo" → Operator adds phone → Tier stays "WARNING" (email typo remains)
  - Record with "WARNING: missing phone + email typo" → Operator adds phone + fixes email → Tier changes to "PASS"
- Issues column updates to reflect resolved issues
- Suggested Fixes updates or clears
- **CRITICAL**: Both the dropdown VALUE and CSS CLASS must update for this to work correctly

**Test verification (Single Issue)**: 
1. **Before Edit**: 
   - Tier dropdown VALUE = "Warning"
   - Tier dropdown CSS class = "tier-warning" (yellow #fff3cd)
   - Issues = "Phone: Phone number not found"
2. **Edit**: Add phone `5551234567` and click Save
3. **After Edit** (verify within 1 second):
   - Tier dropdown VALUE = "Pass" (not "Warning")
   - Tier dropdown CSS class = "tier-pass" (green #d4edda, NOT "tier-warning")
   - Issues = empty
   - Color visually changes from yellow to green in dropdown

**Test verification (Multiple Issues - Partial Fix)**:
1. **Before Edit**: Record has TWO issues
   - Tier = "Warning" with class "tier-warning" (yellow)
   - Issues = "Phone: Phone number not found" AND "Email: Email domain 'gmai.com' looks like a typo"
2. **Fix Issue 1**: Add phone number and Save
3. **After Issue 1 Fixed**:
   - Tier should STILL be "Warning" with class "tier-warning" (NOT "Pass")
   - Issues = only email typo remains
   - **THIS IS THE KEY TEST**: Tier should NOT jump to Pass just because one issue is fixed
4. **Fix Issue 2**: Correct email to `user@gmail.com` and Save
5. **After ALL Issues Fixed**:
   - Tier becomes "Pass" with class "tier-pass" (green)
   - Issues = empty

---

### Color Coding Consistency
- Dropdown colors match their meaning:
  - Pass = Green (#d4edda) + Green border
  - Warning = Yellow (#fff3cd) + Yellow border
  - Fail = Red (#f8d7da) + Red border
- Color updates immediately when:
  - Inline edits fix issues (tier recalculates)
  - Operator changes tier dropdown manually
  - Page loads (initial rendering)

**Test verification**: Visual inspection + CSS color assertions

---

### Fuzzy Email Domain Matching
- Catches typos at 70% similarity threshold (aggressive, favors recall over precision)
- Common domains checked: gmail.com, yahoo.com, outlook.com, hotmail.com, aol.com, protonmail.com, icloud.com
- Typos caught:
  - Character drops: `gmai.com` (missing l)
  - Character swaps: `gmial.com` (l and a swapped)
  - TLD variants: `gmail.co` (legitimate variant, allowed)
- Suggestion always points to standard domain

**Test verification**: Enter typo → Issue appears → Suggestion shown → Fix inline → Tier updates

---

### Operator Decision Workflow
- Three mutually-exclusive options: Approved, Follow-up, Rejected
- Override confirmation: If approving FAIL or WARNING tier, operator sees warning dialog
- Bulk actions: Single click to set all records to same decision
- Smart confirmation: Avoids UI fatigue with summary dialogs for large batches

**Test verification**: Select bulk action → Dialog appears → Confirm → All decisions set → "Done" submits

---

## Success Definition for Testing Agent

**Overall**: Operator can upload, review, fix issues, make decisions, and submit all without errors.

**Specifically**:
- ✅ Upload creates file in review queue with accurate tier counts
- ✅ Inline editing works (click → edit → save → persists)
- ✅ Tier auto-updates when issues are resolved
- ✅ Color coding is accurate (green/yellow/red)
- ✅ Fuzzy email matching catches typos
- ✅ Operator can override tier via dropdown
- ✅ All changes auto-save to CSV (verified on reload)
- ✅ Bulk actions set all decisions at once with confirmation
- ✅ "Done" button completes workflow (file removed from queue)
- ✅ Output CSVs created with correct data

---

## Important Context for Agent

### Why Inline Editing Matters
Traditional workflow: Operator sees error → Notes it → Manually edits CSV → Re-uploads
New workflow: Operator sees error → Clicks cell → Types fix → Done

This 80% reduction in friction means operators review 10x faster.

### Why Tier Override Matters
Validators are conservative (default to WARNING/FAIL).
Operators have domain knowledge (know if a record is actually OK).
Tier override lets operators make final judgment without rejecting valid records.

### Why Auto-Save Matters
No "Save" button = no forgotten saves = no data loss.
Operator edits phone → Changes persist immediately → Can close browser safely.

### Why Fuzzy Matching Matters
Email typos are invisible to human review (both `gmai.com` and `gmail.com` look similar).
Fuzzy matching catches 95%+ of typos without needing hardcoded lists.
Aggressive threshold (70%) means some false positives, but operator can easily override.

---

### Phone Number Validation Rules
- **10 digits**: Valid (e.g., `5551234567`)
- **11 digits starting with 1**: Valid (e.g., `15551234567`)
- **<10 digits**: FAIL - Too short
- **>11 digits (but ≤15)**: WARNING - Flagged as "too long" with suggestion. When operator tries to save, confirmation dialog appears: "This phone has X digits (expected ≤11). Are you sure?" Operator can confirm to proceed or cancel to edit.
- **>15 digits**: Cannot be entered (HTML maxlength prevents it)

**Example**: Operator enters `2125551234567` (13 digits)
- Input validation passes (13 is within 10-15 range)
- On save, confirmation dialog appears
- If confirmed, saved with WARNING tier
- Issues column flags: "Phone too long (13 digits)"
- Suggestion: "Phone has 13 digits (expected ≤11). Confirm this is correct or remove extra digits."

## Related Documentation

- **README.md**: Feature list & quick start
- **OPERATOR_MANUAL.md**: How to use the app (for end users)
- **PROCESSOR_GUIDE.md**: Validation rules & technical details
- **E2E_TEST_PLAN_P0.md**: Detailed test procedures (this agent's guide)

This document: **What the app does & why tests matter**

