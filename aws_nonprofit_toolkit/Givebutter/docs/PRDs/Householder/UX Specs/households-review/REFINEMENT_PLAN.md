# Households Review — Refinement Plan

**Screen:** Households Review (Suggested Household Review)  
**Node ID:** 301d7906577449908563bb9a591b88f7  
**Current Issue:** Approval-forward design; needs to be reviewer-decision-explicit and audit-safe  
**Status:** Ready for Stitch refinement  

---

## Key Changes Required

### 1. Replace Dominant Button with Balanced Decision Row

**Current:** Full-width "Approve Household" button (approval-forward)

**Change to:** Three explicit decision buttons in a balanced row:
```
[Confirm Household] [Defer] [Reject]
```

- Confirm: Primary blue button (~120px)
- Defer: Secondary outlined button (~80px)
- Reject: Secondary outlined button (~80px)
- Horizontal layout, equal spacing
- Confirm may be slightly more prominent, but should NOT dominate

### 2. Add Explicit Scope Copy

**Location:** Below decision buttons, in each household card

**Text:**
```
Confirmed households affect export staging only. 
Raw import rows will not be changed. 
This decision is logged.
```

**Style:** Small gray italic text, non-prominent but visible

### 3. Implement Confirmation Modal

**Trigger:** Clicking "Confirm Household" button

**Modal Title:**
```
Confirm suggested household?
```

**Modal Body:**
```
These contacts will be marked as belonging to the suggested household for this import's export staging. 
Raw import rows will not be changed. 
This decision will be logged to the audit trail.
```

**Modal Buttons:**
- Cancel (secondary)
- Confirm Household (primary blue)

**Behavior:**
- Non-dismissible (requires user action)
- Logs decision to audit trail on confirm
- Updates card status (optional UI feedback)

### 4. Update Safety Strip

**Current:** (Unknown - likely generic or absent)

**Change to:**
```
Suggested changes only. Confirmed households affect export staging only. Raw import rows are never changed.
```

**Location:** Below batch metadata line  
**Style:** Compact, light background, subtle border

### 5. Standardize Confidence Display

**Rule:** Use numeric confidence consistently

**Format:**
```
"98% match" (preferred)
"95%+ similarity"
NOT "High confidence" or vague terms
```

**Location:** Household card header or near suggested name

### 6. Strengthen Evidence Section

**What to show:**
- Shared address (if present)
- Same last name (if present)
- Shared phone (if present)
- Source file
- Conflicting signals (if present)

**Format:**
```
Evidence:
✓ Shared address: 123 Maple St, Seattle, WA
✓ Same last name: Smith
✓ Shared phone: (555) 123-4567
⚠ Email domain differs: personal vs work

Confidence: 92% match
```

**Important:** Do NOT hide conflicts. Let the reviewer see all signals.

### 7. Preserve & Enhance Card Structure

Keep the existing card structure but refine:

1. **Header**
   - Suggested household name (prominent)
   - Confidence score (numeric)
   - Status badge (Suggested Household)

2. **Proposed Members**
   - Clear list of contacts
   - Key identifiers (name, email, phone)

3. **Evidence** (strengthen this)
   - All matching signals
   - Conflicting signals (transparent)
   - Confidence explanation

4. **Decision Row** (change this)
   - Replace single button with three options
   - Add scope copy below

### 8. Remove Unsafe Language

**Forbidden terms:**
- ❌ Auto-household
- ❌ Auto-merge
- ❌ Merge
- ❌ Writeback
- ❌ Sync to CRM
- ❌ Apply All
- ❌ Approve All

**Preferred terms:**
- ✅ Confirm Household
- ✅ Suggested Household
- ✅ Defer
- ✅ Reject
- ✅ Export staging
- ✅ Logged to audit trail

### 9. Verify Navigation Pattern

**Desktop Web:**
- Top navigation bar (DonorTrust standard)
- Left sidebar (Data Controls / Batch Filters)
- Main content area (household cards)
- Full 1440px width assumed

**If Tablet:**
- Label as "Households Review (Tablet)"
- Sidebar may be drawer/bottom tab
- Cards may be full-width or two-column

