# DonorTrust v1 — Households Review Screen

## Design + Implementation Specification

**Status:** Specification created (Stitch refinement pending)  
**Screen:** Households Review (Suggested Household Review)  
**Node ID:** 301d7906577449908563bb9a591b88f7  
**Primary purpose:** Human review of system-suggested households; confirm, defer, or reject each suggestion with audit logging  
**Design approach:** Desktop-first, audit-safe, reviewer-decision-explicit, consistent with DonorTrust v1  
**Visual style:** Consistent with DonorTrust v1 (white/light gray, subtle borders, clear card hierarchy, safe action patterns)

---

## 1. Core Principle

> The system suggests households. The reviewer confirms, defers, or rejects. Raw import rows are never changed.

**Core guarantee:** Suggested households affect **export staging only**. Raw import rows remain immutable. Every decision is logged to the audit trail.

---

## 2. v1 Safety Constraints

The screen must preserve:

* Raw import rows are immutable (no mutations from this screen)
* Household suggestions are system-generated, not reviewer-created
* No automatic household confirmation
* No CRM writeback from this view
* No automatic contact merging
* Every reviewer decision (confirm/defer/reject) is audit logged
* Explicit reviewer intent required (no approve-all shortcuts)
* Confidence levels are informational only
* Deferred households may be re-reviewed; rejected suggestions are logged but not enforced
* Import staging reflects confirmed households only

---

## 3. Navigation & Layout

### Top Navigation Bar

Preserve DonorTrust navigation with "Households" or "Review" active:

```
[DonorTrust logo] | Upload | Imports | Review | Matches | People | Households
```

### Left Sidebar

**Title:** Data Controls (or Batch Filters)  
**Subtitle:** Audit-Safe Filtering

**Controls:**
- Batch ID (context)
- Confidence threshold filter
- Status filter (Pending, Confirmed, Deferred, Rejected)
- Source file filter
- Date range

**Batch Status Card** (near bottom of sidebar):

```
Batch Status

Pending: 47
Confirmed: 23
Deferred: 8
Rejected: 2
```

Display as counts + optional progress indicator.

### Main Content Area

**Page Title:** Households Review

**Metadata Line:**
```
Batch ID: #IMP-2023-0914-A | Source: Main_Donations_Q3.csv | Confidence threshold: 95%+
```

**Safety Strip** (compact, below title):
```
Suggested changes only. Confirmed households affect export staging only. Raw import rows are never changed.
```

---

## 4. Card-Based Household Suggestion Display

### Card Structure

Each suggested household is displayed in a bordered card with:

1. **Header: Suggested Household Name**
   - Display the system-proposed household name
   - Show confidence score: "98% match" (numeric preferred)
   - Small badge or label: "Suggested Household"

2. **Proposed Members Section**
   - List the contacts proposed to belong to this household
   - Show key identifiers: name, email, phone (abbreviated/truncated as needed)
   - Mark current assignments (if applicable)
   - Example format:
     ```
     Proposed Members:
     • John Smith (john.smith@example.com)
     • Jane Smith (jane@example.com)
     • Michael Smith (555-867-5309)
     ```

3. **Evidence Section**
   - Display the system's reasoning for the suggestion
   - Show matching signals clearly:
     - ✓ Shared address: "123 Maple St, Seattle, WA"
     - ✓ Same last name: Smith
     - ✓ Shared phone: (555) 123-4567
     - ✓ Source file: Main_Donations_Q3.csv
   - If conflicting signals exist, display them transparently:
     - ⚠ Different email domains (personal vs work)
     - ⚠ Age of last contact differs (3 years vs 6 months)
   - Do NOT hide or minimize conflicts; let the reviewer decide

4. **Reviewer Decision Actions** (explicit, balanced)
   - Three buttons in a horizontal row (not a dominant full-width button):
     - **Confirm Household** (primary blue button)
     - **Defer** (secondary outlined button)
     - **Reject** (secondary outlined button)
   - Layout: Side-by-side, equal visual weight
   - Confirm may be slightly more prominent (primary color), but should not dominate
   - Each button should be ~100-120px wide with padding

5. **Scope Copy** (below decision buttons)
   ```
   Confirmed households affect export staging only. 
   Raw import rows will not be changed. 
   This decision is logged.
   ```
   Style: Small gray text, italic, subtle

---

## 5. Decision Modal Confirmation

### Confirm Household Modal

**Trigger:** User clicks "Confirm Household" button

**Modal Structure:**

**Title:**
```
Confirm suggested household?
```

**Body:**
```
These contacts will be marked as belonging to the suggested household for this import's export staging. 
Raw import rows will not be changed. 
This decision will be logged to the audit trail.
```

**Buttons:**
- **Cancel** (secondary, left)
- **Confirm Household** (primary blue, right)

**Behavior:**
- Modal is non-dismissive on background click (requires user action)
- Clicking Cancel closes modal without change
- Clicking Confirm Household:
  - Logs the decision to audit trail
  - Updates the card status to "Confirmed" (optional UI update)
  - May move card to "Confirmed" section below or stay in place
  - User can proceed to next suggestion

