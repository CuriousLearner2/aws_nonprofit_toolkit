# All Records / Validation Review — Iteration 002: Reference Mock

**Status:** Local implementation reference created (not a Stitch update)  
**Date:** 2026-06-10  
**Type:** Implementation reference mock  
**Source:** Stitch variant 1e651afb51c74f199144b6ec44e65776 (corrected)

---

## Important Clarification

**This reference mock was created because:**

1. Stitch SDK/MCP infrastructure is unavailable in the current Node environment
2. The Stitch export had layout issues and unnecessary columns
3. Direct Stitch refinement was not possible

**This is NOT a claim that the Stitch screen itself was refined.**

The original Stitch artifact remains a visual baseline. This local reference mock plus `all_records_validation_review-spec.md` are the source of truth for future implementation.

---

## What Was Fixed

### 1. Table Column Structure (Critical)

**Fixed:** Removed the Issue/Fix column. Table now uses exactly **10 columns** as specified:

| Column | Width | Purpose |
|--------|-------|---------|
| Selection | 50px | Checkbox for row selection |
| Transaction ID | 120px | Unique transaction identifier (monospace) |
| Date | 100px | Transaction date |
| Name | 140px | Donor/payer name |
| Email | 160px | Email address |
| Phone | 130px | Phone number |
| Amount | 100px | Transaction amount |
| Address | 150px | Physical address |
| Status | 120px | Validation status badge (✓ Valid, ⚠ Needs Review, ✗ Issue, ✓ Reviewed) |
| Action | 100px | Navigation action (View Row / Review Issues) |

**Total width:** ~1070px (fits 1440px canvas comfortably with sidebar visible)

### 2. Validation Issue Representation (UX Improvement)

**Instead of a separate Issue/Fix column, validation problems are now represented through:**

1. **Status Badge** (column 9)
   - Color-coded with icon and text label
   - Quick visual indicator at a glance

2. **Subtle Field Highlighting** (inline, on affected fields)
   - Invalid email: light red background (`field-error`)
   - Invalid phone: light amber background (`field-warning`)
   - Zero/invalid amount: light red background + red text
   - Subtle 4% opacity tint (not harsh)

3. **Contextual Action Label** (column 10)
   - "Review Issues" for rows with ✗ Issue or ⚠ Needs Review status
   - "View Row" for rows with ✓ Valid or ✓ Reviewed status
   - Clear signal of what reviewer should do next

**Detailed explanations** belong in:
- Row detail view (click "Review Issues" → expanded row or drawer)
- Tooltip on hover (future enhancement)
- Not cluttering the main table

### 3. Layout Issue (Critical)

**Problem:** Original export had `min-w-[1800px]`, forcing horizontal scrolling at 1440px.

**Solution:** 
- Changed table container from `min-w-[1800px]` to `w-full`
- Added `table-layout: fixed` CSS rule for stable column widths
- Columns remain readable and visually balanced (not crushed)

### 4. Added Safety Strip

**Added:** Compact safety strip below page metadata
```
Suggested changes only. Raw import rows are never changed.
```

**Location:** Between batch metadata and action buttons
**Styling:** Light background (surface-audit), subtle border, gray text

---

## Files in This Folder

| File | Purpose |
|------|---------|
| `design-reference.html` | Corrected HTML with fixed layout (1440px viewport) |
| `screenshot-2x-above-fold.png` | High-res 2880×1800px above-fold screenshot |
| `screenshot-2x-full.png` | High-res 2880×... full-page screenshot |
| `verification.json` | Automated verification results |
| `REFERENCE_MOCK_NOTES.md` | This file |

---

## Verification Results

All acceptance criteria verified via content analysis:

### Visual ✅
- [x] Exactly 10 columns (no Issue/Fix column)
- [x] Status column visible (120px width)
- [x] Action column visible (100px width)
- [x] All 10 columns fit 1440px width comfortably
- [x] Safety strip present below metadata
- [x] All status badges visible with text labels
- [x] Row action links: contextual labels ("View Row" / "Review Issues")
- [x] Subtle field highlighting on problematic fields (red/amber tints)
- [x] Table readable, columns not visually crushed

### Safety ✅
- [x] No "Approve All" language present
- [x] No "Auto-apply" language present
- [x] No "Clean All" language present
- [x] Button says "Review Selected (1)" (selection state shown)
- [x] Safety strip: "Raw import rows are never changed"
- [x] Footer safety message: "Nothing is applied until a reviewer approves it. Raw import rows are never changed."

