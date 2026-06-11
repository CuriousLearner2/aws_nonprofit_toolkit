# Households Review — Implementation Reference Mock

**Status:** Local implementation reference created (not a Stitch update)  
**Date:** 2026-06-10  
**Type:** Implementation reference mock  
**Source:** Specification-driven (households_review-spec.md)

---

## ⚠️ Important Clarification

**This reference mock was created because:**

1. Stitch SDK requires MCP infrastructure unavailable in current environment
2. Stitch variants/edit methods cannot be called without MCP server
3. This is a local implementation-reference artifact, not a Stitch screen update

**This is NOT a claim that the Stitch screen has been refined.**

The original Stitch screen remains at node ID `301d7906577449908563bb9a591b88f7`. This reference mock is a corrected implementation guide based on the specification.

---

## What Was Changed

### 1. Decision Actions (Critical)

**Before:** Single dominant "Approve Household" button (approval-forward)

**After:** Three balanced decision buttons in horizontal row
```html
[Confirm Household] [Defer] [Reject]
```

- **Confirm Household:** Primary blue button (~120px)
- **Defer:** Secondary outlined button (~80px)
- **Reject:** Secondary outlined button (~80px)
- Equal spacing, balanced visual weight
- Confirm slightly more prominent, but not dominant

### 2. Confirmation Modal (Critical)

**Added:** Modal to prevent accidental confirms

**Trigger:** Clicking "Confirm Household" button

**Modal Title:**
```
Confirm suggested household?
```

**Modal Body:**
```
These contacts will be marked as belonging to the suggested household 
for this import's export staging. 
Raw import rows will not be changed. 
This decision will be logged to the audit trail.
```

**Modal Buttons:**
- Cancel (secondary)
- Confirm Household (primary blue)

**Behavior:** Non-dismissible (requires user action)

### 3. Explicit Scope Copy (Critical)

**Below decision buttons, in each card:**
```
Confirmed households affect export staging only. 
Raw import rows will not be changed. 
This decision is logged.
```

**Style:** Small gray italic text, supporting detail

### 4. Updated Safety Strip

**Location:** Below batch metadata

**Text:**
```
Suggested changes only. Confirmed households affect export staging only. 
Raw import rows are never changed.
```

### 5. Confidence Labels (Numeric)

**Format:** Use numeric confidence consistently

**Examples:**
- ✅ "98% match"
- ✅ "87% match"
- ❌ "High confidence" (too vague)

### 6. Strengthened Evidence Display

**For each suggested household, show:**

- ✓ Shared address (with specifics)
- ✓ Same last name (if present)
- ✓ Shared phone (if present)
- ⚠ Conflicting signals (transparently, not hidden)
- Confidence calculation explanation

**Example:**
```
Evidence:
✓ Shared address: 123 Maple St, Seattle, WA (exact match)
✓ Same last name: Smith
✓ Shared phone: (555) 987-6543
⚠ Email domain differs: personal vs work
✗ No shared source file

Confidence: 92% match (4 of 5 signals align)
```

**Important:** Conflicting signals are shown, not hidden. Let the reviewer see all evidence.

### 7. Removed Unsafe Language

**All forbidden terms removed:**
- ❌ Auto-household → ✅ Suggested Household
- ❌ Auto-merge → ✅ Confirm
- ❌ Merge → ✅ Group as household
- ❌ Writeback → ✅ (not mentioned)
- ❌ Sync to CRM → ✅ (not mentioned)
- ❌ Apply All → ✅ Individual decision per card
- ❌ Approve All → ✅ Confirm (per household)

### 8. Preserved Card Structure

**Each household card contains:**

1. **Header**
   - Suggested household name (prominent)
   - Confidence score (numeric, e.g., "98% match")
   - Status badge ("Suggested Household")

2. **Proposed Members Section**
   - Clear list of contacts
   - Names, email, phone
   - Easy to scan

3. **Evidence Section** (strengthened)
   - All matching signals (checkmarks)
   - Conflicting signals (warning/error icons)
   - Confidence calculation

4. **Decision Row** (balanced buttons)
   - Confirm Household (primary)
   - Defer (secondary)
   - Reject (secondary)

