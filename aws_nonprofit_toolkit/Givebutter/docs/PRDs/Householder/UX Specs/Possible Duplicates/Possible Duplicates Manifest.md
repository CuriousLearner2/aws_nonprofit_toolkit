# Duplicate Candidate Review — Manifest Entry

## Screen Identification
- **Name:** Possible Duplicate in This Import
- **Scope:** v1 (Current Import Only)
- **Status:** ✅ Design Finalized, Needs Packaging
- **Route:** `/imports/<import_id>/duplicates/<candidate_id>`
- **Final Stitch URL:** https://web.application/stitch/projects/9371274764538076058/screens/a1a45428a98046b28a56ee0390d09a65

## Artifact Paths
- **HTML Export**: `docs/ux/duplicate-candidate-review/duplicate-candidate-review-final.html`
- **Screenshot**: `docs/ux/duplicate-candidate-review/duplicate-candidate-review-final-screenshot.png`
- **Stitch Notes**: `docs/ux/duplicate-candidate-review/duplicate-candidate-review-stitch-recreation-notes.md`
- **README**: `docs/ux/duplicate-candidate-review/README.md`

## Summary of Key Components
- **Comparison Engine**: Side-by-side Contact A vs Contact B layouts.
- **Evidence Panels**: Distinct Supporting Evidence and Conflicting Evidence sections.
- **Accountability UX**: Reasoning required when conflicting evidence exists; the finalized example is an address conflict.
- **Details Drawer**: Persistent right-side panel for candidate context.

## Implementation Notes
- **Primary Data**: `duplicate_candidates` table.
- **Contact Data**: `contacts` table for Contact A and Contact B.
- **Donation Context**: Current-import donation rows associated with the same `import_id`.
- **Audit Output**: `duplicate_candidates.decision`, `duplicate_candidates.reviewer_notes`, `decided_by`, `decided_at`.
- **Claude Code Guidance**:
  - Use existing Flask/Jinja architecture.
  - Do not create a React app.
  - Wire “Mark as Same Person” disabled state to reviewer reasoning when conflicting evidence exists.
  - Log every decision with operator ID, timestamp, decision type, candidate ID, and reviewer notes when provided or required.
  - No contact merge occurs in v1.

## v1 Exclusions / Forbidden Concepts
- NO lifetime giving or lifetime donor profiles.
- NO master person IDs or historical record linking.
- NO global households.
- NO automated resolution.
- NO automatic merges or automatic approvals.
- NO Givebutter writeback.
- NO cross-import matching or global identity.
- **Record-Only**: Saves reviewer decision only; no contact entities, donation transactions, raw CSV rows, or Givebutter records are modified.
