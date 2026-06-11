# DonorTrust v1 — All Records / Validation Review Screen

## Design + Implementation Specification

**Status:** Specification created; Stitch generation pending
**Screen:** All Records / Validation Review
**Route:** `/imports/<import_id>/validation`
**Primary purpose:** Human review of all imported records in a batch; understand validation status; filter and navigate to details
**Design approach:** Desktop-first, high-density but readable, technical and audit-safe
**Visual style:** Consistent with DonorTrust v1 (white/light gray, subtle borders, compact table, clear badges)

---

## 1. Product Intent

The All Records / Validation Review screen allows a human reviewer to:

1. Inspect every imported record in a batch
2. Understand the validation status of each record (valid, needs review, issue)
3. Filter and triage records
4. Navigate to individual row details for deeper review
5. Select rows for batch workflow actions

This screen is **inspection and navigation only**. Raw import rows are never mutated from this view.

Core principle:

> The system validates. The reviewer inspects. Raw import rows remain unchanged.

---

## 2. v1 Safety Constraints

The screen must preserve:

* Raw import rows are immutable (no mutations from this screen)
* No automatic cleaning
* No automatic approval
* No Givebutter writeback
* No CRM writeback
* No automatic duplicate merging
* No householding decisions
* Every reviewer action is audit logged
* Selection-based workflow (no approve-all shortcuts)
* Validation status is informational only (does not auto-apply fixes)

---

## 3. Navigation & Layout

### Top Navigation Bar

Preserve DonorTrust navigation with "Review" active:

```
[DonorTrust logo] | Upload | Imports | Review | Matches | People | Households
```

Review tab is highlighted/active on this screen.

### Left Sidebar

**Title:** Data Controls  
**Subtitle:** Audit-Safe Filtering

**Controls:**
- Filters (by validation status, source, etc.)
- Sources
- Confidence
- Date Range
- Tags
- Assignment

**Queue Status Card** (near bottom of sidebar):

```
Queue Status

42%
1,204 records remaining in current import batch.
```

Display as visual progress indicator + text.

### Main Content Area

**Page Title:** All Records / Validation Review

**Metadata Line:**
```
Batch ID: #IMP-2023-0914-A | Source: Main_Donations_Q3.csv
```

**Safety Strip** (compact, below title):
```
Suggested changes only. Raw import rows are never changed.
```

---

## 4. Top-Right Actions

### Secondary Button

```
Export Warnings
```

Action: Download/generate a warnings report for the current batch.

### Primary Button (Selection-Aware)

**When zero eligible rows are selected:**
```
Review Selected (0)
```
State: Disabled, visually muted, not clickable

**When N eligible rows are selected:**
```
Review Selected (N)
```
State: Enabled, blue primary button

**Rules:**
- Do NOT use: "Approve All Validated", "Approve All", "Auto-apply", "Clean All"
- Button counts only eligible rows (typically: rows with "Issues" or "Needs Review" status)
- Do NOT enable bulk operations on "Valid" rows
- Clicking when enabled opens a review workflow modal

---

## 5. Main Table

### Table Structure

Bordered table with sticky header.

**Columns:**
1. Selection checkbox
2. Transaction ID
3. Date
4. Name
5. Email
6. Phone
7. Amount
8. Address
9. Validation Status
10. Action

### Example Data

| Checkbox | Transaction ID | Date | Name | Email | Phone | Amount | Address | Status | Action |
|----------|---|---|---|---|---|---|---|---|---|
| ☑ | TX-8829-X | 2023-09-12 | JONATHAN R. SMITH | jsmith@@gmail.con | (555) 012-3456 | $1,250.00 | 123 Maple St, Seattle | Issue | View |
| ☐ | TX-8830-Y | 2023-09-12 | Sarah Jenkins | s.jenkins@outlook.com | (555) 987-6543 | $50.00 | 456 Oak Ave, Portland | Valid | View |
| ☑ | TX-8831-Z | 2023-09-13 | Michael Chen | mchen@techcorp.io | 55512344 | $5,000.00 | 888 5th Ave, New York | Needs Review | View |
| ☐ | TX-8832-A | 2023-09-13 | Linda Thompson | l.thompson@charity.org | (212) 555-0982 | $25.00 | 10 Birch Ln, Austin | Valid | View |
| ☑ | TX-8833-B | 2023-09-14 | Robert Williams | rob.wills@provider.net | (312) 555-4433 | $0.00 | 99 Lake Dr, Chicago | Issue | View |

### Validation Status Badges

**Valid** (green badge + text)
```
✓ Valid
```

**Needs Review** (amber badge + text)
```
⚠ Needs Review
```

**Issue** (red badge + text)
```
✗ Issue
```

**Reviewed** (gray or blue badge + text)
```
✓ Reviewed
```

**Rule:** Do not rely on color alone. All badges must have text labels.

### Suspicious Field Highlighting

- **Invalid email:** Display in red or with error icon (e.g., `jsmith@@gmail.con`)
- **Invalid phone:** Display in amber or with warning icon (e.g., `55512344`)
- **Zero amount:** Display in red (e.g., `$0.00`)

These visual hints help reviewers spot problems at a glance.

### Row Actions

Each row has a "View Row" or "Review Issues" action button.

Preferred labels (safe, navigation-only):
- "View Row"
- "Review Issues"
- "Open Details"

**Do NOT include:**
- Direct raw-data editing controls
- Apply/approve buttons in the table row
- Auto-fix buttons

Clicking a row action navigates to the detailed row review screen (different route).

---

## 6. Sticky Footer

**Safety Message:**
```
Suggested changes only. Nothing is applied until a reviewer approves it. Raw import rows are never changed.
```

