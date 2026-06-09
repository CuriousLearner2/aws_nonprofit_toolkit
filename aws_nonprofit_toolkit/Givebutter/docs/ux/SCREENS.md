# Householder v1 — Finalized Screen Artifacts

This index tracks all finalized UX screens for Householder v1 and provides quick links to artifacts, screenshots, and reimport notes.

## Status Summary

| Screen | Status | Artifacts | Stitch Notes |
|--------|--------|-----------|--------------|
| Upload / Import Queue | ✅ Finalized + Implemented | [View](./upload-screen/) | [Read](./upload-screen/upload-screen-stitch-reimport-notes.md) |
| Duplicate Candidate Review | 🔄 Design Finalized, Not Yet Packaged | — | — |
| All Records Review | 📋 Planned | — | — |
| Normalizations Review | 📋 Planned | — | — |
| Households Review | 📋 Planned | — | — |
| Export Console | 📋 Planned | — | — |
| Audit Log | 📋 Planned | — | — |

## Finalized Screens

### Upload / Import Queue

**Purpose:** Safe CSV import entry point showing active import batches in a scrollable queue.

**Artifacts:**
- 📄 [HTML Reference](./upload-screen/upload-screen-final.html)
- 📸 [Screenshot](./upload-screen/upload-screen-final-screenshot.png)
- 📖 [README](./upload-screen/README.md)
- 🔧 [Stitch Reimport Notes](./upload-screen/upload-screen-stitch-reimport-notes.md)
- 📋 [Manifest Entry](./upload-screen/upload-screen-manifest-entry.md)

**Key Features:**
- DonorTrust top navigation
- Safety banner with v1 messaging
- Upload Givebutter CSV card (drag-and-drop)
- v1 Safety Mode panel (7 checkpoints + live stats)
- Current Import Queue table (9 columns, scrollable, sticky Action column)
- Status/Action mapping (Pending Review → Review Import, In Review → Continue Review, Completed → View Summary)

**Tables Used:**
- `imports` (create, query active batches)
- `raw_import_rows` (immutable storage)
- `contacts` (baseline extraction)
- Suggestion tables (validation, normalizations, households, duplicates)
- Operator decisions (status computation)

**v1 Safety Constraints:**
- ✅ Non-destructive suggestions only
- ✅ Raw rows immutable
- ✅ All suggestions pending approval
- ✅ No automatic merges or approvals
- ❌ No cross-import matching (v2)
- ❌ No Givebutter writeback
- ❌ No master people or global households (v2)

---

## Planned Screens (v1 Roadmap)

### Duplicate Candidate Review
- **Purpose:** Side-by-side comparison of potential intra-file duplicates
- **Status:** Design Finalized, Not Yet Packaged
- **Artifacts:** Coming soon (design exists in Stitch, artifact package pending)

### All Records Review
- **Purpose:** Master table of all records with validation status (PASS/WARNING/FAIL)
- **Status:** Planned
- **Artifacts:** TBD

### Normalizations Review
- **Purpose:** Quick-action queue for typo and formatting suggestions
- **Status:** Planned
- **Artifacts:** TBD

### Households Review
- **Purpose:** Address-based household grouping suggestions
- **Status:** Planned
- **Artifacts:** TBD

### Export Console
- **Purpose:** Download reviewed and approved data in clean formats
- **Status:** Planned
- **Artifacts:** TBD

### Audit Log
- **Purpose:** Searchable trail of all reviewer decisions
- **Status:** Planned
- **Artifacts:** TBD

---

## Artifact Package Structure

Each finalized screen gets a dedicated folder:

```
docs/ux/{screen-name}/
  README.md                         # Overview and usage notes
  {screen}-final.html               # Standalone HTML reference
  {screen}-final-screenshot.png     # Accepted screenshot
  {screen}-stitch-reimport-notes.md # Stitch recreation guidance
  {screen}-manifest-entry.md        # Feature/data requirements
```

---

## For Claude Code Contributors

When implementing or updating a finalized screen:

1. **Check this index** — Verify the screen is finalized
2. **Read the artifact README** — Understand the design intent and constraints
3. **Reference the HTML** — Compare your implementation against the visual target
4. **Check the manifest entry** — Verify you're meeting all feature and data requirements
5. **Test against the screenshot** — Ensure visual parity (allow for viewport differences)
6. **Run existing E2E tests** — Confirm no regressions

---

## For Stitch Designers / UX Teams

When recreating or reimporting a finalized screen in Stitch:

1. **Start with the README** — Understand the design goals
2. **Open the HTML in a browser** — Study the exact layout, spacing, colors
3. **Read the Stitch Notes** — Follow step-by-step recreation guidance
4. **Use the manifest entry** — Understand the data model and feature requirements
5. **Reference the screenshot** — Verify visual accuracy

---

## For Project Managers

Each finalized screen has:

- ✅ Production implementation (tested, passing E2E tests)
- ✅ Design artifacts (HTML reference, screenshot, notes)
- ✅ Feature manifest (data requirements, API endpoints, user actions)
- ✅ Stitch reimport guidance (for design collaboration)

Use this index to track v1 completion and to brief new contributors on what's been finalized.

---

## Historical Notes

### Upload / Import Queue

**Finalization Date:** 2026-06-09  
**Key Decisions:**
- Status and Action columns kept separate (both fully readable, no truncation)
- Horizontal scrolling with sticky Action column (min-width 1320px)
- Filename display: single-line with ellipsis, full name in tooltip
- v1 Safety Mode panel: 7 checkpoints + 3 live stats
- Status computed from reviewer decision count, not static

**Commits:**
- `b9c082c` — Resolve Status column truncation issue

---

## Quick Links

- [v1 PRD](../PRDs/Householder/Householder-PRD-v1-final.md)
- [Implementation Plan](../PRDs/Implementation/Householder/Implementation\ Plan\ -\ Householder\ v1.md)
- [Possible Duplicates Manifest (Design Brief)](../PRDs/Householder/UX\ Specs/Possible\ Duplicates\ Manifest.txt)
- [Production Template](../../scripts/uploader/templates/review.html)
- [E2E Tests](../../tests/e2e/test_e2e_upload_workflow.py)
