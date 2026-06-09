# Upload / Import Queue Screen — Manifest Entry

## Screen Identification

- **Name:** Upload Givebutter CSV / Current Import Queue
- **Scope:** v1 (Current Import Only)
- **Status:** ✅ Finalized
- **Route:** `/` (existing upload route) or `/imports/new`

## Artifacts

- **HTML Export:** `docs/ux/upload-screen/upload-screen-final.html`
- **Screenshot:** `docs/ux/upload-screen/upload-screen-final-screenshot.png`
- **Stitch Notes:** `docs/ux/upload-screen/upload-screen-stitch-reimport-notes.md`
- **Production Template:** `scripts/uploader/templates/review.html` (Jinja2/Flask)

## Screen Sections

### 1. DonorTrust Navigation
- Logo + nav tabs (Upload, Imports, Review, Exports, Audit)
- Sticky top, white background
- Right: Notifications, Settings, User Avatar

### 2. Safety Banner
- Message: "Suggested changes only. Nothing is applied until a reviewer approves it. Raw import rows are never changed."
- Styling: Blue left border, light gray background
- Purpose: Emphasize non-destructive review model

### 3. Upload Card (Grid Left)
- Drag-and-drop CSV upload
- "Select File" button
- Subtitle: "Givebutter CSV only"
- Note: "Upload creates a new import batch. Raw CSV rows are preserved unchanged."

### 4. v1 Safety Mode Panel (Grid Right)
- 7 safety checkpoints (all enabled for v1):
  - Current import review only
  - Givebutter CSV files only
  - Raw rows preserved unchanged
  - Suggestions generated as pending review
  - No automatic approvals
  - No merges on upload
  - No Givebutter writeback
- Live stats:
  - Active imports
  - Total pending review items
  - Last upload time

### 5. Current Import Queue Table

#### Columns (9 total)

| # | Column | Width | Type | Content |
|---|--------|-------|------|---------|
| 1 | Filename | 280px | Text | File icon + name (ellipsis, tooltip for full) |
| 2 | Uploaded | 100px | Time | Relative format (e.g., "just now") |
| 3 | Total Rows | 80px | Numeric | Row count, center-aligned |
| 4 | Validation | 120px | Badge | PASS (green), WARN (orange), FAIL (red) |
| 5 | Normalizations | 140px | Text | Summary (e.g., "0 pending") |
| 6 | Households | 120px | Text | Summary (e.g., "0 suggested") |
| 7 | Duplicates | 120px | Text | Summary (e.g., "0 candidates") |
| 8 | Status | 220px | Text | Full text: "Pending Review" / "In Review" / "Completed" |
| 9 | Action | 140px | Button | Status-dependent label (sticky right) |

#### Action Mapping

| Status | Button Label | Behavior |
|--------|--------------|----------|
| Pending Review | Review Import | Open duplicate candidate / all-records review |
| In Review | Continue Review | Resume review workflow |
| Completed | View Summary | Show import summary and export options |

#### Table Behavior
- **Scrolling:** Horizontal scroll if table exceeds viewport (min-width 1320px)
- **Sticky Column:** Action column remains visible when scrolled right
- **Hover:** Row background changes to light gray
- **Empty State:** "No imports yet. Upload a CSV to get started."
- **Footer:** "Showing [X] of [Y] active imports"

## Data Sources

### Backend Tables
- `imports` — Import records (id, filename, uploaded_at, row_count, status, etc.)
- `raw_import_rows` — Immutable original CSV rows (never modified)
- `contacts` — Extracted baseline contact records
- Validation results — Count of PASS / WARN / FAIL
- Suggestion tables — Normalizations, Households, Duplicates (all pending review)
- `Operator_Decision` (or equivalent) — Reviewer decisions (used to compute status)

