# Givebutter Processor - E2E Test Plan (P0)
## Top 5 Critical User Workflows via Playwright

**Target**: Test the complete operator review workflow with focus on new features (inline editing, editable tier, auto-save).

---

## P0 Test Case 1: Upload CSV & Process Records

**Objective**: Verify the complete upload → processing → review queue flow works end-to-end.

**Steps**:
1. Navigate to `http://127.0.0.1:8000/`
2. Wait for drop-zone to appear
3. Upload sample CSV file (5-10 records with mixed tiers: PASS, WARNING, FAIL)
4. Wait for success message ("Processed X records")
5. Verify Review Queue shows the uploaded file with record counts
6. Verify summary shows: PASS count (green), WARNING count (yellow), FAIL count (red)

**Success Criteria**:
- ✅ File appears in Review Queue immediately after upload
- ✅ Record counts match uploaded CSV
- ✅ Tier breakdown summary is accurate
- ✅ "Review" button is clickable

---

## P0 Test Case 2: Inline Editing with Real-Time Tier Auto-Update

**Objective**: Verify that editing data fields triggers validation and automatically updates tier when issues are resolved.

**Steps**:
1. Upload CSV with a WARNING-tier record (e.g., missing phone number)
2. Click "Review" button
3. Verify record shows WARNING tier (yellow dropdown)
4. Click on Phone cell (empty field)
5. Enter valid phone: `5551234567`
6. Click Save button
7. Wait for tier dropdown to update color
8. Verify:
   - Phone field now displays the new number
   - Issues column updates (phone issue removed)
   - Tier dropdown changes from Warning (yellow) → Pass (green)

**Success Criteria**:
- ✅ Phone field accepts input and saves
- ✅ Tier dropdown color changes automatically
- ✅ Issues list updates in real-time
- ✅ No page refresh needed
- ✅ Change persists if page is reloaded

---

## P0 Test Case 3: Override Tier via Dropdown & Confirm Warning

**Objective**: Verify operator can manually change tier and is warned when approving FAIL/WARNING records.

**Steps**:
1. Open review page with a FAIL-tier record (red dropdown)
2. Click Decision dropdown → select "Approved"
3. Override confirmation dialog appears: "You are approving this record despite validation failures"
4. Click "OK" to confirm
5. Decision saves as "Approved"
6. Click on Tier dropdown (currently showing "Fail" in red)
7. Change to "Pass" (dropdown changes to green)
8. Close the record (click Done button)
9. Reopen the file → verify tier persisted as "Pass"

**Success Criteria**:
- ✅ Override dialog appears when approving FAIL/WARNING records
- ✅ Tier dropdown updates immediately with correct color (red→green)
- ✅ Tier change persists to CSV file
- ✅ Decision and Tier changes both saved on reload

---

## P0 Test Case 4: Fix Email Typo & Verify Fuzzy Matching Suggestion

**Objective**: Verify aggressive email fuzzy matching catches typos and suggests corrections.

**Steps**:
1. Upload CSV with email typo: `user@gmai.com` (missing 'l')
2. Record shows WARNING tier (yellow)
3. Issues column displays: "Email: Email domain 'gmai.com' looks like a typo"
4. Suggested Fixes shows: "Consider: user@gmail.com"
5. Click Email cell
6. Change email to: `user@gmail.com` (correct)
7. Click Save
8. Verify:
   - Email updates in cell
   - Issues column clears email issue
   - Tier auto-updates from WARNING → PASS (if no other issues)

**Success Criteria**:
- ✅ Typo is flagged (fuzzy matching works)
- ✅ Suggestion is accurate
- ✅ Inline edit works
- ✅ Tier updates automatically after fix
- ✅ Change persists on reload

---

## P0 Test Case 5: Bulk Actions → Complete Review Workflow

**Objective**: Verify bulk decision buttons work and "Done" button completes the review.

**Steps**:
1. Open review page with 10+ records (mix of tiers)
2. Click "All: Approved" button
3. If ≤5 FAIL/WARNING records: Individual confirmation dialogs appear
4. If >5 FAIL/WARNING records: Single summary dialog appears
5. Accept all confirmations
6. Verify all Decision dropdowns show "Approved"
7. Click "Done" button
8. Success message: "Review complete for [filename] - all changes saved"
9. Review Queue reappears
10. File should be moved out of Review Queue (not visible anymore)

