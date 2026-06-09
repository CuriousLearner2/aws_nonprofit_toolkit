# Upload Screen Stitch Reimport / Recreation Notes

## Screen Name
Upload Givebutter CSV / Current Import Queue (v1)

## Status
✅ Finalized v1 visual target

## Purpose
Provide a safe, non-destructive entry point for Givebutter CSV imports. Users upload a CSV, see it added to the import queue, and initiate review workflows without any automatic data changes.

## Screen Sections

### 1. Top Navigation (DonorTrust Header)
- Logo: "DonorTrust"
- Navigation tabs: Upload (active), Imports, Review, Exports, Audit
- Right icons: Notifications, Settings, User Avatar
- Styling: White background, sticky/fixed top, 24px padding

### 2. Safety Banner
- Icon: Verified User (Material Symbols)
- Title: "Suggested changes only."
- Subtitle: "Nothing is applied until a reviewer approves it. Raw import rows are never changed."
- Styling: Light gray background (#f2f4f6), blue left border (4px, #0051d5), rounded corners
- Purpose: Reassure users that raw data is safe

### 3. Upload Givebutter CSV Card
- Icon: Upload File (Material Symbols, 40px, blue #0051d5)
- Title: "Upload Givebutter CSV"
- Subtitle: "Drag and drop your file here, or click to browse. Supported file type: **Givebutter CSV only**"
- Button: "Select File" (blue primary button)
- Note: "Upload creates a new import batch. Raw CSV rows are preserved unchanged."
- Behavior: Click or drag-drop to select CSV file
- Styling: White card, subtle grid pattern background, 12px border-radius

### 4. v1 Safety Mode Panel
- Title: "V1 SAFETY MODE" (uppercase, small font, muted)
- Checklist (7 items, green check circles):
  1. Current import review only
  2. Givebutter CSV files only
  3. Raw rows preserved unchanged
  4. Suggestions generated as pending review
  5. No automatic approvals
  6. No merges on upload
  7. No Givebutter writeback
- Live Stats Section:
  - Active imports: [number]
  - Total pending review items: [number]
  - Last upload: [relative time, e.g., "just now", "2m ago"]
- Styling: Dark background (#131b2e), text color white/off-white, rounded corners 12px, padding 32px

### 5. Current Import Queue Table
- Title: "Current Import Queue" with badge "V1 CURRENT IMPORT REVIEW"
- Scrollable: Horizontal scroll if needed (min-width 1320px)

#### Table Columns (9 columns)

| Column | Width | Content | Notes |
|--------|-------|---------|-------|
| Filename | 280px | File icon + filename text | Single line with ellipsis; full filename in title/tooltip |
| Uploaded | 100px | Relative time | e.g., "just now", "3m ago", "1h ago" |
| Total Rows | 80px | Numeric count | Center-aligned |
| Validation | 120px | Color badges | PASS (green), WARN (orange), FAIL (red); can stack vertically |
| Normalizations | 140px | Text summary | e.g., "0 pending", "2 suggested" |
| Households | 120px | Text summary | e.g., "0 suggested", "5 pending" |
| Duplicates | 120px | Text summary | e.g., "0 candidates", "3 potential" |
| Status | 220px | Plain text, full word | "Pending Review", "In Review", or "Completed" |
| Action | 140px | Button, sticky right | Button text based on status |

#### Table Styling
- Header: Light gray background, uppercase labels, small font (11px), no truncation
- Rows: Hover effect (light gray background)
- Font: 12px, sans-serif (Inter preferred)
- Padding: 12px 16px per cell
- Borders: Subtle gray bottom border on each row
- Sticky Action Column: Fixed right with background color matching row state

#### Status-to-Action Mapping

| Status | Button Label | Color | Intended Action |
|--------|--------------|-------|-----------------|
| Pending Review | Review Import | Blue (#0051d5) | Open the duplicate candidate or all-records review |
| In Review | Continue Review | Blue | Resume the review workflow |
| Completed | View Summary | Gray/secondary | Display import summary and export options |

#### Empty State
- Message: "No imports yet. Upload a CSV to get started."

#### Footer
- Count: "Showing [X] of [Y] active imports"

## Stitch/Recreation Instructions

If importing or recreating this screen in Stitch:

1. **Use `upload-screen-final.html` as the visual reference.**
   - Open in a browser to see the exact layout, colors, spacing, and typography.
   - Use the DOM structure and CSS variables as guidance.

2. **Preserve these sections in order:**
   - DonorTrust top nav (sticky, white background)
   - Safety banner (blue left border, light gray background)
   - Upload Givebutter CSV card (centered, with drag-drop icon and button)
   - v1 Safety Mode panel (dark background, 7 checkpoints + 3 stats)
   - Current Import Queue table (scrollable, 9 columns)

3. **Use the CSS color palette:**
   - Primary: #000000 (black text)
   - Secondary: #0051d5 (blue, buttons and highlights)
   - PASS: #10B981 (green validation badge)
   - WARN: #F59E0B (orange validation badge)
   - FAIL: #EF4444 (red validation badge)
   - Surface: #f7f9fb (light gray background)
   - Surface Container High: #e6e8ea (darker gray)
   - Border Subtle: #E2E8F0 (light gray borders)
   - Primary Container: #131b2e (dark background for safety panel)

4. **Important: Table column widths**
   - Do NOT compress columns to fit a fixed width.
   - Use horizontal scrolling (min-width 1320px) if needed.
   - Status column must display full text without truncation.
   - Filename can use ellipsis with tooltip for full name.
   - Action button must always remain visible (sticky right, if possible).

5. **v1 Safety Messaging (Non-negotiable)**
   - Keep the exact safety banner text.
   - Keep all 7 checklist items in v1 Safety Mode panel.
   - These reinforce that raw data is never modified until approved.

## Required Table Columns

1. **Filename** — CSV filename with icon
2. **Uploaded** — Relative timestamp (e.g., "just now", "2h ago")
3. **Total Rows** — Row count from CSV
4. **Validation** — Color-coded badge summary (PASS / WARN / FAIL counts)
5. **Normalizations** — Text summary of suggestions (e.g., "0 pending")
6. **Households** — Text summary (e.g., "0 suggested")
7. **Duplicates** — Text summary (e.g., "0 candidates")
8. **Status** — Full text status, no abbreviation: "Pending Review" / "In Review" / "Completed"
9. **Action** — Button with status-dependent label

## Required Action Mapping

- **Pending Review** → Review Import (opens duplicate/all-records review)
- **In Review** → Continue Review (resumes review workflow)
- **Completed** → View Summary (shows import summary and export options)

## v1 Safety Boundary

**Do not add:**
- Cross-import matching (v2 feature)
- Lifetime giving metrics (v2)
- Master people / global identity (v2)
- Global households (v2)
- Prior import history (v2)
- Identity links (v2)
- Givebutter writeback (out of scope)
- Automatic merges (forbidden by v1 safety model)
- Automatic approvals (forbidden by v1 safety model)

**Keep in mind:**
- This is the upload/queue screen only.
- The actual review workflows (duplicate review, household review, etc.) are separate screens.
- This screen shows the queue; it does not perform the review itself.

## Notes for Implementation

1. **Backend Behavior (Not Visible in This Screen)**
   - On upload: Create `imports` record, save immutable rows to `raw_import_rows`, extract baseline `contacts`, generate pending suggestions.
   - The Current Import Queue should pull from real import data (not hardcoded rows).
   - Status should be computed from the reviewer decisions count.

2. **Dynamic Data**
   - Filename: from `imports.filename`
   - Uploaded: from `imports.uploaded_at` (formatted as relative time)
   - Total Rows: from `raw_import_rows` count for this import
   - Validation: from validation result summary
   - Normalizations, Households, Duplicates: from suggestion counts
   - Status: computed from `Operator_Decision` or equivalent decision count
   - Action button: conditional based on status

3. **Stitch Limitations**
   - If Stitch cannot connect to the backend directly, populate the table with sample/placeholder data.
   - Use the `upload-screen-final.html` as the visual target.
   - In Stitch, you may hardcode 1-3 sample rows to show the table layout.

4. **Accessibility & Usability**
   - Filename truncation: Use title/tooltip for full filename.
   - Status column: Must always display full text (no abbreviation).
   - Action buttons: Must be large enough to click (6px 10px padding minimum).
   - Safety messaging: Keep prominent (blue banner, dark panel).

## Related Documentation

- **v1 PRD:** `docs/PRDs/Householder/Householder-PRD-v1-final.md`
- **Implementation Plan:** `docs/PRDs/Householder/Implementation Plan - Householder v1.md`
- **Production Template:** `scripts/uploader/templates/review.html` (Jinja2/Flask)
- **E2E Tests:** `tests/e2e/test_e2e_upload_workflow.py`
