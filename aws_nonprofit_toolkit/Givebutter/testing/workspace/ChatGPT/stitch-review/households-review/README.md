# Households Review — Design Refinement

**Status:** Specification complete | Ready for Stitch refinement  
**Screen:** Households Review (Suggested Household Confirmation)  
**Stitch Node ID:** 301d7906577449908563bb9a591b88f7  
**Preview URL:** https://stitch.withgoogle.com/preview/9371274764538076058?node-id=301d7906577449908563bb9a591b88f7

---

## 📄 Key Documents

### **households_review-spec.md** ⭐ AUTHORITY
The authoritative specification for this screen (14 sections, 11 acceptance criteria).

**Contains:**
- Core principle: System suggests, reviewer confirms/defers/rejects
- Safety constraints and audit-safe patterns
- Detailed layout and card structure
- Decision modal specifications
- Confirmation flow and state management
- 11 acceptance criteria (visual, safety, functional)
- DonorTrust v1 styling direction

**Use this for:** Implementation, QA verification, design review

### **REFINEMENT_PLAN.md**
Actionable summary of changes needed to audit-safe design.

**Contains:**
- 9 critical changes (decision buttons, modals, copy, safety)
- Stitch refinement prompt (ready to copy-paste)
- Verification checklist
- Timeline

**Use this for:** Stitch refinement, quick reference on what to change

---

## 🎯 Problem & Solution

### Problem
The current screen is **approval-forward**:
- Single dominant "Approve Household" button
- Lacks confirmation modal
- Missing explicit scope copy
- Unsafe language possible
- Doesn't clearly show evidence of system's reasoning

### Solution
Make the design **reviewer-decision-explicit** and **audit-safe**:
1. Replace single button with three balanced options: Confirm, Defer, Reject
2. Add confirmation modal to prevent accidental confirms
3. Add explicit copy: "Raw import rows are never changed"
4. Show all evidence (including conflicts) to reviewer
5. Use numeric confidence consistently
6. Log every decision to audit trail

---

## 📋 Critical Changes at a Glance

| Change | Current | Required |
|--------|---------|----------|
| **Decision Button** | Single "Approve" (dominant) | Three balanced buttons: Confirm, Defer, Reject |
| **Modal** | Likely absent | Confirm modal with explicit text |
| **Scope Copy** | Likely absent | "Confirmed households affect export staging only. Raw import rows will not be changed." |
| **Safety Strip** | Generic or absent | "Suggested changes only. Confirmed households affect export staging only. Raw import rows are never changed." |
| **Confidence** | Possibly vague | Numeric: "98% match", "95%+ similarity" |
| **Evidence** | May hide conflicts | Show ALL signals + conflicts transparently |
| **Unsafe Language** | Possible: Auto-household, Merge, Writeback | None—use: Confirm, Defer, Reject, Export staging |

---

## ✅ Acceptance Criteria (11 total)

### Visual ✅
- Three decision buttons visible (Confirm, Defer, Reject) in balanced row
- Safety strip visible below title
- Scope copy visible below decision buttons
- Confidence score numeric ("98% match")
- Evidence section shows all signals + conflicts
- DonorTrust v1 styling preserved

### Safety ✅
- No "Approve All" language
- No "Auto-" prefix language
- No "Merge" or "Writeback" language
- Confirmation modal present with correct copy
- Modal buttons: Cancel | Confirm Household

### Functional ✅
- Clicking Confirm opens modal
- Modal confirms with audit logging
- Defer and Reject buttons work
- Evidence displays all signals (including conflicts)
- Sidebar filters work

---

## 🚀 Next Steps

### For Stitch Refinement
1. Open Stitch screen (node ID: 301d7906577449908563bb9a591b88f7)
2. Copy the refinement prompt from REFINEMENT_PLAN.md
3. Use `screen.variants()` method to create refined variant
4. Download fresh HTML and screenshots
5. Verify against 11 acceptance criteria
6. Archive artifacts as design reference

### For Implementation
1. Use `households_review-spec.md` as authority
2. Reference refined artifacts as visual guide
3. Build from the specification (not from manual patches)
4. Follow DonorTrust v1 styling direction (section 12)
5. Implement all three decision flows: Confirm, Defer, Reject
6. Include confirmation modal

---

## 🔒 Safety Guarantees

This design ensures:
- ✅ Raw import rows are **never mutated**
- ✅ Suggested households affect **export staging only**
- ✅ Every decision is **audit logged**
- ✅ No automatic household creation
- ✅ No CRM writeback from this screen
- ✅ Reviewer **intent is explicit** (no approve-all shortcuts)

---

## 📚 DonorTrust v1 Consistency

This screen follows DonorTrust v1 patterns:
- Top navigation bar (Households active)
- Left sidebar (Data Controls / Batch Filters)
- Card-based content structure
- Clear hierarchy and action buttons
- Audit-safe copy and patterns
- High contrast, readable typography

See section 12 of spec for styling direction.

---

## 🔗 Related

- **All Records / Validation Review:** Similar audit-safe pattern (10-column table)
- **Normalization Review:** Modal confirmation pattern (same approach)
- **Stitch Project:** https://stitch.withgoogle.com/projects/9371274764538076058

---

**Created:** 2026-06-10  
**Authority:** households_review-spec.md + refined artifacts  
**Status:** Specification complete, ready for Stitch refinement  
**Safety Level:** Audit-safe, reviewer-decision-explicit, raw-rows-immutable
