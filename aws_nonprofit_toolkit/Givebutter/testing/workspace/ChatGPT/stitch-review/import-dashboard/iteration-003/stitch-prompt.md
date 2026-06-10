# Stitch Revision Prompt — Import Dashboard — Iteration 003

## Design Goal
Strengthen the Import Dashboard as a sharper, safer, more executive-quality read-only command center for a single Givebutter CSV import batch.

The dashboard should answer within 5 seconds:
1. What import am I reviewing?
2. Is the import safe/healthy?
3. What review work remains?
4. Where should I go next?
5. Is the system still human-in-the-loop and non-destructive?

## Constraints
- Dashboard must remain read-only.
- Do not add approve, merge, normalize, delete, export-execute, writeback, or auto-apply actions.
- Do not introduce cross-import matching, global identity, lifetime giving, or Givebutter writeback.
- Do not mutate raw imported data.
- The system suggests; the reviewer decides.
- Preserve DonorTrust design language: technical, trustworthy, audit-safe, high-density but readable.
- Keep layout desktop-first at 1440×1024.
- Use consistent card spacing, section headers, and alignment.

## Specific Changes

### 1. Strengthen the Top Summary Hierarchy
- Keep batch metadata (filename, Import ID, upload date) close to the page title.
- Make the human-in-the-loop safety badge prominent near the title, but not visually louder than the "Import Dashboard" title.
- Make "50 raw rows preserved" clearly visible as a trust/audit metric, not a secondary afterthought.

### 2. Make the Validation Breakdown More Scannable
- Present PASS / WARNING / FAIL as a compact health strip.
- Include both count and label (e.g., "45 PASS", "5 WARNING", "0 FAIL").
- Do not rely only on color; use clear text labels.
- Keep 0 FAIL visually reassuring but not overly celebratory.

### 3. Improve the Review Queue Cards
- The three queue cards should feel like the main work routing area.
- Each card should include:
  - Count (e.g., "12")
  - Queue name (e.g., "Pending Normalizations")
  - Short explanation of what will be reviewed there (e.g., "Proposed field-format suggestions only.")
  - Safe navigation CTA (see CTA labels below)
- Use safe CTA labels:
  - "Review Normalizations"
  - "Review Households"
  - "Review Duplicate Candidates"
- Do not use unsafe decision/action labels like: Fix, Merge, Approve, Clean, Auto-apply.

### 4. Clarify Read-Only Dashboard Behavior
- Add or preserve a small note near the queue cards stating: "Dashboard is read-only. Decisions happen in review screens."
- Ensure no dashboard control implies it performs a data-changing action.

### 5. Improve Recent Actions
- Keep 5 audit trail entries.
- Make them compact and readable.
- Each entry should show:
  - Action type (e.g., "Approved normalization")
  - Record/person context (e.g., "John Smith")
  - Reviewer/system context if available (e.g., "operator@example.com")
  - Timestamp or relative time (e.g., "2m ago")
- The section should feel like audit context, not a primary work queue.

### 6. Improve v1 Guardrails Panel
- Keep it visible.
- Make the guardrails concise and high-signal:
  - Raw rows preserved
  - No auto-apply
  - No Givebutter writeback
  - Reviewer decides
- Avoid making the panel too visually heavy or scary.

### 7. Refine Export Access
- Keep Export Console as navigation, not immediate export execution.
- Use safe CTA label: "Open Export Console"
- Add copy clarifying export happens after review completion / readiness checks.
- Avoid "Export Now" or any language implying immediate export action.

### 8. Visual Polish
- Maintain DonorTrust design language: technical, trustworthy, audit-safe, high-density but readable.
- Keep layout desktop-first at 1440×1024.
- Use consistent card spacing, section headers, and alignment.
- Avoid excessive decoration.
- Preserve the current design system unless necessary.

## Content to Preserve

**Do not remove or significantly alter:**
- DonorTrust top navigation
- Page title: "Import Dashboard"
- Batch metadata:
  - givebutler_donors_june.csv
  - Import ID IMP-2026-006
  - Uploaded Jun 8, 2026
- Safety badge: HUMAN-IN-LOOP · NO AUTO-APPLY
- Summary metrics:
  - 50 total contacts
  - 50 raw rows preserved
- Validation breakdown: 45 PASS, 5 WARNING, 0 FAIL
- Queue cards: 12 Pending Normalizations, 5 Pending Households, 3 Unreviewed Duplicates
- Recent Actions (5 audit trail entries)
- v1 Guardrails panel
- Export Access section with Export Console navigation

## Success Criteria

After revision, the dashboard should:
1. ✓ Remain read-only (no execution buttons).
2. ✓ Use only safe navigation language (Review X, Open Export Console, View Recent Activity).
3. ✓ Make all required content visible and scannable within 5 seconds.
4. ✓ Clearly separate summary, queue work, audit context, and export navigation.
5. ✓ Reinforce human-in-the-loop / non-destructive behavior through copy and visual design.
6. ✓ Maintain DonorTrust design language and desktop-first layout.
