# Normalization Review Screen — Implementation Requirements

**Status:** Ready for app implementation  
**Date:** 2026-06-11  
**Design Source:** DonorTrust v1 audit-safe principles  
**Verification Method:** Playwright against app code (not Stitch)

---

## Overview

The Normalization Review screen is a human-in-the-loop interface for reviewing and approving suggested field normalizations before export. All design decisions prioritize audit safety, raw data preservation, and explicit reviewer control.

---

## UI Components & Copy Requirements

### 1. Top-Right Action Button

**Component:** Approve Selected Button

**States:**

**When no rows are selected (disabled):**
```
Approve Selected (0)
[Disabled state styling]
```

**When N rows are selected (enabled):**
```
Approve Selected (3)    // or whatever count N is
[Enabled state styling]
```

**Behavior:**
- Update button text and disabled state dynamically based on checkbox selection
- Use JavaScript/React event listeners to track selected rows
- Disabled state should be visually distinct (grayed out, cursor: not-allowed)
- Clicking when enabled should open the approval modal

**Why:** Prevents accidental bulk approvals; makes intent explicit

---

### 2. Safety Strip (Below Page Title)

**Component:** Prominent text banner

**Content:**
```
Human-in-loop · Raw rows preserved · Approved suggestions affect export staging only
```

**Styling:**
- Position: Below "Normalization Review" page title
- Styling: Compact, readable, prominent
- Visual hierarchy: Secondary prominence (not as bold as title, more bold than body text)

**Why:** Reinforces all three core audit-safe principles

---

### 3. Approval Modal (Hidden, Triggered by Button Click)

**Trigger:** Clicking "Approve Selected (N)" button

**Modal Layout:**

**Title:**
```
Approve selected pending suggestions?
```

**Body:**
```
Only selected pending suggestions will be approved. Raw import rows remain unchanged. These decisions are logged to the audit trail.
```

**Actions:**
```
[Cancel] [Approve Selected]
```

**Styling:**
- Modal overlay with backdrop blur
- Centered on screen
- Icon: Checkmark or verification icon
- Primary button: Blue (secondary or accent color)

**Behavior:**
- Cancel: Close modal without action
- Approve Selected: Process the approval and show toast

**Why:** 
- Clear confirmation prevents accidental approvals
- Explicit language about what "approval" means
- Audit trail reference present

---

### 4. Toast Notification (Success Message)

**Trigger:** After modal approval is processed

**Toast Layout:**

**Title:**
```
Normalization decisions recorded
```

**Body:**
```
Selected suggestions approved for export staging.
```

**Icon:** Checkmark (success state)

**Position:** Bottom right of screen, with slide-in animation

**Duration:** Auto-dismiss after 4-5 seconds

**Why:**
- "Recorded" language emphasizes audit trail
- "Decisions" → not automatic
- "Approved for staging" → not direct export or CRM write

---

### 5. Row-Level Actions (Table)

**Component:** Per-row action buttons in suggestions table

**Visible Actions (each row must show):**

1. **Approve button/icon**
   - Label or tooltip: "Approve suggestion"
   - Action: Mark this row as approved

2. **Reject button/icon**
   - Label or tooltip: "Reject suggestion"
   - Action: Mark this row as rejected

3. **Defer button/icon**
   - Label or tooltip: "Defer decision"
   - Action: Mark for later review

**Requirements:**
- NOT hover-only (always visible in normal state)
- Clearly clickable and labeled
- Positioned consistently in each row
- Icons + text labels preferred (accessibility)

**Why:** Transparent, accessible reviewer control; audit trail clarity

---

### 6. Status Badges (Per Row)

**Component:** Color-coded badges showing decision state

**Visible on every row:**

- "Pending" (gray) — Not yet reviewed
- "Approved" (green) — Marked for export
- "Rejected" (red) — Rejected from export
- "Deferred" (yellow/orange) — Pending later review

**Why:** Full transparency of review history

---

### 7. Donor History Drawer (If Present)

**Component:** Right-side drawer showing export history

**Drawer Content:**