### Defer Modal (Optional)

**Trigger:** User clicks "Defer"

**Modal Structure:**

**Title:**
```
Defer household suggestion?
```

**Body:**
```
This suggestion will be marked as deferred. 
You can review it again later or at the end of this batch.
Raw import rows will not be changed. 
This decision will be logged.
```

**Buttons:**
- **Cancel** (secondary, left)
- **Defer** (secondary, right)

### Reject Modal (Optional)

**Trigger:** User clicks "Reject"

**Modal Structure:**

**Title:**
```
Reject household suggestion?
```

**Body:**
```
This suggestion will be marked as rejected. 
These contacts will not be grouped as a household in the export staging. 
Raw import rows will not be changed. 
This decision will be logged.
```

**Buttons:**
- **Cancel** (secondary, left)
- **Reject** (secondary, red or warning color, right)

---

## 6. Confidence & Evidence Standards

### Confidence Labels

**Rule:** Use numeric confidence consistently when available. Prefer "X% match" over vague terms.

**Examples:**
- "98% match" ✓ (numeric, clear)
- "High confidence" ✗ (vague)
- "95%+ similarity" ✓ (numeric, clear)

### Evidence Display

**Required:**
- Show all matching signals (address, name, phone, source, etc.)
- Quantify matches when possible (e.g., "3 of 4 signals match")
- Display conflicting signals transparently (not hidden)
- Explain the confidence calculation briefly

**Example evidence layout:**
```
Evidence:
✓ Shared address: 123 Maple St, Seattle, WA (exact match)
✓ Same last name: Smith
✓ Shared phone: (555) 123-4567
⚠ Email domain differs: personal vs work
⚠ Last contact: 3 months vs 1 year apart

Confidence: 92% match (3 of 4 primary signals)
```

---

## 7. Status & Workflow

### Suggestion States

1. **Pending** (initial)
   - Awaiting reviewer decision
   - Card displayed in main area

2. **Confirmed**
   - Reviewer clicked "Confirm Household"
   - Modal confirmed the decision
   - Audit logged
   - Optional: move to "Confirmed" section or mark with checkmark badge

3. **Deferred**
   - Reviewer chose to review later
   - Card may be moved to "Deferred" section or filtered
   - Can be re-opened for review

4. **Rejected**
   - Reviewer rejected the suggestion
   - Card may be moved to "Rejected" section or filtered
   - Audit logged with rejection reason

### Page Layout (Optional Sections)

If desired, organize cards by status:

```
[Pending Suggestions] (main review area)
  - Card 1 (pending)
  - Card 2 (pending)
  
[Confirmed Households] (collapsible section)
  - Card 3 (confirmed, read-only)
  - Card 4 (confirmed, read-only)

[Deferred Suggestions] (collapsible section)
  - Card 5 (deferred, can be re-opened)

[Rejected Suggestions] (collapsible section)
  - Card 6 (rejected, read-only)
```

Alternatively, show all pending, with status badges and filters.

---

## 8. Safety Messaging & Copy

### Safety Strip (Below Title)

```
Suggested changes only. Confirmed households affect export staging only. Raw import rows are never changed.
```

### Scope Copy (Below Decision Buttons)

```
Confirmed households affect export staging only. 
Raw import rows will not be changed. 
This decision is logged.
```

### Confirmation Modal Body

```
These contacts will be marked as belonging to the suggested household for this import's export staging. 
Raw import rows will not be changed. 
This decision will be logged to the audit trail.
```

### Forbidden Language

Do NOT use:

* "Auto-household" (suggests automation, not review)
* "Auto-merge" (suggests automatic action)
* "Merge" (implies raw data mutation)
* "Writeback" (implies CRM mutation)
* "Sync to CRM" (implies automatic CRM sync)
* "Apply All" (suggests bulk approval)
* "Approve All" (suggests bulk approval)
* "Create household" (reviewer is confirming, not creating)
* "Bulk confirm" (no shortcuts)

---

## 9. Sticky Footer (Optional)

If needed for batch-wide context:

```
Batch Progress: 47 pending | 23 confirmed | 8 deferred | 2 rejected
```

Or pagination controls if suggestions span multiple pages.

---

## 10. Navigation Pattern Check

### Desktop Web (Full Width)

- Top navigation bar (DonorTrust standard)
- Left sidebar (Data Controls / Batch Filters)
- Main content area (household suggestion cards)
- Right-aligned or below: optional footer

**Viewport:** 1440px desktop width assumed.

### If Tablet-Specific Review Mode

- Indicate clearly in page title: "Households Review (Tablet)"
- Top nav may collapse to hamburger menu
- Sidebar may collapse to bottom tab bar or modal drawer
- Cards may expand to full width or use two-column layout
- Explicitly state this is a variant if not full desktop experience

**Assume full desktop for this specification unless otherwise specified.**

---

## 11. Acceptance Criteria