### Required Data Flow
1. User uploads CSV → `imports` record created
2. CSV rows saved to `raw_import_rows` (immutable)
3. Baseline `contacts` extracted
4. Suggestions generated and marked as pending
5. Current Import Queue pulls from `imports` + aggregated suggestion counts
6. Status computed: 0 decisions = "Pending Review", all decisions made = "Completed", partial = "In Review"

### API Endpoints
- **GET `/api/processing`** — Returns list of active imports with aggregated stats
- **POST `/api/upload`** — Handle CSV file upload
- **GET `/api/imports/{id}/summary`** — (future) Import summary and export options

## User Actions

| Action | Trigger | Effect |
|--------|---------|--------|
| Upload CSV | Drag-drop or "Select File" click | Create import record, trigger validation, populate queue |
| Review Import | Click action button (Pending Review) | Navigate to duplicate candidate / all-records review |
| Continue Review | Click action button (In Review) | Resume review workflow at last decision point |
| View Summary | Click action button (Completed) | Display import summary, export options, audit trail |

## v1 Safety Constraints

✅ **Enabled:**
- Non-destructive suggestions only
- Raw import rows immutable
- All suggestions pending reviewer approval
- Audit trail for all decisions

❌ **Not in v1:**
- Cross-import matching
- Lifetime giving metrics
- Master people / global identity
- Global households
- Prior import history integration
- Identity links
- Automatic approvals
- Automatic merges
- Givebutter writeback

## Accessibility

- ✅ Semantic HTML (nav, main, section, table)
- ✅ ARIA labels where needed
- ✅ Color not sole differentiator (PASS/WARN/FAIL badges also use text)
- ✅ Keyboard navigation (buttons, links, form inputs)
- ✅ Sufficient contrast (WCAG AA minimum)
- ✅ Responsive design considerations (horizontal scroll for wide tables)

## Testing

- ✅ All 8 E2E tests passing (21-30 seconds)
- ✅ Unit tests for validation logic (integration tests)
- ✅ Manual screenshot verification at multiple viewports
- ✅ No JavaScript errors in console
- ✅ Performance: Page load < 2 seconds, table population < 1 second

## Implementation Notes

### Frontend
- **Framework:** Flask/Jinja2 (server-rendered HTML)
- **CSS:** Inline styles with CSS variables for theming
- **JavaScript:** Vanilla JS for file upload, table population, relative time formatting
- **Icons:** Material Symbols (Google Fonts)
- **Typography:** Inter font family

### Backend
- **Language:** Python (Flask)
- **Database:** SQLite (v1), upgrade path to PostgreSQL
- **ORM:** Raw SQL (parameterized) or lightweight wrapper (SQLAlchemy if needed, with approval)
- **Validation:** CSV parsing, data type checking, typo detection

### v1 Scope Note
The Upload screen is the **first user-facing screen**. It creates the import record and initiates the review workflow, but does NOT perform the review itself. Actual duplicate matching, normalization review, and household grouping are separate screens.

## Stitch Reimport

To recreate or reimport this screen in Stitch:
1. Use `upload-screen-final.html` as the visual reference
2. Refer to `upload-screen-stitch-reimport-notes.md` for detailed instructions
3. Preserve all 9 table columns exactly
4. Keep v1 safety messaging verbatim
5. Status and Action columns must be separate (not merged)
6. Status must show full text, Action must show button
7. Table must be scrollable, Action column sticky

See `upload-screen-stitch-reimport-notes.md` for full Stitch recreation guidance.

## Related Screens (v1 Roadmap)

- **Duplicate Candidate Review** — Side-by-side duplicate review (finalized design exists)
- **All Records Review** — Master list with pass/warning/fail status
- **Normalizations Review** — Typo and formatting fixes
- **Households Review** — Address-based grouping
- **Export Console** — Download options
- **Audit Log** — Decision history

## Sign-Off

✅ **Visual Design:** Finalized  
✅ **UX/IA:** Finalized  
✅ **Implementation:** Complete and tested  
✅ **Artifacts:** Packaged and documented  

Production deployment: Ready for v1 release.
