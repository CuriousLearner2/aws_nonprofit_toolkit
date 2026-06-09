# Upload / Import Queue Screen Artifacts

This folder contains the finalized v1 Upload / Import Queue screen artifacts.

## Files

- `upload-screen-final.html` — standalone HTML visual reference (rendered from production Flask/Jinja template)
- `upload-screen-final-screenshot.png` — final accepted screenshot at 1500px viewport
- `upload-screen-stitch-reimport-notes.md` — notes for recreating/importing this screen in Stitch
- `upload-screen-manifest-entry.md` — manifest entry for the v1 screen manifest

## Status

✅ **Finalized v1 visual target**

All columns display correctly:
- Filename (readable, single-line with ellipsis, tooltip for full filename)
- Uploaded (relative time format)
- Total Rows (numeric)
- Validation (color-coded badges)
- Normalizations (pending count)
- Households (suggested count)
- Duplicates (candidates count)
- Status (full text: "Pending Review", "In Review", "Completed")
- Action (buttons: "Review Import", "Continue Review", "View Summary")

## Important v1 Scope

This screen is v1-scoped and **does not include** v2 concepts:
- Current import only (no cross-import matching)
- Raw rows preserved unchanged
- Suggestions generated as pending review (no automatic approvals)
- No merges on upload
- No Givebutter writeback
- No household creation
- No identity linking

## Usage

The standalone HTML is a **visual reference** for design and Stitch recreation. Production behavior remains governed by the v1 PRD and the existing Flask/Jinja implementation at `scripts/uploader/templates/review.html`.

## Reuse Notes

For Claude Code:
- Use `upload-screen-final.html` as a visual check-in against future changes
- Reference `upload-screen-manifest-entry.md` for feature requirements and backend mapping

For Stitch:
- Use `upload-screen-stitch-reimport-notes.md` for recreation/reimport guidance
- `upload-screen-final.html` provides the DOM structure and CSS reference
- Preserve the v1 safety messaging and constraints

## Implementation Status

✅ DonorTrust header with navigation  
✅ Safety banner with v1 messaging  
✅ Upload Givebutter CSV card with drag-and-drop  
✅ v1 Safety Mode panel with 7 safety checkpoints and live stats  
✅ Current Import Queue table with 9 columns  
✅ Status and Action columns (separate, both fully readable)  
✅ Horizontal scrolling with sticky Action column  
✅ Color-coded validation badges  
✅ Relative timestamp formatting  
✅ Single-line filename with ellipsis and tooltip  
✅ All 8 E2E tests passing  

## Related Files

- Production template: `scripts/uploader/templates/review.html`
- Production app: `scripts/uploader/app.py`
- E2E tests: `tests/e2e/test_e2e_upload_workflow.py`
- v1 PRD: `docs/PRDs/Householder/Householder-PRD-v1-final.md`
- Implementation Plan: `docs/PRDs/Householder/Implementation Plan - Householder v1.md`