**Success Criteria**:
- ✅ Bulk action dialog logic works (individual vs summary)
- ✅ All decisions set to "Approved" at once
- ✅ Done button closes review without errors
- ✅ File disappears from Review Queue after completion
- ✅ Output CSV files created (check review/approved/ directory)

---

## Test Data Requirements

**Sample CSV** (`sample_test.csv`):
```
Transaction ID,Date,Name,Email,Phone,Amount
TX001,2026-05-10,John Doe,john@gmail.com,5551234567,100
TX002,2026-05-11,Jane Smith,jane@gmai.com,,250
TX003,2026-05-12,Bob Wilson,bob.smith,5551112222,500
TX004,2026-05-13,Alice Brown,alice@example.co,555-1234-5678,1000000
TX005,2026-05-14,Charlie Lee,charlie@gmial.com,5555555555,75
```

**Expected Tier Distribution**:
- TX001: PASS (valid email, phone, amount)
- TX002: WARNING (email typo: gmai.com, missing phone)
- TX003: FAIL (invalid email format: missing @)
- TX004: WARNING (email domain variant: .co, high dollar amount)
- TX005: WARNING (email typo: gmial.com, test phone: all same digits)

---

## Browser & Environment Setup

**Browser**: Chromium (via Playwright)
**Viewport**: Desktop (1280x800)
**Base URL**: `http://127.0.0.1:8000`
**Flask Server**: Must be running before tests start

```bash
# Start Flask app
cd aws_nonprofit_toolkit/Givebutter/scripts/uploader
python app.py

# In another terminal, run tests
pytest tests/e2e/test_e2e_p0_critical.py -v
```

---

## Key UI Elements to Target (CSS Selectors)

| Element | Selector | Notes |
|---------|----------|-------|
| Drop Zone | `div.drop-zone` | File upload area |
| File Input | `input[type="file"]` | Hidden input |
| Upload Button | `button[type="submit"]` | Primary upload trigger |
| Review Button | `button:has-text("Review")` | Opens review panel |
| Decision Dropdown | `.decision-select` | Per-record decision (Approved/Rejected/Follow-up) |
| Tier Dropdown | `.tier-select` | Per-record tier override (Pass/Warning/Fail) |
| Data Cell (editable) | `.editable-cell[data-field="email"]` | Click to edit |
| Save Button (inline) | `.btn-edit-save` | Save inline edit |
| Done Button | `button:has-text("Done")` | Complete review |
| Bulk Buttons | `button:has-text("All:")` | Approve/Reject/Follow-up all |
| Issues Column | `td[data-field-type="issues"]` | Shows validation issues |
| Suggested Fixes | `td[data-field-type="suggestions"]` | Shows correction suggestions |

---

## Expected Behaviors

### Color Coding
- **Pass (Green)**: `#d4edda` background, dark green text
- **Warning (Yellow)**: `#fff3cd` background, brown text
- **Fail (Red)**: `#f8d7da` background, dark red text

### Auto-Save Triggers
- ✅ Decision dropdown change → saves immediately
- ✅ Notes textarea blur → saves immediately
- ✅ Inline field Save button → saves immediately, tier recalculates
- ✅ Tier dropdown change → saves immediately

### Data Persistence
- All changes persist across page reloads (check CSV file)
- Decisions remain selected after review reopens
- Edited values remain in cells
- Tier overrides persist

---

## Troubleshooting Guide

| Issue | Solution |
|-------|----------|
| Tier dropdown doesn't update color | Verify `updateTierSelectColor()` function is called; check browser console for errors |
| Inline edit not saving | Ensure Save button is enabled (validation passed); check network tab for API response |
| Override dialog doesn't appear | Verify record tier is FAIL or WARNING; check selector `.decision-select` |
| Bulk action dialog shows summary instead of individual | Count FAIL/WARNING records; >5 triggers summary dialog (expected) |
| File not removed from Review Queue after Done | Check if file was actually submitted; verify output CSV files exist |

---

## Pass/Fail Scoring

**PASS**: All 5 test cases pass with all success criteria met  
**FAIL**: Any test case fails or any success criterion is not met  
**PARTIAL**: 3-4 test cases pass (investigate failures, may be environmental)

---

## Notes for Testing Agent

- Run tests in fresh browser context (no cached data)
- Clear review/processing/ directory between test runs
- Monitor browser console for JavaScript errors
- Verify CSV files are actually persisted (check disk, not just UI)
- Test on both Chrome and Firefox if possible (CSS styling differences)
- Document any timing issues (e.g., tier updates delayed >1 second)