The screen is ready when:

### Visual ✅
- [ ] DonorTrust navigation bar is present (Households or Review active)
- [ ] Left sidebar with Data Controls is present
- [ ] Batch Status card shows pending/confirmed/deferred/rejected counts
- [ ] Page title and metadata line are present
- [ ] Safety strip is visible below title: "Suggested changes only. Confirmed households affect export staging only..."
- [ ] Household suggestion cards are displayed with clear hierarchy
- [ ] Suggested household name is prominent
- [ ] Confidence score is displayed numerically ("98% match")
- [ ] Proposed members section is visible
- [ ] Evidence section shows all matching signals + conflicts
- [ ] Decision buttons are visible in a balanced row: Confirm, Defer, Reject
- [ ] Scope copy visible below decision buttons
- [ ] DonorTrust v1 styling is preserved (colors, typography, spacing)

### Safety ✅
- [ ] No "Auto-household" language
- [ ] No "Auto-merge" language
- [ ] No "Merge" language
- [ ] No "Writeback" language
- [ ] No "Sync to CRM" language
- [ ] No "Apply All" language
- [ ] No "Approve All" language
- [ ] Safety strip present and accurate: "Suggested changes only. Confirmed households affect export staging only. Raw import rows are never changed."
- [ ] Scope copy present: "Confirmed households affect export staging only. Raw import rows will not be changed. This decision is logged."
- [ ] No raw-data editing controls in cards
- [ ] Confirmation modal present with correct text
- [ ] Modal buttons are Cancel and Confirm Household (not OK/Submit)

### Functional ✅
- [ ] Clicking "Confirm Household" opens confirmation modal
- [ ] Modal Cancel button closes without change
- [ ] Modal Confirm Household button logs decision and updates status
- [ ] Clicking "Defer" opens defer modal or marks card as deferred
- [ ] Clicking "Reject" opens reject modal or marks card as rejected
- [ ] Decision is logged to audit trail
- [ ] Confidence score is numeric ("X% match")
- [ ] Evidence displays all matching signals (address, name, phone, source)
- [ ] Evidence displays conflicting signals transparently
- [ ] Sidebar filters (confidence, status, source) work correctly
- [ ] Navigation to next/previous suggestion works (if paginated)
- [ ] Card is readable and not cluttered

### Optional Enhancements ✅
- [ ] Confirmed households move to separate "Confirmed" section (or stay in place with status badge)
- [ ] Deferred suggestions are re-openable
- [ ] Batch progress footer shows real-time counts
- [ ] Color-coded status badges on cards (confirmed = green, deferred = amber, rejected = red)

---

## 12. Visual Design Direction

Use DonorTrust v1 style:

**Colors:**
- Background: White or very light gray (#F5F5F5)
- Borders: Subtle gray (#E0E0E0)
- Text: Dark gray or black (#333, #000)
- Primary action (Confirm): Blue (#0051D5)
- Secondary action (Defer, Reject): Gray outlined (#64748B)
- Success/Confirmed: Green (#10B981)
- Warning/Conflicting signal: Amber (#F59E0B)
- Error/Rejected: Red (#EF4444)

**Typography:**
- Title: Large, bold (24px+)
- Card header: Bold (18px)
- Body: Regular 14-16px
- Metadata: Small, muted gray (12-14px)

**Card Spacing:**
- Card padding: 16px-24px
- Margin between cards: 12px-16px
- Action button row: Horizontal, equal spacing

**Interactive Elements:**
- Buttons: Primary blue, secondary outlined, clear hover states
- Modals: Centered, semi-transparent background
- Evidence section: Organized list with icons or check/warning symbols

**Accessibility:**
- High contrast (WCAG AA or better)
- Buttons clearly labeled (not icon-only)
- Modal focus management (trap focus in modal)
- Keyboard navigation supported

---

## 13. Stitch Refinement Note

This design is intended for refinement in Stitch using the `variants()` method:

**Refinement Process:**
1. Create variant with this specification as prompt
2. Download fresh HTML and screenshots
3. Verify against acceptance criteria (section 11)
4. If all criteria pass, design is approved
5. If criteria fail, pivot to implementation or new variant

**Do NOT:**
- Accept API success responses without verifying artifacts
- Manually patch exported HTML
- Assume tool success means design is correct

---

## 14. Final Product Decision

The Households Review screen design direction is accepted with the specifications above.

**Status:**
```
Households Review — v1 Design Direction Ready for Refinement
Specification Complete
```

**Next step:**
```
Refine in Stitch using variants() method.
Verify fresh artifacts match specification.
Archive visual artifacts as reference.
Implement from this specification when app development begins.
```

---

**Created:** 2026-06-10  
**Status:** ✅ Specification Complete | Ready for Stitch Refinement  
**Verification:** Fresh artifacts must match all acceptance criteria (section 11)  
**Authority:** This specification + refined artifacts  
**Safety Level:** Audit-safe, reviewer-decision-explicit, raw-rows-immutable
