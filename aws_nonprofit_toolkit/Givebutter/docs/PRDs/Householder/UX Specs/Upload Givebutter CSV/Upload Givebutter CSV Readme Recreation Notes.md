# Upload Screen Stitch Recreation Notes

## Screen Name
Upload Givebutter CSV / Current Import Queue (v1)

## Status
✅ Finalized v1 visual target

## Overall Page Layout
- **Desktop Optimization**: Designed for 1440px+ width.
- **Structure**: Vertical stack containing header, safety banner, bento grid (upload card + safety panel), and the import queue table.
- **Background**: Light surface color (`#f7f9fb`).

## Header/Nav Structure
- **Product Name**: "DonorTrust" (font-weight: 900, Inter).
- **Navigation Tabs**: Upload (active), Imports, Review, Exports, Audit.
- **Utilities**: Notifications, Settings, and Profile Avatar on the far right.
- **Styling**: Persistent/sticky top bar, white background, subtle bottom border.

## Cards and Panels
- **Upload Givebutter CSV Card**:
  - Central 2/3 width of the bento grid.
  - Features a cloud upload icon (blue `#0051d5`).
  - Verbatim Copy: "Upload Givebutter CSV", "Drag and drop your file here, or click to browse. Supported file type: Givebutter CSV only".
  - Button: "Select File" (Primary blue).
  - Note: "Upload creates a new import batch. Raw CSV rows are preserved unchanged."
- **v1 Safety Mode Panel**:
  - Right-side 1/3 width.
  - Background: Dark navy (`#131b2e`).
  - Seven checkpoints with green check-circle icons:
    1. Current import review only
    2. Givebutter CSV files only
    3. Raw rows preserved unchanged
    4. Suggestions generated as pending review
    5. No automatic approvals
    6. No merges on upload
    7. No Givebutter writeback
  - Live stats at the bottom: Active imports, Total pending review items, Last upload time.

## Table Structure and Columns
- **Current Import Queue Table**:
  - Exactly 9 columns: Filename, Uploaded, Total Rows, Validation, Normalizations, Households, Duplicates, Status, Action.
  - **Filename**: Single-line with ellipsis and file icon; full name in tooltip.
  - **Validation**: Color-coded badges for PASS (green), WARN (orange), FAIL (red).
  - **Numeric Data**: Uses monospace font (JetBrains Mono) for counts and timestamps.
  - **Status**: Plain text indicator (e.g., "Pending Review").
  - **Action**: Visible button (e.g., "Review Import").

## Spacing and Density
- **Typography**: Inter (Sans-serif) for general UI; JetBrains Mono for data IDs and counts.
- **Table Density**: High-density rows (approx 48-52px height).
- **Margins**: Standard page margins (24-32px).

## Colors and Visual States
- **Primary Blue**: `#0051d5`.
- **Navy**: `#0f172a` / `#131b2e`.
- **Pass/Warn/Fail**: `#10B981`, `#F59E0B`, `#EF4444`.
- **Row Hover**: Subtle background shift to light gray.

## Behavior and Constraints
- **Scroll Behavior**: Table supports horizontal scrolling for smaller desktop viewports (min-width 1320px).
- **Sticky Region**: The "Action" column must be sticky on the far right during horizontal scroll.
- **Action Mapping**:
  - Pending Review → "Review Import"
  - In Review → "Continue Review"
  - Completed → "View Summary"
- **Safety**: Disclaimer banner at the top must be prominent and verbatim.
