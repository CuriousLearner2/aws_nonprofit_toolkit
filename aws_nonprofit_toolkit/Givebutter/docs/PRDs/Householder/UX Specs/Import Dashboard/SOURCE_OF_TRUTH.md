# Import Dashboard — Folder Organization & Authority

**Last Updated:** 2026-06-11  
**Project:** DonorTrust / Householder v1 UX Workflow  
**Screen:** Import Dashboard

---

## Folder Roles

### 1. `Import Dashboard/` — Canonical Quick-Access Final Reference
**Purpose:** Fast visual review of the final Stitch design  
**Contents:**
- `FINAL_STATUS.md` — Design finalization record
- `README.md` — Quick overview
- `design.html` — Stitch-exported HTML (visual/structural reference)
- Screenshots at multiple resolutions (2x, 3x, highres)
- `stitch-prompt.md` — Design specifications (audit trail)
- `results.json` — Verification metadata
- `capture-summary.md` — Design capture notes

**Usage:**
- Use this folder for **quick visual review** of the final design
- Use `design.html` for **structural/visual reference**
- Do **not** treat this as fully accepted v1 implementation reference yet
- Implementation should use the eventual **local implementation-reference mock/spec as authority**, not raw Stitch HTML

### 2. `import-dashboard/` — Historical Iteration Archive
**Purpose:** Preserve full design progression for audit trail  
**Contents:**
- `iteration-001/` — First iteration
- `iteration-002/` — Second iteration
- `iteration-003/` — Third iteration
- `iteration-004/` — Final iteration (mirrors `Import Dashboard/`)

**Usage:**
- Preserves complete design history
- `iteration-004/` is the final Stitch iteration
- Do **not** delete earlier iterations without explicit approval
- Use for audit trail and historical context

---

## Authority Reference

| Item | Value |
|------|-------|
| **Screen Name** | Import Dashboard |
| **Final Stitch Screen ID** | `76ae1ecb02ec4c559bea438ad0012d0f` |
| **Final Iteration Folder** | `import-dashboard/iteration-004/` |
| **Quick-Access Folder** | `Import Dashboard/` |
| **Design Status** | Stitch Design Final |
| **Acceptance Status** | Pending Local Reference Cleanup |

---

## Current Status

**Stitch Design Final** ✅
- All 13 design changes applied
- All v1 constraints maintained
- Artifacts generated and verified
- Visual design accepted

**Pending Local Reference Cleanup** ⏳
- Vocabulary review needed
- Terms to address:
  - "Bulk Approval" → safer import-scoped language
  - "Approved Normalization" → safer language
  - "cleaned files" → "reviewed data" or "files with decisions reflected"
  - "householded files" → safer language
- Once cleanup complete → v1 Design Reference Accepted

---

## Next Steps

1. **Do not mark as "v1 Design Reference Accepted" yet**
   - Stitch HTML contains unsafe vocabulary
   - Needs local cleanup before acceptance

2. **Create local implementation-reference mock/spec**
   - Will become authority for implementation
   - Stitch HTML serves as visual reference only

3. **Vocabulary cleanup verification**
   - Replace unsafe terms with import-scoped/export-staging-safe language
   - Verify all 11 acceptance criteria

4. **Final acceptance**
   - Once cleanup complete and verified → v1 Design Reference Accepted

---

## Key Principle

**Folder Structure:**
- `Import Dashboard/` = Quick visual reference (Stitch final)
- `import-dashboard/` = Historical archive (full iterations)

**Authority Hierarchy:**
1. Local implementation-reference mock/spec (when created)
2. Stitch design.html (visual/structural reference only)
3. Historical iterations (audit trail)

---

**Created:** 2026-06-11  
**Authority:** Project documentation (this file)  
**Status:** Active organization guide