### Functional ✅
- [x] Table uses `table-layout: fixed` (stable column widths)
- [x] Table uses `w-full` (fits viewport)
- [x] No min-w-[1800px] constraint
- [x] All status badges text-labeled (✓ Valid, ⚠ Needs Review, ✗ Issue, ✓ Reviewed)
- [x] Validation issues represented via:
  - Status badge (visual indicator)
  - Field highlighting (inline, subtle tint)
  - Action label (contextual: "Review Issues" vs "View Row")
- [x] Pagination controls present
- [x] Status summary present (Valid: 842 | Review: 12 | Issues: 5)

---

## How to Use This Reference

### For Implementation
1. Use `design-reference.html` as visual reference for row structure and styling
2. Refer to `all_records_validation_review-spec.md` for exact copy and acceptance criteria
3. Key implementation details:
   - **Table structure:** Exactly 10 columns (Selection, Transaction ID, Date, Name, Email, Phone, Amount, Address, Status, Action)
   - **No Issue/Fix column:** Validation issues shown through status badge + field highlighting + action label
   - **Column widths:** Use fixed widths per the table above for consistency
   - **Field highlighting:** Apply `field-error` (4% red tint) and `field-warning` (4% amber tint) to problematic fields
   - **Action labels:** Use "Review Issues" for rows with Issue/Needs Review status, "View Row" for Valid/Reviewed
   - **Table width:** `w-full` with `table-layout: fixed`
   - **Safety strip:** Below metadata line with text "Suggested changes only. Raw import rows are never changed."
   - **DonorTrust v1 styling:** All existing design preserved

### For Design Review
- Use `screenshot-2x-above-fold.png` and `screenshot-2x-full.png` for visual inspection
- Verify at 1440px desktop width that Status and Action columns are visible
- Confirm layout matches design direction

### For QA Verification
- Use spec section 11 (Acceptance Criteria) from `all_records_validation_review-spec.md`
- Verify no unsafe language ("Approve All", "Auto-apply", etc.)
- Verify selection-aware button behavior
- Verify all badges have text labels

---

## DonorTrust v1 Styling Preserved

All DonorTrust v1 design elements are preserved:
- Navigation bar (Review tab active)
- Data Controls sidebar with Queue Status
- Color scheme (green for valid, amber for needs review, red for issues)
- Font styling (Inter, JetBrains Mono for data)
- Badge styling with icons and text labels
- Button styling (primary blue, secondary outlined)
- Hover states and transitions
- Sticky footer with status summary

---

## Original Stitch Artifact

The original Stitch export remains available:
```
testing/workspace/ChatGPT/stitch-review/all-records-validation-review/design.html
```

This reference mock is NOT a replacement for that artifact, but a corrected implementation reference created due to SDK unavailability.

---

## Next Steps for Implementation

1. **Use this reference mock for UI development**
   - Copy HTML structure and Tailwind classes
   - Adapt to your app's templating (JSX, Jinja, etc.)
   - Connect to real data endpoints

2. **Keep spec as authority**
   - `all_records_validation_review-spec.md` section 11 defines all acceptance criteria
   - Use spec for edge cases and business logic

3. **Table structure and layout checklist**
   - [ ] Exactly 10 columns (no Issue/Fix column)
   - [ ] Column order: Selection, Transaction ID, Date, Name, Email, Phone, Amount, Address, Status, Action
   - [ ] Table uses `table-layout: fixed` for stable column widths
   - [ ] Table width: `w-full` (no `min-w-[1800px]` or other excessive constraints)
   - [ ] Column widths match reference above (or proportionally scaled for responsive layouts)
   - [ ] Status column visible at 1440px (120px width minimum)
   - [ ] Action column visible at 1440px (100px width minimum)
   - [ ] Columns remain readable and visually balanced (not crushed)
   - [ ] Safety strip visible below batch metadata
   - [ ] Validation issues shown through three complementary techniques:
     - Status badge (✓ Valid / ⚠ Needs Review / ✗ Issue)
     - Subtle field highlighting (red tint for errors, amber for warnings)
     - Contextual action labels ("Review Issues" vs "View Row")

---

**Created:** 2026-06-10  
**Type:** Local implementation reference (not a Stitch update)  
**Authority:** Spec document + this reference mock  
**Status:** Ready for implementation
