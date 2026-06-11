# ⚠️ Visual Reference Only — Implementation Spec Overrides

**Status:** Stitch artifacts archived as visual design reference  
**Date:** 2026-06-11  
**Issue:** Stitch API reported successful edits/refines, but exported artifacts remained stale or regressed changes
**Authority:** See `normalization_review-spec.md` for definitive requirements

## What's Here
- `design.html` — Stitch export (visual baseline only)
- Screenshots — Stitch previews (visual direction only)
- `results.json`, `README.md` — Design iteration metadata (reference only)

## What This IS
✅ Visual design direction for DonorTrust v1 style  
✅ UI component layout reference  
✅ Color, typography, spacing precedent  

## What This Is NOT
❌ Implementation source of truth  
❌ Copy specification (use spec.md instead)  
❌ Behavior specification (use spec.md instead)  
❌ Acceptance criteria (use spec.md instead)  

## Authority
**See:** `normalization_review-spec.md` (definitive specification)

This specification document:
- Overrides any Stitch artifact detail
- Defines exact copy, behavior, and acceptance criteria
- Is the source of truth for implementation

---

## Implementation Requirements

Do not:
- ❌ Manually patch these Stitch artifacts
- ❌ Treat Stitch API success as final
- ❌ Implement from Stitch HTML directly

Do:
- ✅ Implement per `normalization_review-spec.md`
- ✅ Use these artifacts for visual direction only
- ✅ Verify with app code + Playwright

---

## Stitch Lessons Learned

The Stitch design tool was helpful for visual direction, but API refinement showed:
- API success reports were unreliable
- Exported HTML became stale
- Further refinements regressed visible changes
- Persistence between edit operations and exports was inconsistent

Therefore:
- Visual reference: Useful
- API source of truth: Not reliable
- Implementation: Must follow this specification, not Stitch artifacts