**Status Summary:**
```
Valid: 842 | Needs Review: 12 | Issues: 5
```

**Pagination:**
```
Page 1 of 42  [< Previous] [Next >]
```

Footer should be sticky (always visible at bottom as user scrolls).

---

## 7. Filtering & Navigation

The sidebar controls (Filters, Sources, Confidence, Date Range, Tags, Assignment) should filter the table in real time.

Common filter scenarios:
- Show only "Issue" rows
- Show only "Needs Review" rows
- Filter by source file
- Filter by date range
- Filter by confidence threshold

Selected filters should be visible (e.g., "Active filters: Status=Issue, Source=Main_Donations_Q3.csv").

---

## 8. Selection Model

**Row Selection:**
- Clicking the checkbox selects a row
- Header checkbox selects/deselects all visible rows on current page
- Selected rows are highlighted (light background or border)

**Button Update:**
- As rows are selected, "Review Selected (0)" updates to "Review Selected (N)"
- Button enabled/disabled state updates dynamically
- Button click opens a review workflow modal

**Selected Rows Behavior:**
- Selected rows persist across pagination (or user is warned if moving pages clears selection)
- Bulk actions apply only to explicitly selected rows

---

## 9. Workflow & Audit Events

### Review Selected Modal

When "Review Selected (N)" is clicked:

**Title:**
```
Review selected records?
```

**Body:**
```
You are about to review N selected records. This action is logged to the audit trail.
```

**Buttons:**
```
Cancel | Proceed with Review
```

### Audit Events

Each action should create an audit event:
- User ID
- Timestamp
- Batch ID
- Selected row IDs
- Action type (opened review, exported warnings, etc.)
- Status before/after

---

## 10. Data Model Expectations

The screen reads from:
- imports
- raw_import_rows
- validation_results
- audit_events

The screen should never overwrite or mutate `raw_import_rows`.

Validation results are calculated from the raw data (e.g., email format, phone format, amount > 0) and stored separately.

---

## 11. Acceptance Criteria

The screen is ready when:

### Visual
- [ ] DonorTrust navigation bar is present (Review active)
- [ ] Left sidebar with Data Controls is present
- [ ] Queue Status card shows progress indicator
- [ ] Page title and metadata line are present
- [ ] Safety strip is visible below title
- [ ] Export Warnings button is present (secondary)
- [ ] Review Selected button is present (primary, selection-aware)
- [ ] Main table displays 10+ example rows
- [ ] Validation status badges are visible (color + text label)
- [ ] Suspicious fields are highlighted (invalid email, phone, zero amount)
- [ ] Row action links are visible and labeled
- [ ] Sticky footer with safety message is present
- [ ] Status summary is visible in footer
- [ ] Pagination controls are present

### Safety
- [ ] No "Approve All" language anywhere
- [ ] No "Auto-apply" language
- [ ] No "Clean All" language
- [ ] "Review Selected (0)" button is disabled (not clickable)
- [ ] No raw-data editing controls in the table
- [ ] Safety strip is visible and accurate: "Suggested changes only. Raw import rows are never changed."
- [ ] Footer safety message matches spec

### Functional
- [ ] Row selection updates button text (0 → N)
- [ ] Button enabled/disabled state updates dynamically
- [ ] Filtering works (sidebar controls)
- [ ] Pagination works
- [ ] Row action navigates to detail screen
- [ ] Export Warnings generates/downloads file
- [ ] Table is readable at desktop width (1440px+)
- [ ] Status badges are color-coded + text-labeled (not color-only)
- [ ] Suspicious fields stand out visually

---

## 12. Visual Design Direction

Use the DonorTrust v1 style:

**Colors:**
- Background: White or very light gray (#F5F5F5)
- Borders: Subtle gray (#E0E0E0)
- Text: Dark gray or black (#333, #000)
- Badges: Green (#4CAF50), Amber (#FFC107), Red (#F44336), Gray (#9E9E9E)

**Typography:**
- Title: Large, bold (24px+)
- Body: Regular 14-16px
- Metadata: Small, muted gray (12-14px)

**Spacing:**
- Compact but readable
- High-density table (small padding)
- Clear whitespace around major sections

**Icons:**
- Checkmark (✓) for Valid
- Warning (⚠) for Needs Review
- Error (✗) for Issue
- Chevrons (< >) for pagination

**Accessibility:**
- High contrast (WCAG AA or better)
- Text labels on all badges (not color-only)
- Clear focus states for interactive elements

---

## 13. Stitch Generation Note

This design is generated in Stitch using the `variants()` or `generate_screen_from_text()` method.

**Verification Process:**
1. Stitch generates screen and returns edited screen ID
2. Fresh HTML is downloaded via `getHtml()`
3. Fresh screenshot is downloaded via `getImage()`
4. Downloaded artifacts are verified against this specification (section 11)
5. If artifacts match spec, design is approved
6. If artifacts are stale or regressed, pivot to implementation

**Do NOT:**
- Accept API success responses without verifying artifacts
- Manually patch the exported HTML
- Assume tool success means design is correct

---

## 14. Final Product Decision

The All Records / Validation Review screen design direction is accepted with the specifications above.

**Status:**
```
All Records / Validation Review — v1 Design Direction Ready for Generation
Specification Complete
```

**Next step:**
```
Generate design in Stitch when design phase begins.
Verify fresh artifacts match specification.
Archive visual artifacts as reference.
Implement from this specification when app development begins.
```

---

**Created:** 2026-06-11  
**Status:** ✅ Specification Complete | Ready for Stitch Generation
**Verification:** Fresh artifacts must match all acceptance criteria (section 11)
