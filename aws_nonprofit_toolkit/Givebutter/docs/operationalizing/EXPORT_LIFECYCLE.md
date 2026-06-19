# Export Artifact Lifecycle Guide

**Version:** 1.1  
**Status:** Current (no automatic cleanup policy)  
**Audience:** System operators, DevOps engineers, site reliability engineers

---

## Overview

This guide explains how Householder v1.1 manages generated export CSV files, audit records, and the lifecycle behavior operators should expect.

**Key principle:** Export files are local CSV artifacts stored on your server. Each export is independently tracked by an immutable audit record. No cleanup or archival policy is currently implemented.

---

## 1. Export File Location

### Environment Variable: EXPORT_OUTPUT_DIR

Export files are stored in a directory specified by the `EXPORT_OUTPUT_DIR` environment variable.

**Default:** `/tmp/givebutter/exports`

**Example configuration:**
```bash
# Set export directory (optional, uses default if not set)
export EXPORT_OUTPUT_DIR="/var/givebutter/exports"

# Verify configuration
echo $EXPORT_OUTPUT_DIR
# Output: /var/givebutter/exports
```

**Directory creation:**
- Directory is created automatically on first export if it doesn't exist
- Requires write permissions for the Flask application process
- If directory creation fails, export fails with a clear error message

**Directory permissions:**
- Should be writable by the Flask process user
- Example: `chmod 755 /var/givebutter/exports`
- Ensure sufficient disk space (see "Cleanup/Retention Policy" section)

---

## 2. Export Filename Behavior

### Filename Format

Generated export files follow this naming convention:

```
{sanitized_import_id}_export_{YYYYMMDD_HHMMSS}.csv
```

**Example:**
```
IMP-2025-0601-DONORS_export_20260619_143022.csv
IMP-DEMO-TEST_export_20260619_143023.csv
```

### Filename Sanitization

The import ID is sanitized before being used in the filename to prevent path traversal and invalid characters:

