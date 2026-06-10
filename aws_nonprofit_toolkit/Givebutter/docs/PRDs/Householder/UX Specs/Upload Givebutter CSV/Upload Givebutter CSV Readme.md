# Upload / Import Queue — README

## Screen Purpose
Provide a safe, non-destructive entry point for uploading Givebutter CSV files and viewing active import batches awaiting review. It allows operators to see what is uploaded, what review work is pending, and where to start.

## Current Maturity/Status
✅ **Finalized + Implemented + Packaged**

## Final Visual Target
- **Stitch URL**: https://web.application/stitch/projects/9371274764538076058/screens/0bf383c1ea6f4a82ac07778338e54ab7

## Key UX Decisions
- **Safety Banner**: Immediate reassurance that raw data is unchanged.
- **v1 Safety Mode Panel**: Explicit checklist of enabled safety guardrails.
- **Separate Status/Action**: Decouples the state of the import from the interaction to advance it.
- **Sticky Action Column**: Ensures primary interactions are always accessible on data-dense tables.

## v1 Safety Constraints
- **Immutable Raw Data**: Raw rows are preserved unchanged in `raw_import_rows`.
- **Current Import Only**: No cross-import matching or historical intelligence.
- **Human-in-the-loop**: All changes are generated as pending suggestions.
- **V1 Exclusions**: No master people, no global households, no identity links, no automatic merges, no automatic approvals, no lifetime giving, and no Givebutter writeback.

## Included Artifacts
- `upload-screen-final.html`: HTML reference artifact.
- `upload-screen-final-screenshot.png`: Visual source of truth.
- `upload-screen-stitch-recreation-notes.md`: Layout and styling guide for Stitch recreation.
- `upload-screen-manifest-entry.md`: Technical metadata and backend mapping.

## Notes for Claude Code
- **Architecture**: Use the existing Flask/Jinja Givebutter Processor architecture.
- **No New Apps**: Do not create a new React app.
- **Source of Truth**: Use the v1 PRD as the source of truth for behavior, data model, safety, and tests.
- **Visual Target**: Use these UX artifacts as the visual source of truth.
- **Data Integration**: Pull from `/api/processing`. Replace static prototype data with real backend data.
- **Testing**: Run tests after changes. Summarize files changed, tests run, assumptions, and TODOs.
- **Fidelity**: Do not alter safety messaging or v1 guardrail checklists.

## What must not be changed without product review
- Safety banner text
- V1 safety mode checkpoints
- Table column order (9 columns)
- Separation of Status and Action columns