5. **Scope Copy** (supporting text)
   - Affirms raw rows immutable
   - Confirms export staging only
   - States decision is logged

---

## Layout & Navigation

### Desktop Web Pattern ✅

- **Top Navigation:** DonorTrust logo, tabs (Upload, Imports, Review, Matches, People, Households)
- **Left Sidebar:** Data Controls, filters, batch status card
- **Main Content:** Household cards in column layout
- **Viewport:** 1440px desktop width assumed

### Not Tablet-Specific

This is designed as desktop web. If a tablet variant is needed, it should be labeled separately.

---

## Files in This Folder

| File | Purpose |
|------|---------|
| `households_review-spec.md` | Authoritative specification (14 sections, 11 acceptance criteria) |
| `REFINEMENT_PLAN.md` | Summary of required changes |
| `design-reference.html` | Corrected implementation reference |
| `screenshot-2x-above-fold.png` | High-res above-fold (2880×1800px) |
| `screenshot-2x-full.png` | High-res full-page (2880×...) |
| `verification.json` | All 40 checks pass |
| `REFERENCE_MOCK_NOTES.md` | This file |
| `README.md` | Orientation document |

---

## How to Use This Reference

### For Implementation
1. Use `design-reference.html` as visual/structural reference
2. Refer to `households_review-spec.md` for exact copy and acceptance criteria
3. Copy card structure, button layout, modal pattern
4. Implement all three decision flows: Confirm, Defer, Reject
5. Include confirmation modal
6. Use DonorTrust v1 styling direction (spec section 12)

### For Design Review
1. Use `screenshot-2x-above-fold.png` and `screenshot-2x-full.png` for visual inspection
2. Verify decision buttons are balanced, not one giant "Approve" button
3. Confirm safety strip and scope copy are visible
4. Check evidence display shows conflicts transparently

### For QA Verification
1. Use `households_review-spec.md` section 11 (11 Acceptance Criteria)
2. Verify no unsafe language ("Approve All", "Auto-merge", etc.)
3. Verify confirmation modal appears and blocks accidental confirms
4. Verify all three decision buttons work (Confirm, Defer, Reject)
5. Verify audit logging is configured

---

## Key Safety Guarantees

This design ensures:
- ✅ Raw import rows are **never mutated**
- ✅ Suggested households affect **export staging only**
- ✅ Every decision (Confirm/Defer/Reject) is **audit logged**
- ✅ No automatic household creation
- ✅ No CRM writeback from this screen
- ✅ Reviewer **intent is explicit** (three clear options, not approve-all)
- ✅ Conflicting evidence is **transparent**, not hidden

---

## DonorTrust v1 Consistency

This screen follows DonorTrust v1 patterns:
- ✅ Top navigation bar (Households active)
- ✅ Left sidebar (Data Controls, Batch Status)
- ✅ Card-based content structure
- ✅ Clear visual hierarchy
- ✅ Balanced action buttons
- ✅ Audit-safe copy and messaging
- ✅ High contrast, readable typography

---

## Original Stitch Screen

The original Stitch screen remains:
```
Node ID: 301d7906577449908563bb9a591b88f7
Preview: https://stitch.withgoogle.com/preview/9371274764538076058?node-id=301d7906577449908563bb9a591b88f7
```

This reference mock is NOT a replacement for that artifact, but a corrected implementation guide created due to Stitch SDK unavailability.

---

## Authority & Next Steps

**Authority:** 
- `households_review-spec.md` (specification)
- This reference mock (visual/structural reference)

**For implementation:**
1. Build from the spec (not by patching this HTML)
2. Use this reference mock for visual guidance
3. Follow all safety constraints from spec section 2
4. Include confirmation modal as described
5. Pass all 11 acceptance criteria before considering done

**Timeline:**
1. ✅ Specification created
2. ✅ Reference mock created & verified (40/40 checks pass)
3. → Implementation in app code
4. → QA verification against spec
5. → Deployment

---

**Created:** 2026-06-10  
**Type:** Local implementation reference (not a Stitch update)  
**Authority:** Spec document + this reference mock  
**Status:** Ready for implementation  
**Safety Level:** Audit-safe, reviewer-decision-explicit, raw-rows-immutable
