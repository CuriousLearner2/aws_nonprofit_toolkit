# Export Console — Implementation Reference Mock

**Status:** Local implementation reference created (not a Stitch update)  
**Date:** 2026-06-11  
**Type:** Implementation reference mock  
**Source:** Specification-driven (export_console-spec.md)

---

## ⚠️ Important Clarification

**This reference mock was created because:**

1. Stitch SDK requires MCP infrastructure unavailable in current environment
2. Stitch variants/edit methods cannot be called without MCP server
3. This is a local implementation-reference artifact, not a Stitch screen update

**This is NOT a claim that any Stitch screen has been created or refined.**

This reference mock is a corrected implementation guide based on the specification, created locally as a visual and structural reference for implementation.

---

## What This Contains

### 1. **export_console-spec.md** ⭐ AUTHORITY
The authoritative specification for this screen (14 sections, 11 acceptance criteria).

**Contains:**
- Core principle: System prepares exports, reviewer chooses downloads, raw rows unchanged, no CRM writeback
- Safety constraints: All actions logged, no external system integration, clear messaging
- Detailed layout: Navigation, safety banner, export cards, right sidebar, sticky action bar
- 4 canonical export cards: Reviewed, Household, Backlog, Raw
- Confirmation modal specification
- Safe action language definitions (10 forbidden terms removed, replacements defined)
- 11 acceptance criteria (visual, safety, functional)
- Export status definitions
- DonorTrust v1 styling direction

**Use this for:** Implementation specification, QA verification, design review, authority reference

### 2. **REFINEMENT_PLAN.md**
Actionable summary of vocabulary changes required for export-safe design.

**Contains:**
- 10 unsafe language terms + safe replacements
- Canonical export card names (enforced)
- Canonical action labels (enforced)
- Critical safety requirements (5 items)
- Verification checklist
- Do's and Don'ts
- Timeline

**Use this for:** Quick reference on what needs to change, vocabulary mapping, safety review

### 3. **design-reference.html**
Corrected local HTML reference with export-safe design applied.

**Contains:**
- DonorTrust v1 navigation (Exports tab active)
- Safety banner (Review decisions logged | Raw rows unchanged | Exports ready)
- Left sidebar: Data Controls (5 filters)
- Page title: "Export Console"
- Page description with "No data is written back..." message
- 4 export cards with safe vocabulary:
  - Reviewed Export (Generated status)
  - Household Export (Ready status)
  - Backlog Export (Pending Review status, with caution copy)
  - Raw Export (Ready status, with caution copy)
- Each card includes: description, metadata, caution copy, footer copy, download button
- Right sidebar: Export History (optional)
- Sticky bottom action bar: "Generate Export Package" button
- Confirmation modal with export-safe messaging
- Footer safety message (4 guarantees)
- DonorTrust v1 styling

**Key Features:**
- ✅ No unsafe language (sync, CRM, finalized, auto-export, master record, etc.)
- ✅ 4 canonical export card names
- ✅ 5 canonical action labels
- ✅ Confirmation modal before export
- ✅ Safety messaging throughout (banner + footer + caution)
- ✅ No external system integration language
- ✅ Raw rows immutable messaging
- ✅ DonorTrust v1 pattern preserved

**Use this for:** Visual/structural reference, copy templates, design guidance, implementation reference

---

## Export Card Vocabulary (Final)

### Card Names
- ✅ Reviewed Export (not "Export Clean" or "Finalized Export")
- ✅ Household Export
- ✅ Backlog Export
- ✅ Raw Export

### Action Labels
- ✅ Download Reviewed CSV
- ✅ Download Household CSV
- ✅ Download Backlog CSV
- ✅ Download Raw CSV
- ✅ Generate Export Package (button)

### Status Badges
- ✅ Generated (blue)
- ✅ Ready (green)
- ✅ Pending Review (amber)

---

## Unsafe Language Removed (Old → New)

### Button/Action Language
- ❌ "Finalize Batch Export" → ✅ "Generate Export Package"
- ❌ "Export Clean" → ✅ "Reviewed Export"
- ❌ "Last sync" → ✅ "Last generated" or "Last export"

### Feature Descriptions
- ❌ "donor CRM ingestion" → ✅ "reviewed CSV output" or "manual downstream import/review"
- ❌ "Connected to Secure Audit Vault" → ✅ "Audit logging enabled" (unless explicitly v1 infrastructure)

### Status Labels
- ❌ "FINALIZED" → ✅ "Generated" or "Ready" or "Reviewed Output"

### Messaging
- ✅ ADDED: "No data is written back to Givebutter or any CRM"
- ✅ ADDED: Backlog caution copy
- ✅ ADDED: Raw caution copy
- ✅ ADDED: Confirmation modal

