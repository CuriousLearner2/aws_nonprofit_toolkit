# Duplicate Candidate Review Stitch Recreation Notes

## Screen Name
Possible Duplicate in This Import / Duplicate Candidate Review (v1)

## Status
✅ Design Finalized, Needs Packaging

## Overall Page Layout
- **Desktop First**: Optimized for 1440px+ width.
- **Main Area (Left)**: Side-by-side comparison cards and evidence panels, approximately 75–80% of the available width.
- **Details Drawer (Right)**: Persistent 400px wide Candidate Details panel.
- **Background**: Light surface color (`#f7f9fb`).

## Header and Nav
- **DonorTrust Header**: Standard platform navigation with Upload, Imports, Review, Exports, and Audit.
- **Page Title**: “Possible Duplicate in This Import”.
- **Match Headline**: “Jane A. Smith may be the same person as Jane Smith”, with names visually emphasized.

## Comparison Cards
- **Side-by-Side Layout**: Two identical vertical cards for Contact A and Contact B.
- **Card Sections**:
  - **Identity**: Header with card label, Contact A or Contact B, and full name.
  - **Contact Info**: Rows with icons for email, phone, and address.
  - **Donation Context**: “DONATION IN THIS IMPORT” section showing amount, date, and campaign.
- **Visuals**: White cards with subtle borders; use blue accents for headings, highlights, and active emphasis where shown in the final screenshot.

## Evidence Panels
- **Supporting Evidence**: Vertical list with green check-circle icons, such as exact email match, exact phone match, and similar name.
- **Conflicting Evidence**: Warning panel with orange warning icon, such as address differs.
- **Reviewer Reasoning**: Large textarea labeled “Reviewer Reasoning” with placeholder text.

## Button Groups
- **Primary Action**: “Mark as Same Person” blue button.
- **Constraint**: When conflicting evidence exists, reviewer reasoning is required before “Mark as Same Person” is enabled. The finalized example is an address conflict.
- **Secondary Actions**: “Mark as Different” and “Defer” outline buttons.
- **Safety Copy**: “No contact fields or raw CSV rows are changed in v1. Marking as Same Person records the reviewer’s decision only.”

## Drawer Structure
- **Sections**:
  - **Candidate Summary**: Displays status, such as Pending Review, and confidence score, such as 95%.
  - **Duplicate Evidence**: Checklist matching the main panel’s evidence.
  - **Import Context**: Shows source filename and upload date.

## Typography and Spacing
- **Font**: Inter for labels and copy; JetBrains Mono for IDs or tabular technical values.
- **Density**: Comfortable desktop padding with high contrast between labels and data values.
- **Hierarchy**: Page title, match headline, card headings, field labels, and evidence labels should remain visually distinct.

## Colors
- **Primary Blue**: `#0051d5`.
- **Surface**: `#f7f9fb`.
- **Navy**: `#0f172a`.
- **Pass / Supporting Evidence**: `#10B981`.
- **Warn / Conflicting Evidence**: `#F59E0B`.

## v1 Safety and Scope Notes
- Compare only Contact A and Contact B from the same uploaded CSV/import.
- Do not show master person profiles, lifetime giving, prior import history, global households, or identity links.
- Do not merge contacts, donation transactions, or raw CSV rows.
- Do not write decisions back to Givebutter.
- Mark as Same Person records a reviewer decision only.