**DO:**
- Use: "Export file generated"
- OR use: "Included in prior export package"

**DO NOT:**
- Use: "Exported to Master CRM" (implies writeback)
- Use: Any CRM-specific language

**Why:** Avoids implying direct Givebutter CRM integration

---

## Hard Constraints (Must Maintain)

✅ **No "Approve All" shortcut** — Only selected rows can be approved  
✅ **No raw data mutation** — Import rows remain unchanged  
✅ **No automatic cleaning** — Approvals are decisions, not automation  
✅ **No Givebutter writeback** — Language avoids CRM integration implications  
✅ **Audit trail logging** — All decisions logged (via backend)  
✅ **Human-in-the-loop** — Every change is explicit reviewer action  
✅ **Layout preservation** — No structural changes from DonorTrust v1 design  

---

## Implementation Checklist

### Button & Modal
- [ ] Top-right button shows "Approve Selected (0)" when no rows selected
- [ ] Top-right button shows "Approve Selected (N)" when rows selected
- [ ] Button is disabled when count is 0
- [ ] Clicking button opens modal
- [ ] Modal displays correct title and body
- [ ] Modal has Cancel and Approve Selected buttons
- [ ] Modal close triggers success toast

### Safety Strip
- [ ] Safety strip visible below page title
- [ ] Text says: "Human-in-loop · Raw rows preserved · Approved suggestions affect export staging only"

### Row Actions
- [ ] Each row has Approve, Reject, Defer buttons
- [ ] Actions are visible (not hover-only)
- [ ] Each action has label or tooltip
- [ ] Clicking each action triggers appropriate state change

### Status Badges
- [ ] Status badges show: Pending, Approved, Rejected, Deferred
- [ ] Badges update when actions are clicked
- [ ] Color coding is consistent and accessible

### Toast Notification
- [ ] Toast appears after approval
- [ ] Title: "Normalization decisions recorded"
- [ ] Body: "Selected suggestions approved for export staging."
- [ ] Toast auto-dismisses after ~5 seconds

### Drawer (if applicable)
- [ ] Drawer does NOT contain "Exported to Master CRM"
- [ ] Drawer contains "Export file generated" or "Included in prior export package"

### Language Verification
- [ ] No "Approve All" anywhere in the interface
- [ ] No "Bulk Approval" or "Bulk Normalization Applied"
- [ ] No "328 records queued" or hardcoded counts
- [ ] No language implying raw data mutation
- [ ] No language implying Givebutter CRM writeback

---

## Verification (Post-Implementation)

### Automated Verification (Playwright)

```bash
# Run Playwright against the app route
pytest tests/e2e/test_normalization_review_impl.py -v

# Key checks:
# 1. Button shows "Approve Selected (0)" on load
# 2. Safety strip text is present and correct
# 3. Row actions are visible (not hidden)
# 4. Modal title and body are correct
# 5. Toast title and body are correct
# 6. No unsafe strings present in page HTML
```

### Manual Verification

1. **Load the screen** — Check button state and safety strip
2. **Select rows** — Verify button text updates to "Approve Selected (N)"
3. **Click button** — Modal should appear with correct text
4. **Click Approve Selected in modal** — Toast should appear
5. **Check drawer** — Verify no "Exported to Master CRM"
6. **Click row actions** — Verify Approve, Reject, Defer all work

---

## DonorTrust v1 Design Language

Maintain consistency with the Import Dashboard and other DonorTrust screens:

- **Colors:** Use the established color palette (primary, secondary, success, warning, error)
- **Typography:** Headline, body, and caption text styles
- **Spacing:** Consistent padding and margins
- **Icons:** Use Material Symbols or the project's icon set
- **Interactions:** Tooltips, hover states, disabled states

---

## Notes

- **Stitch design reference:** See `iteration-003/` for visual design direction
- **Do not patch Stitch artifacts:** Implement in app code instead
- **Source of truth:** The app code + Playwright verification
- **Audit trail:** Backend must log all approval/reject/defer decisions

---

**Created:** 2026-06-11  
**Status:** Ready for implementation  
**No Stitch dependencies:** Implement directly in app
