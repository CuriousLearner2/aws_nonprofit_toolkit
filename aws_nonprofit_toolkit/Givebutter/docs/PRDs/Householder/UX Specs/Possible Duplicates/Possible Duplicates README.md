# Duplicate Candidate Review — README

## Screen Purpose
Review whether two contact records from the same uploaded CSV appear to represent the same person. This is the primary human-in-the-loop deduplication interface for the v1 release.

## Current Maturity/Status
✅ **Design Finalized, Needs Packaging**

## Final Visual Target
- **Stitch URL**: https://web.application/stitch/projects/9371274764538076058/screens/a1a45428a98046b28a56ee0390d09a65

## Key UX Decisions
- **Side-by-Side Comparison**: Contact A and Contact B are presented in identical vertical cards for easy field-level scanning.
- **Evidence-Based Logic**: Explicit lists for Supporting Evidence and Conflicting Evidence guide the reviewer.
- **Forced Accountability**: When conflicting evidence exists, reviewer reasoning is required before the reviewer can mark the records as the same person. The current finalized example is an address conflict.
- **Context Drawer**: Persistent right-side drawer provides Duplicate Candidate Details and import context without displacing the comparison cards.

## v1 Safety Constraints
- **Decision-Only**: “Mark as Same Person” records reviewer judgment only. It does not merge contact entities, merge donation transactions, overwrite raw fields, change original CSV rows, or write back to Givebutter.
- **Current Import Only**: Comparisons are strictly limited to records within the same `import_id`.
- **No Cross-Import Intelligence**: No cross-import matching, no prior import history, and no historical donor intelligence.
- **No v2 Identity Model**: No lifetime giving, no master person profiles, no global households, and no identity links.
- **No Automation**: No automatic merges, no automatic approvals, no auto-resolve, and no auto-link.
- **No Givebutter Writeback**: Decisions are stored locally in the audit/suggestion tables.

## Included Artifacts
- `duplicate-candidate-review-final.html`: HTML reference artifact.
- `duplicate-candidate-review-final-screenshot.png`: Visual source of truth.
- `duplicate-candidate-review-stitch-recreation-notes.md`: Detailed rebuilding guide for Stitch.
- `duplicate-candidate-review-manifest-entry.md`: Technical metadata and data mapping.

## Notes for Claude Code
- **Architecture**: Use the existing Flask/Jinja Givebutter Processor architecture. Do not create a React app.
- **Visual Baseline**: Stitch HTML/screenshots are visual targets and recovery artifacts; they are not frontend architecture requirements.
- **Logic Guard**: When conflicting evidence exists, require reviewer reasoning before enabling “Mark as Same Person.” The current finalized example is an address conflict.
- **Audit Logging**: Ensure every decision — Same Person, Different, or Defer — logs the operator ID, timestamp, decision type, candidate ID, and reviewer notes when provided or required.
- **Data Source**: Pull real candidate data from `duplicate_candidates`, contact info from `contacts`, and donation context from records associated with the same current `import_id`.
- **Fidelity**: Maintain the side-by-side card layout, supporting/conflicting evidence panels, required-reasoning behavior, and persistent right-side details drawer. Do not condense the comparison view without product review.
