# DonorTrust v1 — Normalization Review Screen

## Design + Implementation Specification

**Status:** Design direction finalized; implementation pending
**Screen:** Normalization Review
**Route:** `/imports/<import_id>/normalizations`
**Primary purpose:** Human review of suggested field normalization changes for a single import batch
**Source design reference:** Stitch Normalization Review artifacts, iteration 003 / variant screen
**Important note:** Stitch artifacts are visual references only. Final behavior and copy are governed by this specification.

---

## 1. Product Intent

The Normalization Review screen allows a human reviewer to inspect, approve, reject, or defer proposed normalization suggestions for imported Givebutter contact data.

This screen is not an automatic cleaning tool. It is a human-in-the-loop review interface.

Core principle:

> The system suggests. The reviewer decides. Raw import rows remain unchanged.

Approved normalization decisions affect export staging only. They must not mutate raw imported rows, baseline source records, or Givebutter data.

---

## 2. v1 Safety Constraints

The screen must preserve the following v1 constraints:

* Raw import rows are immutable.
* No automatic cleaning.
* No automatic approval.
* No Givebutter writeback.
* No CRM writeback.
* No cross-import matching.
* No householding decisions.
* No duplicate merge decisions.
* Every reviewer decision is logged to the audit trail.
* Approval, rejection, and deferral apply only to normalization suggestions.
* Bulk actions apply only to explicitly selected pending suggestions.

---

## 3. Visual Design Direction

Use the current Stitch Normalization Review screen as the visual baseline:

* DonorTrust top navigation
* Left Data Controls sidebar
* Review breadcrumb
* Page title: **Normalization Review**
* Compact safety strip below title
* Export Report secondary action
* Suggestions table
* Pagination footer
* Optional right-side Donor History drawer
* Toast confirmation pattern
* Confirmation modal pattern

The design should remain:

* desktop-first
* dense but readable
* technical and trustworthy
* audit-safe
* visually consistent with the finalized Import Dashboard design

---

## 4. Required Header Area

### Breadcrumb

Display:

```text
Review > Normalizations
```

### Page Title

Display:

```text
Normalization Review
```

### Safety Strip

Display directly below the title:

```text
Human-in-loop · Raw rows preserved · Approved suggestions affect export staging only
```

Do not use:

```text
Approved normalizations affect export staging only
```

Reason: "suggestions" is more precise and reinforces that the source data is not being changed.

---

## 5. Top-Right Actions

### Export Report

Secondary action:

```text
Export Report
```

This action may generate or download a review report. It must not export data back to Givebutter or any CRM.

### Approve Selected Button

Primary action must be selection-aware.

When zero rows are selected:

```text
Approve Selected (0)
```

State:

* disabled
* visually muted
* not clickable

When N pending suggestions are selected:

```text
Approve Selected (N)
```

State:

* enabled
* primary blue button
* opens confirmation modal

Rules:

* Do not show a generic active **Approve Selected** button when no rows are selected.
* Do not use **Approve All**.
* Do not approve rejected, approved, or deferred rows through this bulk action.
* Bulk approval applies only to selected pending suggestions.

---

## 6. Data Controls Sidebar

Preserve the left sidebar with:

* Filters
* Sources
* Confidence
* Date Range
* Tags
* Assignment
* Review Progress card

Review Progress example:

```text
612 / 940 Normalized
```

The sidebar is for filtering and triage only. It must not perform approvals or data mutation.

---

## 7. Suggestions Table

The table must show normalization suggestions for the current import batch.

Required columns:

1. Selection checkbox
2. Contact Name
3. Field
4. Current Value
5. Suggested Value
6. Reason
7. Confidence
8. Status
9. Actions

### Contact Name

Show the contact or organization name.

Example:

```text
Jonathan Arbuckle
Miriam Vanderbilt
St. Jude Medical Group
Dr. Helena Troy
```

### Field

Use compact badges.

Examples:

```text
EMAIL
PHONE
ORG NAME
ADDRESS
```

### Current Value

Represents the raw or currently imported value.

Design treatment:

* monospace when useful
* muted or error-colored when suspicious
* must visually read as source data
* must not imply it has been changed

Examples:

```text
JArb_99@gmial.com
2125550198
ST JUDE MED GRP
123 Main Street
```

### Suggested Value

Represents the proposed normalized value.

Examples:

```text
jarbuckle99@gmail.com
+1 (212) 555-0198
St. Jude Medical Group
123 Main St
```

The suggested value must not imply automatic application.

### Reason

Short explanation of the suggested normalization.

Examples:

```text
Domain Typo
Formatting
Expansion
USPS Standard
```

### Confidence

Show percentage plus visual bar.

Examples:

```text
98%
100%
72%
95%
```

Do not rely on color alone. The percentage must be visible as text.

### Status

Every row must show a status badge.

Allowed statuses:

```text
Pending
Approved
Rejected
Deferred
```

Status badge semantics:

* Pending: suggestion awaits reviewer decision
* Approved: reviewer accepted suggestion for export staging
* Rejected: reviewer rejected suggestion
* Deferred: reviewer postponed decision

