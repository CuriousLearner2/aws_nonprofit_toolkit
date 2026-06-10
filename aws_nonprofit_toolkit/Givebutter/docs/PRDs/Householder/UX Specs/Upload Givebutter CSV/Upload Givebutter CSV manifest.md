# Upload / Import Queue Screen — Manifest Entry

## Screen Identification
- **Name:** Upload Givebutter CSV / Current Import Queue
- **Scope:** v1 (Current Import Only)
- **Status:** ✅ Finalized + Implemented + Packaged
- **Route:** TODO: verify actual Flask route
- **Final Stitch URL:** https://web.application/stitch/projects/9371274764538076058/screens/0bf383c1ea6f4a82ac07778338e54ab7

## Artifact Paths
- **HTML Export**: `docs/ux/upload-screen/upload-screen-final.html`
- **Screenshot**: `docs/ux/upload-screen/upload-screen-final-screenshot.png`
- **Stitch Notes**: `docs/ux/upload-screen/upload-screen-stitch-recreation-notes.md`
- **README**: `docs/ux/upload-screen/README.md`

## Summary of Key Components
- **DonorTrust Navigation**: Persistent platform header.
- **Safety Banner**: Non-destructive processing disclaimer.
- **Upload Card**: Drag-and-drop handler for Givebutter CSV files.
- **v1 Safety Mode Panel**: 7-point guardrail checklist and live import stats.
- **Current Import Queue Table**: 9-column grid with separate Status (text) and Action (button) columns.

## Implementation Notes
- **Data Source**: This screen uses real backend data from `/api/processing`.
- **Logic**: Status text is derived from import processing state and pending review counts; Action buttons are contextual to status.
- **Immutability**: The upload flow writes to `raw_import_rows` as immutable JSON.
- **Claude Code Guidance**:
  - Use existing Flask/Jinja architecture.
  - Replace static prototype data with real backend data.
  - Use v1 PRD for logic/behavior.
  - Run tests after changes and summarize.

## v1 Exclusions / Forbidden Concepts
- NO cross-import matching.
- NO lifetime giving metrics or lifetime donor profiles.
- NO master people or global identity.
- NO global households.
- NO identity links.
- NO prior import history integration.
- NO Givebutter writeback.
- NO automatic merges or automatic approvals.
