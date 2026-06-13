# Householder v1.1 Folder Semantics & Organization

**Version:** 1.1  
**Status:** Operational Guidance  
**Date:** 2026-06-13  
**Purpose:** Define folder structure and semantics for v1.1 operators

---

## Executive Summary

Householder v1.1 uses a structured folder hierarchy for managing incoming source files, human review state, archived/failed intakes, and generated export artifacts. This document clarifies the semantic meaning of each folder to prevent confusion between source-file review status and generated export output.

**Key principle:**
- `review/approved` = human-approved source/review files
- `exports/` = generated app export artifacts (configured separately)
- These are NOT the same folder.

---

## Folder Taxonomy Overview

| Folder Category | Purpose | Operator-Managed | Auto-Managed |
|-----------------|---------|-----------------|--------------|
| **intake/** | Incoming source CSVs | ✓ Mostly | (Config only) |
| **review/** | Human review state | ✓ Yes | (State only) |
| **exports/** | Generated export artifacts | ✓ Config | ✓ App creates |

---

## Intake Folders (Incoming Source Files)

### `intake/new`
**Purpose:** Newly arrived source CSVs waiting for processing/review

**Contents:**
- Raw CSV files uploaded by operators
- Files not yet imported or queued for import

**Operator responsibility:**
- Upload new source CSVs here
- Decide when to process files
- Move processed files to archive or failed

**Application responsibility:**
- Read files from intake/new
- Validate and ingest CSVs

**Lifecycle:**
```
intake/new → [processing] → intake/archive OR intake/failed
```

---

### `intake/archive`
**Purpose:** Archived source CSVs after successful intake/review handling

**Contents:**
- Source CSVs that were successfully processed and reviewed
- Older CSVs kept for audit trail or historical reference

**Operator responsibility:**
- Manually move processed CSVs here (operator-managed)
- Define archive retention policy
- Include in backup strategy

**Application responsibility:**
- Does NOT automatically archive files

**Notes:**
- Operator decides when to archive
- Common practice: Archive after human review is complete
- Include in backup/retention policy

---

### `intake/failed`
**Purpose:** Source CSVs that failed intake/processing and require operator attention

**Contents:**
- Files that could not be imported (format error, corruption, etc.)
- Files with ingestion/processing errors

**Operator responsibility:**
- Review failed files
- Determine root cause (bad data, wrong format, etc.)
- Decide whether to:
  - Fix and reprocess
  - Archive as rejected
  - Delete if invalid

**Application responsibility:**
- Places failed files here when processing fails

**Notes:**
- Requires operator investigation and action
- Should be monitored regularly
- Monitor logs for error messages explaining why file failed

---

## Review Folders (Human Review State)

These folders represent the review/decision state for source files during the Householder review workflow.

### `review/processing`
**Purpose:** Source/review files currently being reviewed or processed

**Contents:**
- Files in active review workflow
- Files being evaluated by human reviewers

**Operator responsibility:**
- Monitor for progress
- Understand which reviewers are working on which files

**Application responsibility:**
- Manages this folder state during review workflow

---

### `review/flagged`
**Purpose:** Source/review files with an identified internal data/file issue that blocks approval

**Use flagged when the problem is VISIBLE IN THE FILE:**

Examples of issues visible in the file itself:
- Bad or suspicious donor data (invalid emails, phone numbers)
- Unexpected columns or schema mismatch
- Missing required fields
- Duplicate-heavy file (many exact duplicates)
- Format mismatch (wrong delimiter, encoding)
- Wrong file type (not actually a CSV)
- Large number of validation failures
- Privacy/security concern visible in data

**Operator responsibility:**
- Investigate data issue
- Determine if file should be rejected or if data quality rules need adjustment
- Decide whether to request corrected file or reject

**Application responsibility:**
- Flags files based on data validation rules

**Examples:**
```
CSV has 500 validation failures → review/flagged
CSV has wrong column names → review/flagged
CSV contains suspicious data patterns → review/flagged
CSV file is corrupted or malformed → review/flagged
```

---

### `review/followup`
**Purpose:** Source/review files that are not necessarily wrong, but need external clarification, approval, or action before a reviewer can decide

**Use followup when the blocker is MISSING CONTEXT or MISSING APPROVAL:**

Examples of issues requiring external follow-up:
- Need to ask fundraiser what the file represents
- Need donor team to confirm campaign/source/purpose
- Need source system owner to resend or explain file
- Need clarification on what a column means or represents
- Need approval from another person before proceeding
- Need missing context from data owner before deciding
- Unclear whether this is the final/correct file from the source

**Operator responsibility:**
- Reach out to appropriate person/team
- Get clarification or approval
- Move file to approved/flagged once decision is made

**Application responsibility:**
- Does NOT flag automatically (operator decision)

**Examples:**
```
Not sure whether this is the final CSV from the fundraiser → review/followup
Need campaign owner to confirm purpose/source of file → review/followup
Need ops person to explain which column maps to CRM field → review/followup
Unclear if file includes the latest donations → review/followup
```

---

### `review/rejected`
**Purpose:** Source/review files the human reviewer decided should not proceed

**Contents:**
- Files rejected during human review
- Marked as rejected by operator/reviewer decision

**Operator responsibility:**
- Files end up here when rejected
- Archive if needed for audit trail
- Monitor for patterns of rejection

**Application responsibility:**
- Moves files here when reviewer marks as rejected

**Notes:**
- Rejected files are archived for audit trail
- Can be re-reviewed if circumstances change

---

### `review/approved`
**Purpose:** Source/review files the human reviewer reviewed and approved to proceed

**Contents:**
- Source/review files approved by human reviewer
- Files ready to move to the next stage

**Operator responsibility:**
- Monitor progress
- Ensure approved files are exported if needed
- Archive completed source files

**Application responsibility:**
- Moves files here when reviewer approves

**⚠️ CRITICAL:** `review/approved` is for **source/review files**, NOT for generated export output.

---

## ⚠️ CRITICAL DISTINCTION: `review/approved` vs `exports/`

### `review/approved`

**What it is:** Human-approved **source/review files**  
**Semantics:** "A source CSV that a reviewer has reviewed and approved"  
**Contents:** The original source CSV files  
**Lifecycle:** Source → Review → Approved → Archive

**Example:**
```
File: donation_batch_may_2026.csv
Review state: approved (human reviewed and said "yes, proceed")
Status: Source file approved by human
```

---

### `exports/`

**What it is:** **Generated Householder export artifacts** from the v1.1 workflow  
**Semantics:** "A CSV export generated by Householder for manual CRM import"  
**Contents:** Generated CSV files created by the app  
**Lifecycle:** Generated → Downloaded → Uploaded to CRM

**Example:**
```
File: export_householder_batch_001_20260613.csv
Contents: Householder-generated CSV with normalized, deduplicated, grouped records
Status: Generated artifact, ready for manual CRM upload
```

---

## Decision Rule for Flagged vs Followup

### The Rule

```
If the issue is VISIBLE IN THE FILE ITSELF → review/flagged
If the blocker is MISSING CONTEXT, MISSING APPROVAL, or needs external response → review/followup
```

### Decision Examples

| Scenario | Folder | Why |
|----------|--------|-----|
| CSV has invalid/malformed rows | `flagged` | Issue visible in file data |
| Not sure whether this is the final CSV | `followup` | Missing context (need confirmation) |
| Suspicious donor records or wrong file | `flagged` | Data issue visible in file |
| Need campaign owner to confirm purpose | `followup` | Missing approval/context |
| Wrong columns or schema mismatch | `flagged` | Issue visible in structure |
| Need ops person to explain column mapping | `followup` | Missing context (need clarification) |
| Large number of validation failures | `flagged` | Issues visible in validation results |
| Uncertain whether to include this batch | `followup` | Missing decision/approval |
| Format error or corruption | `flagged` | File issue visible |
| Need stakeholder sign-off before proceeding | `followup` | Missing approval |

---

## Complete Folder Structure Map

```
project_root/
│
├── intake/                          [Incoming source files]
│   ├── new/                         Newly uploaded CSVs
│   ├── archive/                     Processed CSVs (archived)
│   └── failed/                      Failed import CSVs
│
├── review/                          [Human review state]
│   ├── processing/                  Currently being reviewed
│   ├── flagged/                     Data issues found
│   ├── followup/                    Need external context/approval
│   ├── rejected/                    Rejected by reviewer
│   └── approved/                    ✓ Approved by reviewer
│
└── exports/                         [Generated export artifacts]
    └── [EXPORT_OUTPUT_DIR]          Householder-generated CSVs
```

---

## Operator Do's and Don'ts

### DO

- [x] **DO** move processed CSVs from `intake/new` to `intake/archive`
- [x] **DO** investigate `intake/failed` files and determine next action
- [x] **DO** use `review/flagged` when data issue is visible in the file
- [x] **DO** use `review/followup` when you need external context or approval
- [x] **DO** archive `review/approved` files after export is generated
- [x] **DO** include all folders in backup strategy
- [x] **DO** monitor `intake/failed` and `review/followup` regularly

### DO NOT

- [x] **DO NOT** use `review/approved` as the generated export output directory
- [x] **DO NOT** move files between folders unless explicitly instructed
- [x] **DO NOT** delete files without archiving first
- [x] **DO NOT** modify CSV file contents
- [x] **DO NOT** assume application automatically manages folder transitions
- [x] **DO NOT** confuse source review state with generated export artifacts

---

## Folder Management Responsibility

### Operator-Managed Folders

**intake/archive, intake/failed:**
- Operator decides when to move files
- Operator decides archive retention policy
- Operator investigates failed files
- Application does NOT auto-manage these

**review/flagged, review/followup, review/rejected:**
- Operator/reviewer uses these for decision tracking
- Operator reaches out for followup items
- Application may populate flagged/rejected based on decisions
- Operator manages the lifecycle

### Application-Managed State

**review/processing, review/approved:**
- Application updates state during workflow
- Application moves files based on reviewer decisions
- Operator should not manually modify these

### Export Artifacts

**exports/ (EXPORT_OUTPUT_DIR):**
- Application creates files here during export generation
- Operator configures the directory location
- Operator manages retention/cleanup/archiving
- Operator includes in backup strategy

---

## Generated Householder Export CSVs

### Must Use EXPORT_OUTPUT_DIR

All CSV exports generated by Householder v1.1 **MUST** be written to the directory configured in `EXPORT_OUTPUT_DIR` environment variable.

**DO NOT:**
- Write exports to `review/approved`
- Write exports to any review state folder
- Store exports in intake folders

**Why:**
- Maintains clear separation between source review state and generated artifacts
- Prevents confusion about what the file represents
- Allows separate backup/retention policies for exports vs source files
- Simplifies operator workflows

**Configure in next step:**
- Operator Task 2 will set `EXPORT_OUTPUT_DIR` environment variable
- Will point to a dedicated `exports/` directory or equivalent

---

## Statement of Authority

### These Folders Are Operator-Managed Unless Otherwise Specified

The following folders exist for operator use and decision-making:
- `intake/archive` — Operator decides what to archive
- `intake/failed` — Operator investigates and acts
- `review/flagged` — Operator uses for data issues
- `review/followup` — Operator uses for missing context/approval

**If application code explicitly uses any of these folders for automation, that will be documented in code comments and this document will be updated.**

As of v1.1 release date (2026-06-13), the application does not automatically use these folders for automated processing.

---

## Next Step

**Operator Task 2:** Configure `EXPORT_OUTPUT_DIR` environment variable

- Create dedicated `exports/` directory (or equivalent path)
- Set `EXPORT_OUTPUT_DIR` environment variable
- Verify application can write to the directory
- Include in backup strategy

---

## Quick Reference

| Need to... | Use folder | Action |
|-----------|-----------|--------|
| Upload new CSVs | `intake/new` | Place files here |
| Archive processed files | `intake/archive` | Move from intake/new |
| Investigate failed imports | `intake/failed` | Check error logs, decide action |
| Mark data issue visible in file | `review/flagged` | Files move here |
| Need external context/approval | `review/followup` | Reach out, get decision |
| See approved files | `review/approved` | Approved source files |
| Get generated export CSVs | `exports/` (EXPORT_OUTPUT_DIR) | Generated artifacts here |

---

## Version

**Householder v1.1**  
**Release Date:** 2026-06-13  
**Folder Semantics Documentation:** COMPLETE

