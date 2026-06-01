# UX Guide - Givebutter Donation Processor

**Version:** 3.0 | **Last Updated:** June 1, 2026

---

## Overview

This guide documents the user experience design patterns, interaction workflows, accessibility features, and responsive design of the Givebutter Donation Processor web interface. This is a reference for operators, designers, and developers implementing UI changes.

---

## Design Principles

1. **Clarity over Complexity** — Users understand the state of their data and what action to take next
2. **Efficiency** — Keyboard shortcuts and bulk actions reduce time spent reviewing records
3. **Safety** — Clear decision states prevent accidental approvals; data persistence prevents loss of work
4. **Accessibility** — Full keyboard navigation and semantic HTML for screen readers
5. **Responsiveness** — Works on mobile (375px), tablet (768px), and desktop (1920px)

---

## Upload Flow

### Step 1: File Selection

**Pattern: Drag & Drop + File Browser**

```
┌─────────────────────────────────┐
│  Drop CSV here or click browse   │
│         [File Input Area]        │
└─────────────────────────────────┘
```

**Behavior:**
- `dragover` state: Border changes to blue (#0066cc), background becomes light blue (#f0f7ff)
- `drop` state: File immediately uploads, no additional button needed
- **Keyboard**: Tab to field, Space/Enter opens file browser
- **Screen reader**: Announced as "File drop zone. Use browse button or drag and drop to select CSV file"
- **Mobile**: Full-width on small screens, centered on large screens

**Accessibility Features:**
- Input field is keyboard accessible (hidden but focusable)
- Semantic labels
- Visual feedback on interaction (color, background change)

### Step 2: Upload Status Feedback

**Status Messages:**

| Type | Appearance | Message |
|------|-----------|---------|
| **Uploading** | Blue (#d1ecf1) | "Uploading myfile.csv..." |
| **Processing** | Blue (#d1ecf1) | "Processing X records..." |
| **Success** | Green (#d4edda) | "✓ File processed: 150 records, 5 warnings, 2 failures" |
| **Error** | Red (#f8d7da) | "✗ Error: Invalid CSV format. Check: headers, encoding, row count" |

**Feedback Principles:**
- Messages appear below file input
- Include specific details (record count, warning count, error type)
- Persist until user uploads another file or closes the section
- Left border accent (4px solid color) reinforces message type

---

## Review Workflow

### Record Review Interface

**Layout: Table with per-row decision cells**

```
┌─────────────────────────────────────────────────────┐
│ Record | Donor Name    | Email        | Decision    │
├─────────────────────────────────────────────────────┤
│   1    | John Smith    | john@gma...  │ [Dropdown]  │
│        │ Tier: WARNING │ Issues:      │ [Notes]     │
│        │ Email typo    │ Suggestion:  │ [Save]      │
└─────────────────────────────────────────────────────┘
```

### Tier Visual Indicators

**Three-tier system with color coding:**

| Tier | Color | Label | Meaning |
|------|-------|-------|---------|
| **PASS** | Green (#d4edda) | PASS | Record matches reference patterns, low risk |
| **WARNING** | Yellow (#fff3cd) | WARNING | Record has anomalies (typo, unusual format), review suggested |
| **FAIL** | Red (#f8d7da) | FAIL | Record violates rules (missing required field, invalid format), likely reject |

**Implementation:**
- Tier badge appears in first column after record number
- Background color indicates severity
- Label is always visible and readable
- Tier color also used in table row hover state (subtle background tint)

### Issues and Suggestions Display

**Two-part feedback system:**

```
Issues (Red text, #666):
  ❌ Email typo: gmai.com (did you mean gmail.com?)
  ❌ Phone: unusual format (ext. included)

Suggestions (Blue text, #0066cc):
  → Correct email to: john@gmail.com
  → Flag phone for followup: (555) 123-4567 x123
```

**Principles:**
- **Issues**: What's wrong with the data
- **Suggestions**: How to fix it (what the processor recommends)
- Font size: 12px (small but readable)
- Line height: 1.4 (readable for lists)
- Color coding helps distinguish meaning
- Multi-line issues render as bullet list

### Decision Workflow

**Three-option dropdown with notes field:**

```
Decision Dropdown:
  ○ Pending (Default)
  ○ Approved ✓
  ○ Follow-up ⚠
  ○ Rejected ✗

Notes Field (below dropdown):
  [Text area for operator commentary]
  "Approved - donor confirmed by phone"
```

**Interaction Pattern:**

1. **Open dropdown**: Click dropdown, see options
   - Default state: "Pending"
   - Options: Approved, Follow-up, Rejected
   - Keyboard: Tab to focus, arrow keys to navigate, Enter to select

2. **Select decision**: Click option
   - Dropdown updates immediately
   - Selection persists in local state

3. **Add notes** (optional): Click notes field, type comment
   - Textarea is full-width
   - Min height: 50px
   - Resizable (vertical only)
   - Keyboard: Tab navigates, no special handling needed

4. **Save record**: Click [Save] button
   - Button state: Enabled after dropdown selection
   - Button state: Disabled before selection (visual feedback to operator)
   - After save: Row background flashes briefly to indicate save success
   - Notes field clears (or persists, depending on workflow)

**Accessibility:**
- Dropdown is semantic `<select>` element
- Textarea is proper `<textarea>` element
- Labels associated with form controls
- Focus states visible (browser default)

---

## Bulk Actions

**Quick decision buttons for efficiency:**

```
┌──────────────────────────────────────┐
│ Bulk Actions:                         │
│ [Approve All] [Follow-up All] [Reject All] │
└──────────────────────────────────────┘
```

**Behavior:**
- Approve All: Sets all records to "Approved"
- Follow-up All: Sets all records to "Follow-up"
- Reject All: Sets all records to "Rejected"
- After bulk action: User can override individual records
- Undo: Not available (intentional — encourages deliberate review)

**Safety:**
- Buttons are visually distinct but not aggressive
- Bulk actions do NOT automatically save
- User must click final [Submit] to persist all decisions

---

## Submit Workflow

**Final decision point:**

```
┌─────────────────────────────────────┐
│ [Submit Decisions] [Cancel Review]   │
└─────────────────────────────────────┘
```

**Behavior:**
- **Submit Decisions**:
  - Sends all records with decisions to processor
  - Generates three output files (approved/followup/rejected)
  - Displays success message
  - File becomes unavailable in review queue (moves to archive)
  
- **Cancel Review**:
  - Returns to upload screen
  - Preserves file in processing queue
  - Allows resuming review later (multi-session support)

**Accessibility:**
- Buttons are semantic `<button>` elements
- Buttons have keyboard focus indication
- Buttons have hover states for mouse users

---

## Responsive Design

### Mobile (375px)

**Layout changes:**
- Table becomes single-column stacked layout
- Columns render as label/value pairs
- Decision dropdown is full-width
- Notes field is full-width
- Buttons stack vertically
- Font sizes remain readable (13px minimum for table data)

**Example:**
```
Record: 1
Donor Name: John Smith
Email: john@gmail.com
Tier: ⚠ WARNING
Issues: Email typo
Decision: [Dropdown - full width]
Notes: [Textarea - full width]
```

### Tablet (768px)

**Layout:**
- Table uses 2-3 columns that fit side-by-side
- Decision column wraps to next row if needed
- Buttons are inline, one per line if needed
- Font sizes: 13-14px (comfortable for touch)

### Desktop (1280px+)

**Layout:**
- Full table with all columns visible
- Horizontal scroll if needed
- Buttons inline in actions row
- Font sizes: 13-14px (optimal for reading)

**Viewport-Specific CSS:**
```
@media (max-width: 768px) {
  /* Mobile/tablet adjustments */
  .review-table { display: block; }
  .review-table tr { display: block; }
  .review-table td { display: block; width: 100%; }
}

@media (min-width: 1920px) {
  /* Large desktop: increase spacing */
  .review-table td { padding: 16px; }
}
```

---

## Validation Feedback

### Real-Time Validation (Upload)

**As file is processed, user sees:**

```
Status: Processing myfile.csv...
Progress: 150 of 150 records processed

Results Summary:
┌──────────────────┐
│ Total:     150   │
│ Passed:    143   │
│ Warnings:   5    │
│ Failed:     2    │
└──────────────────┘
```

**Progress indicators:**
- Count updates as processing happens
- Color-coded summary (green for pass, yellow for warning, red for fail)
- Operator can start reviewing while processing completes if batch is large

### Form Validation Feedback

**Decision dropdown validation:**
- Cannot submit without selecting decision
- If user tries to submit: Error message appears above submit button
  - "Please select a decision for all records"
  - Message disappears when decisions are completed
  - Color: Red (#dc3545) background with dark red text

---

## Keyboard Accessibility

### Navigation

| Key | Action |
|-----|--------|
| `Tab` | Move focus to next focusable element |
| `Shift+Tab` | Move focus to previous focusable element |
| `Enter` | Activate focused button or select dropdown option |
| `Space` | Toggle focused button or open dropdown |
| `↓` `↑` | Navigate dropdown options |
| `Escape` | Close dropdown (if open) |

### Shortcuts

| Shortcut | Action | Notes |
|----------|--------|-------|
| Tab through record | Focus decision dropdown | No special key needed |
| Arrow keys in dropdown | Select option | Standard HTML select behavior |
| Tab in notes | Move to next field | Textarea is single-focused control |

### Screen Reader Announcements

**Page structure:**
- Heading: "Givebutter Processor - Review & Decide"
- Subheading: "Review and approve records"

**Table announcements:**
- Column headers: "Record Number", "Donor Name", "Email", "Tier", "Issues", "Suggestions", "Decision"
- Row context: "Row 1 of 150. Donor John Smith. Tier WARNING"

**Form controls:**
- Dropdown: "Decision: Select Approved, Follow-up, or Rejected"
- Button: "Save record decision"
- Button: "Submit all decisions and generate output files"

---

## Decision Persistence

### Multi-Session Support

**User journey:**

1. **Session 1**: Upload file, review 50 records, save decisions
   - Decisions are saved to database
   - File status: "in progress"
   - User closes browser

2. **Session 2**: User returns next day
   - Clicks "Resume Review"
   - File reloads with previous decisions still present
   - Dropdown shows "Approved" (persisted from Session 1)
   - User continues reviewing remaining 100 records

3. **Session 3**: Final submission
   - All 150 records now have decisions
   - User clicks "Submit Decisions"
   - Output files generated and saved

**Implementation:**
- Decisions stored in CSV with two new columns: `Operator_Decision` and `Operator_Notes`
- When file is loaded for review, previous decisions are pre-populated
- Dropdown state reflects persisted value
- Notes field shows persisted comments

### Save Behavior

**Per-record save:**
- User selects decision and (optionally) adds note
- Clicks [Save] button for that row
- Row background flashes green briefly
- Decision persists immediately to database

**Batch save (via Submit):**
- User makes decisions on multiple records
- Clicks [Submit Decisions]
- All unsaved decisions are written to CSV
- Output files are generated
- File moves from "processing" to "archived"

---

## Error Handling & Edge Cases

### Missing Data Handling

**When required field is missing:**
- Tier: FAIL (red)
- Issue message: "Missing required field: email"
- Decision: Must be Rejected or Follow-up
- Operator cannot approve missing data

### Duplicate Detection

**When duplicate is detected:**
- Tier: WARNING (yellow) or FAIL (red) depending on type
- Issue message: "Duplicate: Email matches record #5"
- Suggestion: "Review for household grouping"
- Decision: Operator decides to approve (one per household) or reject (remove duplicate)

### File Upload Errors

**Invalid CSV format:**
```
Status: Error
Message: ✗ Invalid CSV format
Details: "Line 3 has 8 columns but expected 7. Check: headers match Givebutter export"
Action: [Re-upload]
```

**Encoding errors:**
```
Status: Error
Message: ✗ Encoding error (expected UTF-8)
Details: "Found non-UTF-8 characters at line 5. Save CSV as UTF-8 and re-upload"
Action: [Re-upload]
```

---

## Visual Design System

### Color Palette

| Element | Color | Usage |
|---------|-------|-------|
| **Primary** | #0066cc | Links, active states, highlights |
| **Success** | #28a745 | Approved, positive actions, PASS tier |
| **Warning** | #ffc107 or #fff3cd bg | Warnings, WARNING tier |
| **Danger** | #dc3545 | Errors, rejections, FAIL tier |
| **Neutral** | #6c757d | Secondary buttons, disabled states |
| **Background** | #f5f5f5 | Page background |
| **Card** | #ffffff | Content containers |
| **Text** | #333333 | Body text |
| **Subtle** | #999999 | Placeholder, helper text |

### Typography

| Element | Style | Size | Weight |
|---------|-------|------|--------|
| **Page Title** | Heading 1 | 24px | 700 (bold) |
| **Section Title** | Heading 2 | 18px | 600 (semibold) |
| **Subsection** | Heading 3 | 16px | 600 (semibold) |
| **Table Header** | Semantic TH | 13px | 600 (semibold) |
| **Table Data** | Semantic TD | 13px | 400 (normal) |
| **Help Text** | Semantic P | 12px | 400 (normal) |

### Spacing

| Scale | Size | Usage |
|-------|------|-------|
| **xs** | 4px | Internal padding in badges |
| **sm** | 8px | Gap between inline elements |
| **md** | 16px | Padding in cells, gap between rows |
| **lg** | 24px | Padding in cards, gap between sections |
| **xl** | 48px | Padding in large sections (upload zone) |

---

## Common UI Patterns

### Status Cards

Used to show file upload status, processing progress:

```css
.status {
  padding: 12px 16px;
  border-radius: 6px;
  border-left: 4px solid <color>;
  background: <light-color>;
  color: <dark-color>;
  font-size: 14px;
}
```

### Summary Grid

Used to show stats (total records, passed, warnings, failed):

```css
.summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
}
```

Creates responsive columns that wrap on small screens.

### Scrollable Table

For very large CSV files:

```css
.review-container {
  max-height: 70vh;
  overflow-y: auto;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
}
```

Header stays sticky while scrolling through records.

---

## Browser Support

| Browser | Minimum Version | Notes |
|---------|-----------------|-------|
| Chrome | 90+ | Full support |
| Firefox | 88+ | Full support |
| Safari | 14+ | Full support |
| Edge | 90+ | Full support |
| Mobile Safari | iOS 14+ | Touch-optimized |
| Chrome Mobile | Android 10+ | Touch-optimized |

**Features used:**
- CSS Grid (IE 11 fallback: flex layout)
- Sticky positioning (no IE 11 support)
- CSS custom properties (no IE 11 support)
- Flexbox (universal support)

---

## Testing UI Changes

### Visual Regression Testing

Test files include visual regression baselines at three viewports:
- Mobile: 375px width
- Tablet: 768px width
- Desktop: 1280px width, 1920px width

When modifying CSS or HTML:
1. Update the code
2. Run visual regression tests: `pytest tests/e2e/test_e2e_visual_regression.py -v`
3. Review generated screenshots in `tests/e2e/screenshots/`
4. If changes are intentional, update baseline images in `tests/e2e/baselines/`

### Form Interaction Testing

Test files include form interaction tests for:
- File upload (drag & drop, file browser)
- Decision dropdown (open, select, persist)
- Notes textarea (type, resize, keyboard)
- Submit button (click, disabled states)
- Bulk action buttons (approve all, reject all)

When modifying form behavior:
1. Run form tests: `pytest tests/e2e/test_e2e_form_input.py -v`
2. Check keyboard navigation works (Tab through all controls)
3. Check screen reader announcements (use browser accessibility inspector)

---

## Future UX Improvements

### Planned (v3.1)

- [ ] Keyboard shortcuts for decisions (e.g., `a` for approve, `r` for reject)
- [ ] Search/filter records by donor name or email
- [ ] Undo for bulk actions (Ctrl+Z)
- [ ] Dark mode toggle
- [ ] Export decisions as PDF report

### Feedback Loop

Operators: Share feature requests or UX pain points in the operator notes or email the support team.

---

## Questions & Support

**For UI issues:**
- Review.html resides in `scripts/uploader/templates/review.html`
- Styles are embedded in the `<style>` section
- For changes, edit template, then run visual regression tests

**For accessibility questions:**
- All form controls use semantic HTML (`<select>`, `<textarea>`, `<button>`)
- ARIA labels are implicit from label associations
- Screen reader testing: Use Safari + VoiceOver (Mac) or NVDA (Windows)

---

**Last Updated:** June 1, 2026  
**Version:** 3.0  
**Maintained By:** Nonprofit Toolkit Team