---

## How to Use This Reference

### For Implementation
1. Use `export_console-spec.md` as the authoritative specification (NOT this mock)
2. Use `design-reference.html` as visual/structural reference for:
   - DonorTrust v1 navigation and styling
   - 4 export card layout and structure
   - Safety banner and footer messaging
   - Sticky action bar placement
   - Modal confirmation pattern
3. Follow spec section 5 for exact safe language terminology
4. Copy the color scheme and typography from the design reference
5. Implement the 4 export cards with all required caution copy
6. Include confirmation modal as specified
7. Pass all 11 acceptance criteria from spec section 11

### For Design Review
1. Use `design-reference.html` to visually inspect:
   - DonorTrust v1 consistency (navigation, sidebar, layout)
   - 4 export cards visible and properly labeled
   - Safe vocabulary used throughout (no sync, CRM, finalized, etc.)
   - Safety banner and footer present
   - Confirmation modal visible
   - Caution copy on Backlog and Raw cards
2. Use `verification.json` to confirm checks pass
3. Compare against `export_console-spec.md` section 12 (Visual Design Direction)

### For QA Verification
1. Use `export_console-spec.md` section 11 (11 Acceptance Criteria) as test checklist
2. Verify visual requirements:
   - Navigation correct, Exports tab active
   - Safety banner visible
   - 4 export cards present and labeled correctly
   - Right sidebar (Export History) present if in design
   - Sticky action bar present with "Generate Export Package" button
3. Verify safety requirements:
   - No unsafe language in ANY copy
   - All card names are canonical
   - All action labels are canonical
   - "No data is written back..." message present
   - Caution copy on Backlog and Raw cards
   - Safety banner and footer present
4. Verify functional requirements:
   - Filters work (by batch status, review completion, export type, date range, source)
   - Date range search works
   - Source file filter works
   - "Generate Export Package" button opens modal
   - Modal has clear confirmation language
   - Download buttons present on all cards
   - Export History displays correctly

---

## Key Safety Guarantees

This design ensures:
- ✅ Raw import rows are **never mutated** by exports
- ✅ Exports prepare **files for download only**
- ✅ No automatic sync or writeback to **external systems** (Givebutter, CRM, etc.)
- ✅ Every export action is **logged to audit trail**
- ✅ All references are **import-scoped** (not external)
- ✅ Reviewer has **explicit control** (no auto-export)
- ✅ Full **transparency** (clear caution messaging)

---

## DonorTrust v1 Consistency

This screen follows DonorTrust v1 patterns:
- ✅ Top navigation bar with tabs (Exports active)
- ✅ Left sidebar (Data Controls / Filters)
- ✅ Card-based content structure
- ✅ Safety banner (prominent, clear)
- ✅ Sticky action bar (main controls at bottom)
- ✅ Right sidebar (optional export history)
- ✅ Confirmation modal (prevents accidental actions)
- ✅ High contrast, readable typography (WCAG AA)

---

## Files in Folder

| File | Purpose |
|------|---------|
| `export_console-spec.md` | Authoritative specification (14 sections, 11 acceptance criteria) |
| `REFINEMENT_PLAN.md` | Summary of 10 vocabulary changes + implementation guide |
| `design-reference.html` | Corrected implementation reference with safe vocabulary |
| `verification.json` | Machine-readable checks (52/52 checks passing) |
| `REFERENCE_MOCK_NOTES.md` | This file; explains local mock purpose and usage |
| `README.md` | Orientation document |
| `ACCEPTANCE_RECORD.md` | Formal acceptance record (v1 Design Reference Accepted) |

---

## Authority & Next Steps

**Authority:**
- `export_console-spec.md` (Specification)
- `design-reference.html` (Visual/Structural Reference)
- `verification.json` (Validation)

**For implementation:**
1. ✅ Specification created (`export_console-spec.md`)
2. ✅ Reference mock created (`design-reference.html`)
3. ✅ Refinement plan created (`REFINEMENT_PLAN.md`)
4. → Build from the spec, not by copying this HTML
5. → Use this reference mock for visual/structural guidance
6. → Follow all safety constraints from spec section 2
7. → Pass all 11 acceptance criteria from spec section 11

**Timeline:**
1. ✅ Specification created
2. ✅ Reference mock created & documented
3. → Implementation in app code
4. → QA verification against spec
5. → Deployment

---

**Created:** 2026-06-11  
**Type:** Local implementation reference (not a Stitch update)  
**Authority:** Specification + Reference mock  
**Status:** Ready for implementation  
**Safety Level:** Export-safe, import-scoped, human-verified, no external system integration