---

## 8. Row-Level Actions

Each row must provide reviewer actions:

```text
Approve
Reject
Defer
```

Preferred visible treatment:

* visible text labels with icons, or
* clearly accessible action menu with labels

Do not rely solely on hover-only icons for production implementation.

Tooltips or accessible labels:

```text
Approve suggestion
Reject suggestion
Defer decision
```

Action semantics:

* Approve: records an approval decision for that suggestion
* Reject: records a rejection decision for that suggestion
* Defer: records a deferral decision
* None of these actions mutate the raw imported row

---

## 9. Bulk Approval Modal

Triggered only when one or more pending suggestions are selected.

### Modal title

```text
Approve selected pending suggestions?
```

### Modal body

```text
Only selected pending suggestions will be approved. Raw import rows remain unchanged. These decisions are logged to the audit trail.
```

### Buttons

Secondary:

```text
Cancel
```

Primary:

```text
Approve Selected
```

Do not use:

```text
Confirm Bulk Approval
Approve All
Approve All (328)
```

---

## 10. Toast Confirmation

After successful approval of selected suggestions, show toast:

### Title

```text
Normalization decisions recorded
```

### Body

```text
Selected suggestions approved for export staging.
```

Do not use:

```text
Bulk Normalization Applied
328 records queued for next export
```

Reason: "Applied" and "queued" imply automation or mutation.

---

## 11. Donor History Drawer

The optional right-side drawer may open when selecting a row or viewing history.

It should show donor/reference history only.

Allowed language:

```text
Record Created
Field Normalization Approved
Export file generated
Included in prior export package
```

Do not use:

```text
Exported to Master CRM
```

Reason: v1 does not perform CRM/Givebutter writeback.

Drawer actions may include:

```text
View Full Donor Profile
```

This must be navigation only.

---

## 12. Pagination Footer

Show current page context.

Example:

```text
Showing 4 of 328 suggestions
```

Pagination controls:

```text
Previous
1
2
3
Next
```

Pagination must not reset selected rows silently without warning if selection spans pages. For v1, selected rows should either be page-local or clearly counted.

---

## 13. Implementation Behavior

### Selection model

* Row checkboxes select suggestions.
* Header checkbox selects all visible pending suggestions on the current page.
* Approved, rejected, or deferred rows should not be included in bulk approval.
* If selected rows include non-pending statuses, the modal should clarify that only pending rows will be approved.

### Bulk action state

* Button disabled at zero selected pending rows.
* Button enabled at one or more selected pending rows.
* Button count reflects selected pending rows.

Examples:

```text
Approve Selected (0)
Approve Selected (1)
Approve Selected (4)
```

### Audit events

Each reviewer decision should create an audit event with:

* import ID
* row/contact ID
* normalization suggestion ID
* decision type: approved / rejected / deferred
* reviewer identity
* timestamp
* old/current value
* suggested value
* reason/confidence metadata

---

## 14. Data Model Expectations

The screen likely reads from:

* imports
* raw_import_rows
* contacts
* normalization_suggestions
* normalization_decisions
* audit_events

The screen should never overwrite `raw_import_rows`.

Approved decisions should be represented as decision records, not direct edits to the raw data.

---

## 15. Acceptance Criteria

The screen is ready when all of the following are true:

### Visual

* DonorTrust navigation is present.
* Left Data Controls sidebar is present.
* Normalization Review title is present.
* Safety strip is present with exact approved copy.
* Suggestions table is readable at desktop width.
* Status badges are visible.
* Row actions are visible or clearly accessible.
* Pagination is present.

### Safety

* No "Approve All" language.
* No "Bulk Normalization Applied" language.
* No "Exported to Master CRM" language.
* No implication of Givebutter writeback.
* No implication of raw data mutation.
* Approve Selected is disabled when zero pending rows are selected.
* Modal confirms selected pending suggestions only.
* Toast says decisions were recorded, not applied.

### Functional

* Reviewer can approve, reject, or defer a suggestion.
* Reviewer can select pending suggestions and approve selected.
* Reviewer can filter suggestions.
* Reviewer can view review progress.
* Reviewer can export a report.
* Reviewer can inspect donor history.
* Every decision is audit logged.

---

## 16. Stitch Artifact Note

The current Stitch artifacts are useful for visual direction, but Stitch API refinement showed inconsistent persistence between reported edit operations and exported HTML.

Therefore:

* Do not treat Stitch API success reports as final.
* Do not treat stale exported HTML as definitive behavior.
* Do not continue refining this screen in Stitch unless a new product requirement is introduced.
* Implementation must follow this specification even if the Stitch artifact differs in minor copy or interaction details.

The implementation source of truth is this specification plus final approved screenshots, not Stitch edit logs.

---

## 17. Final Product Decision

The Normalization Review visual direction is accepted with the implementation requirements above.

Status:

```text
Normalization Review — v1 Design Direction Final
Implementation Spec Ready
```

Next step:

```text
Implement from this specification when app development begins.
```