**Assume desktop unless specified otherwise.**

---

## Stitch Refinement Prompt

```
REFINE: Households Review — Audit-Safe Household Suggestion Review

Current design is visually clean but approval-forward. Make the reviewer decision explicit, audit-safe, and consistent with DonorTrust v1.

Core principle: System suggests households. Reviewer confirms, defers, or rejects. Raw import rows are never changed.

CRITICAL CHANGES:

1. DECISION BUTTONS
   Replace full-width "Approve Household" button with balanced row:
   - [Confirm Household] (primary blue, ~120px)
   - [Defer] (secondary, ~80px)
   - [Reject] (secondary, ~80px)
   Do NOT dominate the card with a single approve button.

2. SCOPE COPY (below decision buttons)
   Confirmed households affect export staging only. 
   Raw import rows will not be changed. 
   This decision is logged.

3. CONFIRMATION MODAL
   Trigger: Clicking "Confirm Household"
   Title: Confirm suggested household?
   Body: These contacts will be marked as belonging to the suggested household for this import's export staging. Raw import rows will not be changed. This decision will be logged to the audit trail.
   Buttons: Cancel | Confirm Household

4. SAFETY STRIP (below batch metadata)
   Suggested changes only. Confirmed households affect export staging only. Raw import rows are never changed.

5. CONFIDENCE LABELS
   Use numeric: "98% match" or "95%+ similarity"
   NOT vague labels like "High confidence"

6. EVIDENCE SECTION
   Show all signals clearly:
   ✓ Shared address: 123 Maple St, Seattle, WA
   ✓ Same last name: Smith
   ✓ Shared phone: (555) 123-4567
   ⚠ Email domain differs: personal vs work
   Do NOT hide conflicts from reviewer.

7. PRESERVE CARD STRUCTURE
   Keep: Suggested name, Proposed members, Evidence
   Change: Decision buttons (add Defer/Reject), add scope copy

8. REMOVE UNSAFE LANGUAGE
   NO: Auto-household, Auto-merge, Merge, Writeback, Sync to CRM, Apply All, Approve All
   YES: Confirm, Defer, Reject, Export staging, Logged to audit trail

VERIFY:
- Top nav (DonorTrust standard)
- Left sidebar (Data Controls)
- All decision buttons visible and balanced
- Safety strip present
- Confirmation modal present
- No unsafe language anywhere
- Evidence shows all signals (including conflicts)
- Confidence is numeric
```

---

## Verification Checklist

After Stitch refinement, verify:

### Visual ✅
- [ ] Three decision buttons visible (Confirm, Defer, Reject)
- [ ] Buttons are balanced (not one giant button)
- [ ] Safety strip below metadata: "Suggested changes only. Confirmed households affect export staging only..."
- [ ] Scope copy below decision buttons: "Confirmed households affect export staging only..."
- [ ] Confidence score is numeric ("X% match")
- [ ] Evidence section shows all signals + conflicts
- [ ] Card structure preserved (name, members, evidence, decisions)

### Safety ✅
- [ ] No "Approve" or "Approve All" language
- [ ] No "Auto-" language
- [ ] No "Merge" language
- [ ] No "Writeback" language
- [ ] Confirmation modal present with correct text
- [ ] Modal buttons say "Cancel" and "Confirm Household"

### Functional ✅
- [ ] Clicking Confirm Household opens modal
- [ ] Modal has Cancel and Confirm buttons
- [ ] DonorTrust navigation present
- [ ] Left sidebar present
- [ ] Cards display confidently, evidence clearly

---

## Timeline

1. **Refinement:** Create Stitch variant with above prompt
2. **Verification:** Download fresh HTML/screenshots, check criteria
3. **Approval:** All visual + safety + functional checks pass
4. **Archive:** Save artifacts as design reference
5. **Implementation:** Use spec + reference artifacts for app development

---

**Status:** Ready for Stitch refinement  
**Specification:** households_review-spec.md (14 sections, acceptance criteria included)  
**Authority:** Spec + refined artifacts  
**Safety Level:** Audit-safe, reviewer-decision-explicit, raw-rows-immutable
