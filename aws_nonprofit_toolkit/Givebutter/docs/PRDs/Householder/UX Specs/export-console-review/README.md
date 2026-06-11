# Export Console — Design Reference

**Status:** Specification complete | Reference mock created | Ready for implementation  
**Screen:** Export Console (v1 Final)  
**Type:** Local implementation-reference mock (not a Stitch update)  
**Authority:** export_console-spec.md + design-reference.html  
**Verification:** 52/52 checks passing (strict v1 vocabulary compliance)

---

## 📄 Key Documents

### **export_console-spec.md** ⭐ AUTHORITY
The authoritative specification for this screen (14 sections, 11 acceptance criteria).

**Contains:**
- Core principle: System prepares exports, reviewer chooses downloads, raw rows unchanged, no CRM writeback
- Safety constraints: All actions logged, import-scoped only, no external system integration
- Detailed layout: Navigation, safety banner, 4 export cards, right sidebar, sticky action bar
- 4 canonical export cards: Reviewed, Household, Backlog, Raw
- Confirmation modal specification with export-safe messaging
- Safe/unsafe language definitions (10 unsafe terms removed, replacements defined)
- 11 acceptance criteria (visual, safety, functional)
- Export status definitions (Generated, Ready, Pending Review, Audit Ready)
- DonorTrust v1 styling direction

**Use this for:** Implementation specification, QA verification, design review, authority reference

### **REFINEMENT_PLAN.md**
Actionable summary of 10 vocabulary changes and implementation guidance.

**Contains:**
- Vocabulary refinement table (unsafe → safe)
- Core vocabulary definitions
- Canonical card/action labels
- 5 critical safety requirements
- Design requirements (preserved structure)
- Forbidden language list
- Verification checklist
- Do's and Don'ts

**Use this for:** Quick reference on what needs to change, vocabulary mapping, implementation guidance

### **design-reference.html**
Corrected local HTML reference with export-safe design applied.

**Contains:**
- Complete DonorTrust v1 layout: navigation, safety banner, sidebars, sticky action bar
- 4 export cards with safe names: Reviewed, Household, Backlog, Raw
- Each card: header, description, metadata, caution (if applicable), footer, download button
- Caution copy on Backlog and Raw cards
- Right sidebar: Export History (optional)
- Sticky action bar: "Generate Export Package" button
- Confirmation modal: "Generate Export Package?" with export-safe messaging
- Footer: 4-item safety guarantee message
- DonorTrust v1 styling (colors, typography, accessibility)

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

## 🎯 Problem & Solution

### Problem
Export preparation must be safe, reviewer-controlled, and audit-logged. Current approach risks:
- Unsafe language (sync, CRM integration, finalized states)
- Missing confirmation steps (prevents accidental exports)
- Unclear export scope (does it affect external systems?)
- Missing caution messaging (especially for pending/unresolved records)

### Solution
Make the design **export-safe** and **import-scoped**:
1. Remove all 10 unsafe language terms completely
2. Replace with import-scoped safe language (generated, reviewed, download-only)
3. Add confirmation modal before export generation
4. Add explicit copy: "No data is written back to Givebutter or any CRM"
5. Use 4 canonical export card types with clear purposes
6. Include caution copy on Backlog (unresolved) and Raw (original) exports
7. Maintain full audit trail (searchable, exportable)

---

## 📋 Vocabulary Migration (Old → New)