**Sanitization rules:**
- Path separators (`/`, `\`) are removed
- Leading dots (`.`) are removed
- Only alphanumeric characters, hyphens (`-`), underscores (`_`), and dots (`.`) are preserved
- Result: Safe, filesystem-friendly filename

**Example sanitization:**
```
Input:  "IMP-2025/../EVIL/TEST"
Output: "IMP-2025EVILTEST"      (separators removed)

Input:  "...IMP-TEST"
Output: "IMP-TEST"              (leading dots removed)

Input:  "IMP-TEST@2025"
Output: "IMP-TEST2025"          (@ symbol removed)
```

### Timestamp Precision

Timestamps are generated with **second-level precision** (`YYYYMMDD_HHMMSS`).

If two exports are generated in the same second for the same import, a collision suffix is applied (see "Collision Handling" below).

### Collision Handling

If a file with the same name already exists, a numeric suffix is appended before the `.csv` extension.

**Example collision sequence:**
```
First export:   IMP-TEST_export_20260619_143022.csv          (created)
Second export:  IMP-TEST_export_20260619_143022.csv          (collides, so...)
                IMP-TEST_export_20260619_143022_01.csv       (created instead)
Third export:   IMP-TEST_export_20260619_143022_02.csv       (created)
```

**Collision logic:**
- Tries suffixes `_01`, `_02`, ..., `_999`
- If all 999 suffixes are taken, export fails with an `ExportIOError`
- This is extremely rare (would require 1000 exports in same second)

---

## 3. Repeated Export Behavior

### Each Export Creates a Separate File

When you generate an export for the same import batch multiple times, each export creates a **separate file**, not an overwrite.

**Example scenario:**
```
Time 1: Generate export for batch "IMP-DONORS-001"
        → File created: IMP-DONORS-001_export_20260619_140000.csv

Time 2: Make more decisions, then generate export again
        → File created: IMP-DONORS-001_export_20260619_141500.csv
        (First file is NOT deleted or overwritten)

Time 3: Generate export a third time
        → File created: IMP-DONORS-001_export_20260619_143000.csv
```

**Result:** Three separate CSV files exist on disk, one per export.

### Why Multiple Exports?

Multiple exports of the same batch occur when:
1. **Initial export** — Generate export after completing all decisions
2. **Revised decisions** — Go back, change some decisions, export again
3. **Audit trail** — Want to export at different stages to track decision history
4. **Comparison** — Need before/after exports to understand change impact

All exports remain accessible for download independently.

### File Persistence

Once created, export files remain on disk indefinitely **until manually deleted** (see "Cleanup/Retention Policy").

---

## 4. Audit-to-File Linkage

### Audit Record for Each Export

Every time an export is generated, an **immutable audit record** is created in the database.

**Audit record contents:**
- `action_type`: `export_generated`
- `filename`: basename of CSV file (e.g., `IMP-DONORS-001_export_20260619_140000.csv`)
- `file_path`: absolute path to CSV file (e.g., `/var/givebutter/exports/IMP-DONORS-001_export_20260619_140000.csv`)
- `row_count`: number of rows in export
- `warning_count`: number of rows with warnings
- `blocked_count`: number of rows blocked from export
- `confirmations`: which deferred items were confirmed (validations, households, duplicates)
- `deferred_counts`: count of deferred items in export
- `timestamp`: when export was generated
- `actor`: who generated export (user/system identifier)

### Audit Record as Source of Truth

The audit record is the **durable record** that an export was generated. It stores:
- Exact filename and path
- Export metadata snapshot (row/warning/block counts)
- Who generated it and when
- Which decisions were confirmed

**Example audit record query (JSON-like representation):**
```json
{
  "id": 12345,
  "batch_id": "IMP-DONORS-001",
  "action_type": "export_generated",
  "action_timestamp": "2026-06-19T14:30:22Z",
  "actor": "alice@nonprofit.org",
  "details": {
    "filename": "IMP-DONORS-001_export_20260619_143022.csv",
    "file_path": "/var/givebutter/exports/IMP-DONORS-001_export_20260619_143022.csv",
    "row_count": 47,
    "warning_count": 3,
    "blocked_count": 0,
    "confirmations": {
      "confirmed_unresolved_validations": true,
      "confirmed_unresolved_households": false,
      "confirmed_unresolved_duplicates": false
    },
    "deferred_counts": {
      "deferred_validation_count": 2,
      "deferred_household_count": 0,
      "deferred_duplicate_count": 0
    }
  }
}
```

### Immutability

Once created, the audit record **cannot be changed or deleted**. This protects audit trail integrity even if the physical file is later removed from disk.

**Key guarantee:** Even if someone deletes the CSV file, the audit record remains as evidence that the export happened.

---

## 5. Download Behavior

### Download Workflow

When you click "Download" for an export, the following happens:

1. **Audit record lookup:** System finds the audit record by export ID
2. **Ownership verification:** Confirms audit record belongs to the requested import batch
3. **File validation:** Checks that the file path in the audit record is safe (within export directory, no path traversal)
4. **File existence check:** Verifies the file exists and is a regular file (not a directory)
5. **Stream download:** If all checks pass, file is streamed to your browser

### Missing or Deleted Files

If the CSV file has been deleted from disk:

**Download response:**
- HTTP status: `404 Not Found`
- Error message: "Export file not found"
- Log entry: Warning that file is missing

**What remains:**
- Audit record still exists in database
- Audit log still shows the export happened
- You can see the export metadata (row count, timestamp, actor) even though the file is gone

**Example scenario:**
```
Exported:         2026-06-19 14:30 — Export created, audit record saved
File deleted:     2026-06-20 09:00 — Someone deletes CSV file from disk
Download attempt: 2026-06-20 10:15 — User tries to download
Result:           404 Not Found, but audit record still visible showing what was exported
```

### Why Audit Persists When File is Deleted

The audit record serves as a **permanent record** that:
- An export was generated
- Who generated it and when
- What data was included (row/warning counts)
- What decisions were confirmed
- What file was created (name, path, size)

This record is preserved to maintain audit trail integrity, even if the actual file is deleted (intentionally or by accident).

---

## 6. Cleanup and Retention Policy

### Current Status: No Automatic Cleanup

**Important:** Householder v1.1 does **not** implement automatic cleanup, archival, or retention policies.

**What this means:**
- Export files remain on disk indefinitely
- Old exports are never automatically deleted
- Export directory size grows with each new export
- **Operator must monitor disk usage**

### Export Directory Growth

Export file size depends on:
- Number of records in batch
- Number of fields per record
- Text length per field

**Typical file sizes:**
```
Small batch (100 records):     ~50 KB
Medium batch (1000 records):   ~500 KB
Large batch (10000 records):   ~5 MB
```

**Example disk usage scenario:**
```
Week 1:  10 exports = ~500 KB
Week 2:  10 exports = ~1 MB total
Week 4:  30 exports = ~1.5 MB total
Month 1: 120 exports = ~6 MB total
Year 1:  1440 exports = ~72 MB total
```

### Disk Monitoring

Operators should:

1. **Monitor export directory size:**
   ```bash
   du -sh /var/givebutter/exports
   # Output: 145M    /var/givebutter/exports
   ```

2. **Check available disk space:**
   ```bash
   df -h /var/givebutter/exports
   ```

3. **Alert if space is low** (e.g., >90% full)

4. **Plan for growth** based on expected export frequency

### Manual Cleanup

Until an automatic retention policy is implemented, operators can **manually delete old export files**:

```bash
# List exports older than 30 days
find /var/givebutter/exports -name "*.csv" -mtime +30

# Delete exports older than 30 days (caution: irreversible)
find /var/givebutter/exports -name "*.csv" -mtime +30 -delete

# Or delete individual files
rm /var/givebutter/exports/IMP-OLD_export_20260501_140000.csv
```

**Warning:** Deleting a file removes the CSV only; the audit record remains.

### Future Policy: TBD

A retention/archival policy **has not yet been decided**. Options under consideration:

- **Archive to cold storage** — Move old files to S3/GCS after N days
- **Automatic deletion** — Delete files after N days (audit records remain)
- **Retention period** — Keep exports for 30/60/90 days, then archive/delete
- **No policy** — Keep indefinitely; operators manage cleanup

**Current guidance:**
- Plan for long-term disk growth
- Implement your own retention policy if needed
- Check back for future updates on automatic cleanup

---

## 7. Troubleshooting

### Problem: Download Returns 404

**Symptom:** Trying to download an export returns "Export file not found" (404).

**Possible causes:**
1. **File was deleted** — Export file no longer exists on disk
2. **File path is incorrect** — Rare; indicates data corruption
3. **Directory was moved** — Export directory path changed or disk was remounted
4. **Disk failure** — Physical disk containing export directory failed

**Resolution:**
- Check if file exists: `ls -la /var/givebutter/exports/*.csv`
- Check audit record to confirm export happened: Audit Log → filter by `export_generated`
- Regenerate export if needed: Go back to Export Console, re-generate CSV
- Check disk health: `df -h`, `dmesg | tail`

### Problem: Export Directory Growing Too Large

**Symptom:** Export directory `/var/givebutter/exports` uses excessive disk space.

**Resolution:**
1. **Identify large files:**
   ```bash
   ls -lhS /var/givebutter/exports | head -20
   ```

2. **Identify old exports:**
   ```bash
   ls -lt /var/givebutter/exports | head -20
   ```

3. **Delete old files (if safe to do so):**
   ```bash
   # Delete files older than 60 days
   find /var/givebutter/exports -name "*.csv" -mtime +60 -delete
   ```

4. **Check audit records still exist:**
   - Audit Log will show export happened even after file is deleted
   - This is normal and expected

### Problem: Multiple Exports Exist for Same Import

**Symptom:** Many CSV files exist for the same import batch (e.g., `IMP-DONORS-001_export_*`).

**Cause:** Repeated exports were generated (expected behavior).

**Example:**
```
IMP-DONORS-001_export_20260610_100000.csv
IMP-DONORS-001_export_20260612_140000.csv
IMP-DONORS-001_export_20260615_093000.csv
```

**Resolution:**
- This is normal; each file represents an export at a point in time
- Check audit log to see when each was generated and by whom
- Keep files that are needed; delete old ones if disk space is tight
- All files can be downloaded independently

### Problem: Collision Suffix Appears in Filename

**Symptom:** Export filename ends with `_01`, `_02`, etc.

**Example:**
```
IMP-TEST_export_20260619_143022.csv
IMP-TEST_export_20260619_143022_01.csv
```

**Cause:** Two exports were generated in the same second for the same import.

**Resolution:**
- This is rare but expected behavior
- Both files are valid and can be downloaded
- Audit records are separate for each file
- No action needed unless disk space is a concern

---

## 8. Related Documentation

**For reviewers:**
- [EXPORT_ONLY_WORKFLOW.md](../user-guide/EXPORT_ONLY_WORKFLOW.md) — How to generate and download exports
- [REVIEWER_WORKFLOW.md](../user-guide/REVIEWER_WORKFLOW.md) — How decisions affect exports

**For demo environment:**
- [DEMO_SETUP.md](../user-guide/DEMO_SETUP.md) — Setting up demo environment with custom export directory

**For developers:**
- `scripts/householder/export_file_service.py` — Export generation logic
- `scripts/householder/export_download_service.py` — Download validation and file retrieval
- `tests/integration/test_export_download_route.py` — Integration tests for lifecycle behavior
- `tests/unit/test_export_file_service.py` — Unit tests for filename/collision logic

---

## Summary

| Aspect | Behavior |
|--------|----------|
| **File location** | `EXPORT_OUTPUT_DIR` environment variable (default `/tmp/givebutter/exports`) |
| **Filename format** | `{sanitized_id}_export_{YYYYMMDD_HHMMSS}.csv` |
| **Repeated exports** | Separate files, separate audit records, no overwrites |
| **Collisions** | Suffix `_01`, `_02`, etc. if two exports in same second |
| **Audit record** | Immutable, persists even if file is deleted |
| **Download missing file** | Returns 404; audit record remains visible |
| **Cleanup policy** | None implemented; operators should monitor disk usage |
| **Future retention** | Policy TBD; options include archival, deletion after N days |

---

**Last updated:** 2026-06-19  
**Status:** Current (no retention policy implemented yet)