| Old (Unsafe) | New (Safe v1) | Context |
|------|-----------------|---------|
| "Finalize Batch Export" | "Generate Export Package" | Button/action (generates files, not permanent) |
| "Export Clean" | "Reviewed Export" | Export card type (explicit about reviewer decisions) |
| "Last sync" | "Last generated" | Timestamp label (no continuous sync) |
| "donor CRM ingestion" | "manual downstream import/review" | Feature description (v1 doesn't push to CRM) |
| "Connected to Secure Audit Vault" | "Audit logging enabled" | Status/feature (if not explicit v1 infrastructure) |
| "FINALIZED" | "Generated" or "Ready" | Status badge (no permanent state implied) |
| (N/A) | "No data is written back to Givebutter or any CRM" | NEW: Required safety message |
| "apply all" / "approve all" | (Removed; individual downloads only) | Actions (v1 has no bulk export) |
| "auto-export" / "auto-apply" | (Not present; exports are reviewer-triggered) | Features (explicit reviewer action required) |

---

## ✅ Acceptance Criteria (11 total)

### Visual ✅
- [ ] DonorTrust navigation (Exports tab active)
- [ ] Safety banner visible below navigation
- [ ] Page title and description present
- [ ] 4 export cards visible (Reviewed, Household, Backlog, Raw)
- [ ] Each card has status badge and download button
- [ ] Right sidebar (Export History) visible if in design
- [ ] Sticky action bar present with "Generate Export Package" button
- [ ] Confirmation modal visible when button clicked
- [ ] Footer safety messaging present

### Safety ✅
- [ ] No "sync" language
- [ ] No "CRM ingestion" or "CRM writeback" language
- [ ] No "finalized" language (use "Generated" or "Ready")
- [ ] No "apply all" or "approve all" language
- [ ] No "auto-export" or "auto-apply" language
- [ ] No "master record" or "master database" language
- [ ] All card names are canonical (Reviewed, Household, Backlog, Raw)
- [ ] All action labels are canonical (Download [Type] CSV, Generate Export Package)
- [ ] Clear message: "No data is written back to Givebutter or any CRM"
- [ ] Caution copy on Backlog and Raw cards

### Functional ✅
- [ ] Filters work (by batch status, review completion, export type, date range, source file)
- [ ] Date range search works
- [ ] Source file filter works
- [ ] "Generate Export Package" button opens modal
- [ ] Modal has clear confirmation language
- [ ] Download buttons work (or placeholder for demo)
- [ ] Export History displays correctly
- [ ] Timestamps accurate and searchable

---

## 🔒 Safety Guarantees

This design ensures:
- ✅ Raw import rows are **never mutated** by exports
- ✅ Exports prepare **files for download only**
- ✅ No automatic sync or writeback to **external systems** (Givebutter, CRM, etc.)
- ✅ Every export action is **logged to audit trail**
- ✅ All references are **import-scoped** (not external)
- ✅ Reviewer has **explicit control** (no auto-export)
- ✅ Full **transparency** (caution messaging on pending/original data)

---

## 📚 DonorTrust v1 Consistency

This screen follows DonorTrust v1 patterns:
- ✅ Top navigation bar with tabs (Exports active)
- ✅ Left sidebar (Data Controls / Filters)
- ✅ Card-based content structure
- ✅ Safety banner (prominent, clear)
- ✅ Sticky action bar (main controls at bottom)
- ✅ Right sidebar (optional export history)
- ✅ Confirmation modal (prevents accidental actions)
- ✅ High contrast, readable typography (WCAG AA)

See `export_console-spec.md` section 12 for detailed styling direction.

---

## 🚀 Next Steps

### For Implementation
1. Use `export_console-spec.md` as the authoritative specification
2. Reference `design-reference.html` for visual/structural guidance
3. Copy safe language patterns from spec section 5
4. Implement 4 export cards with canonical names
5. Implement 5 action labels exactly as specified
6. Include confirmation modal before export
7. Include caution copy on Backlog and Raw cards
8. Pass all 11 acceptance criteria before considering done

### For Design Review
1. Use `design-reference.html` to visually inspect layout and styling
2. Verify no unsafe language present
3. Check DonorTrust v1 consistency
4. Compare against `export_console-spec.md` sections 3, 4, 5, 12
5. Review `verification.json` (52/52 checks pass)

### For QA Verification
1. Use `export_console-spec.md` section 11 as test checklist (11 acceptance criteria)
2. Verify all safety language requirements
3. Test all filter and search functionality
4. Verify modal opens and works correctly
5. Confirm export cards present with correct labels
6. Check caution copy on Backlog and Raw cards

---

## 📊 Verification

**Machine-readable verification:** See `verification.json`
- 14 forbidden language checks ✅ (0/14 found)
- 12 required vocabulary checks ✅ (12/12 present)
- 13 design structure checks ✅
- 4 safe language verification checks ✅
- 9 specification alignment checks ✅
- **Total: 52/52 checks pass**

---

## 📁 Files in This Folder

| File | Purpose | Type |
|------|---------|------|
| `export_console-spec.md` | Authoritative specification (14 sections, 11 acceptance criteria) | Specification |
| `REFINEMENT_PLAN.md` | Summary of vocabulary changes + implementation guide | Reference |
| `design-reference.html` | Corrected implementation reference with safe vocabulary | Reference |
| `verification.json` | Machine-readable checks (52/52 pass) | Verification |
| `REFERENCE_MOCK_NOTES.md` | Explains local mock purpose and usage | Documentation |
| `README.md` | This file; orientation document | Documentation |

---

## 🔗 Related Screens

- **Audit Log:** Activity tracking with safe vocabulary and audit logging
- **All Records / Validation Review:** Table-based import review with safe status indicators
- **Households Review:** Household suggestion confirmation with modal confirmation pattern

---

## ⚠️ Important Notes

**This is a local implementation-reference mock**, not a Stitch screen update:
- Created locally because Stitch SDK requires MCP infrastructure unavailable in current environment
- Specification is authoritative; this mock implements that specification
- Use for visual/structural reference in implementation, not as source-of-truth code
- Do not manually patch this HTML; use it as guidance, then build your own implementation

**For implementation:**
- Build from `export_console-spec.md` (specification), not from this HTML
- Use this HTML reference for visual/structural patterns
- Follow all safety constraints from spec section 2
- Pass all 11 acceptance criteria from spec section 11 before considering done

---

**Created:** 2026-06-11  
**Authority:** export_console-spec.md + design-reference.html  
**Status:** Specification complete, reference mock created, ready for implementation  
**Safety Level:** Export-safe, import-scoped, human-verified, no external system integration  
**Verification:** 52/52 checks pass ✅
