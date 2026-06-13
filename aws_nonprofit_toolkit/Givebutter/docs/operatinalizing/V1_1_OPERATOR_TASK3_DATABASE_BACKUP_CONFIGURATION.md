# Householder v1.1 — Operator Task 3: Database Backup Configuration

**Version:** 1.1  
**Status:** Backup Configuration Complete  
**Date:** 2026-06-13  
**Purpose:** Define and verify database backup strategy for Householder v1.1 operator deployment

---

## Executive Summary

The Householder v1.1 database uses SQLite for data persistence and review state management. A backup and restore strategy has been defined and tested. The database is immutable by design (raw data never mutated), with append-only audit logs for traceability.

---

## Database Configuration Summary

### Database Type

**SQLite** (embedded relational database, file-based)

**Rationale:**
- No separate database server required
- Simple backup (copy file)
- Portable and self-contained
- Appropriate for v1.1 export-only scope

### Active Database Location

**File path:**
```
/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/givebutter.db
```

**File size:** ~44 KB (contains schema and structure)

**Configuration source:**
- Default: `sqlite:///./givebutter.db` (relative path)
- Configurable via: `GIVEBUTTER_DATABASE_URL` environment variable
- Example URL format: `sqlite:////absolute/path/to/givebutter.db`

### Database Initialization

When application starts:
1. If `GIVEBUTTER_DATABASE_URL` is set, use that connection string
2. Otherwise, use default: `sqlite:///./givebutter.db` (creates in current directory if not exists)
3. All tables are created automatically if they don't exist (SQLAlchemy `create_all`)
4. No migrations required for v1.1 (schema is fixed)

---

## Database Schema

### Tables (8 tables, all created automatically)

| Table | Purpose | Immutability |
|-------|---------|--------------|
| `import_batches` | Batch metadata and status | Updated (status field) |
| `raw_import_rows` | Original CSV row data | Immutable (append-only) |
| `import_contacts` | Denormalized contact snapshot | Immutable (append-only) |
| `review_items` | Validation/normalization/duplicate/household suggestions | Immutable (append-only) |
| `review_item_subjects` | Polymorphic subject references for review items | Immutable (append-only) |
| `review_decisions` | Reviewer decisions on review items | Append-only |
| `audit_log` | Immutable record of all actions | Immutable (append-only) |
| `alembic_version` | Schema version tracking | Technical (not user data) |

### Current Data State

**Row counts (verified 2026-06-13):**
- import_batches: 0
- raw_import_rows: 0
- import_contacts: 0
- review_items: 0
- review_item_subjects: 0
- review_decisions: 0
- audit_log: 0
- alembic_version: 1

**Assessment:** Database has correct schema; data tables are empty (expected for initial deployment).

---

## Backup Directory Recommendation

**Recommended backup directory:**
```
/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/backups
```

**Status:** ✓ CREATED  
**Permissions:** `drwxr-xr-x` (755) — owner writable, not world-writable  
**Writability:** ✓ VERIFIED

---

## Backup Command

### Simple Backup Using SQLite

**Basic backup command:**
```bash
sqlite3 <active_database_file> ".backup '<backup_file_path>'"
```

### Production Backup Script

For local/development use:
```bash
DB_PATH="/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/givebutter.db"
BACKUP_DIR="/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/backups"

sqlite3 "$DB_PATH" ".backup '$BACKUP_DIR/householder-v1.1-$(date +%Y%m%d-%H%M%S).db'"
echo "Backup complete: $BACKUP_DIR/householder-v1.1-$(date +%Y%m%d-%H%M%S).db"
```

### Recommended Backup Schedule

- **Frequency:** Daily (or after each significant batch import)
- **Retention:** 30+ days of rolling backups
- **Example schedule:** Cron job at 11:59 PM UTC
  ```bash
  59 23 * * * /path/to/backup/script.sh
  ```

### Backup Naming Convention

Pattern:
```
householder-v1.1-<YYYYMMDD>-<HHMM>.db
```

Example:
```
householder-v1.1-20260613-2359.db
```

---

## Restore Test Procedure

### CRITICAL: Never Restore Over Active Database

**Always test restore to a temporary location first.**

### Step-by-Step Safe Restore Test

**1. Create or identify a backup file:**
```bash
BACKUP_FILE="/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/backups/householder-v1.1-20260613-135747.db"
```

**2. Create a temporary test location (NEVER use production path):**
```bash
TEMP_RESTORE="/tmp/householder-restore-test-$$.db"
```

**3. Restore the backup to the temporary location:**
```bash
sqlite3 "$BACKUP_FILE" ".backup '$TEMP_RESTORE'"
```

**4. Verify the restored database schema:**
```bash
sqlite3 "$TEMP_RESTORE" ".tables"
```

**Expected output (tables should exist):**
```
alembic_version     import_contacts       review_item_subjects
audit_log           raw_import_rows       review_items        
import_batches      review_decisions
```

**5. Verify data integrity (check row counts):**
```bash
sqlite3 "$TEMP_RESTORE" "SELECT COUNT(*) FROM import_batches;"
sqlite3 "$TEMP_RESTORE" "SELECT COUNT(*) FROM audit_log;"
```

**6. Optionally run a deeper verification:**
```bash
sqlite3 "$TEMP_RESTORE" << 'EOF'
SELECT 'import_batches', COUNT(*) FROM import_batches
UNION ALL
SELECT 'raw_import_rows', COUNT(*) FROM raw_import_rows
UNION ALL
SELECT 'audit_log', COUNT(*) FROM audit_log;
EOF
```

**7. Delete the temporary restore file:**
```bash
rm "$TEMP_RESTORE"
```

### What This Procedure Verifies

✓ Backup file is readable  
✓ Restored database has correct schema  
✓ All expected tables exist  
✓ Data can be queried from the restored database  
✓ No corruption during backup/restore process  
✓ Active database remains untouched

---

## Pre-Deployment Database Checklist

Before deploying v1.1 to production, operator must:

- [ ] **Database file exists and is readable**
  ```bash
  ls -l /Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/givebutter.db
  ```

- [ ] **Verify database schema is correct**
  ```bash
  sqlite3 /path/to/givebutter.db ".tables"
  # Should show: alembic_version, audit_log, import_batches, import_contacts, raw_import_rows, review_decisions, review_item_subjects, review_items
  ```

- [ ] **Verify database is not world-writable**
  ```bash
  ls -l /path/to/givebutter.db
  # Should NOT show: ---w---- or similar world-writable permissions
  ```

- [ ] **Backup directory exists and is writable**
  ```bash
  ls -ld /path/to/backups
  chmod 755 /path/to/backups  # If needed
  ```

- [ ] **Create a test backup**
  ```bash
  sqlite3 /path/to/givebutter.db ".backup '/path/to/backups/test-backup.db'"
  ls -lh /path/to/backups/test-backup.db
  ```

- [ ] **Test restore procedure**
  ```bash
  # Follow "Restore Test Procedure" section above
  ```

- [ ] **Document backup schedule and retention policy**
  - How often: daily / weekly / after each batch?
  - Where: local directory / separate server / cloud storage?
  - How long: 30 days / 90 days / indefinite?

- [ ] **Confirm database user credentials are NOT exposed**
  - SQLite uses file permissions (no credentials in code)
  - Verify `.env` or environment variables don't contain passwords
  - Verify production database path is not in code

- [ ] **Confirm GIVEBUTTER_DATABASE_URL is set correctly (if using non-default)**
  ```bash
  echo $GIVEBUTTER_DATABASE_URL
  # Should show the production database URL or be empty (uses default)
  ```

---

## Post-Deployment Monitoring Checklist

After deploying v1.1 to production, operator should:

### Daily (Week 1)

- [ ] **Check application is using correct database**
  ```bash
  # After running application
  ls -l /path/to/givebutter.db
  # File timestamp should be recent (shows app is writing)
  ```

- [ ] **Verify backup was created**
  ```bash
  ls -lt /path/to/backups/ | head -5
  # Most recent backup should have today's date
  ```

- [ ] **Spot-check database integrity**
  ```bash
  sqlite3 /path/to/givebutter.db "SELECT COUNT(*) FROM import_batches;"
  # Should show number of batches imported
  ```

- [ ] **Check for any database error messages in logs**
  ```bash
  grep -i "database\|sqlite\|sql" /path/to/application.log | grep -i error
  ```

### Weekly (Weeks 2-4)

- [ ] **Verify regular backups are being created**
  ```bash
  ls -lt /path/to/backups/ | head -10
  # Should show backups from last 7 days
  ```

- [ ] **Test restore procedure (at least once per week)**
  ```bash
  # Follow restore test procedure above
  ```

- [ ] **Monitor disk space**
  ```bash
  df -h /path/to/
  # Ensure sufficient space for database + backups
  ```

- [ ] **Archive old backups if needed**
  ```bash
  # Move backups older than 30 days to separate location
  find /path/to/backups -name "*.db" -mtime +30 -exec mv {} /archive/path \;
  ```

---

## Limitations and Assumptions

### SQLite Limitations

- **Single-user:** SQLite uses file-level locking; concurrent heavy writes can cause lock timeouts
- **Not suitable for:** High-volume multi-user concurrent writes
- **Suitable for:** v1.1 export-only workflow (review happens sequentially, not concurrently)

### v1.1 Database Assumptions

- **No migrations:** Schema is fixed for v1.1; no breaking schema changes
- **Immutable data:** Raw import rows and audit logs never modified (backup-friendly)
- **Single-file backup:** Entire database is one file; backup is simple file copy
- **No credentials:** SQLite uses filesystem permissions; no database passwords

### Backup Assumptions

- **File copy is safe:** SQLite `.backup` command ensures consistent snapshot
- **No live modification during backup:** Operating system file locking prevents corruption
- **Restore is tested:** All restore tests must happen before production use

---

## What Operator Owns

### Operator Responsible For

- **Backup scheduling:** When to run backups (daily / weekly / per-batch)
- **Backup retention:** How long to keep backups (30 days / 90 days / indefinite)
- **Backup storage:** Where to store backups (local / separate server / cloud)
- **Restore testing:** Periodically testing restore procedure
- **Disk space monitoring:** Ensuring sufficient space for database + backups
- **Documentation:** Recording backup schedule and procedures
- **Compliance:** Meeting any compliance requirements for backup retention

### Application Handles

- **Database creation:** Schema is created automatically on startup
- **Data immutability:** Raw data and audit logs are never modified
- **Audit trail:** All reviewer actions are logged automatically
- **Transaction safety:** Database operations use SQLite transactions

---

## Remaining Operator Actions

### Task 3 — Database Backup Configuration ✅ COMPLETE
- [x] Database configuration identified: SQLite at `givebutter.db`
- [x] Schema verified: 8 tables (7 data + 1 metadata)
- [x] Backup directory created: `/backups/`
- [x] Backup command documented: `sqlite3 ... .backup ...`
- [x] Restore test procedure documented and verified
- [x] Pre-deployment checklist created
- [x] Post-deployment monitoring checklist created

### Task 4 — HTTPS/Network Security (Next)
- [ ] Enable HTTPS for all connections
- [ ] Configure network access controls
- [ ] Verify no external API calls made
- [ ] Confirm export files not world-readable
- [ ] Verify database credentials not exposed

### Task 5 — Support Team Briefing (Parallel)
- [ ] Schedule stakeholder briefing
- [ ] Train support team on v1.1 features
- [ ] Review export-only model and known limitations
- [ ] Prepare FAQ and escalation procedures

### Task 6 — User Communication (Parallel)
- [ ] Prepare release announcement email
- [ ] Link documentation in announcement
- [ ] Provide support contact information

### Task 7 — Deployment Day Execution
- [ ] Run pre-deployment smoke tests
- [ ] Execute deployment procedure
- [ ] Run post-deployment verification
- [ ] Go/no-go decision

### Task 8 — Post-Deployment Monitoring
- [ ] Week 1: Daily monitoring
- [ ] Weeks 2-4: Regular monitoring
- [ ] Week 4: Compile feedback for v1.2 roadmap

---

## 15 Hard Guardrails Confirmed

All guardrails remain in place and enforced:

✓ **No CRM/Givebutter API calls**  
✓ **No credentials storage** (SQLite uses file permissions)  
✓ **No writeback routes**  
✓ **No auth/RBAC changes**  
✓ **No bulk actions**  
✓ **No background jobs**  
✓ **No new export formats**  
✓ **No source-data mutations** (append-only design)  
✓ **No contact mutations** (append-only design)  
✓ **No contact merge**  
✓ **No contact deletion**  
✓ **No household_id assignment**  
✓ **No schema changes**  
✓ **No cross-import matching**  
✓ **No master contacts/households**  

---

## Sign-Off

**Task 3 Completion: VERIFIED**

- [x] Database configuration identified: SQLite in `givebutter.db`
- [x] Database path documented: Full path to file
- [x] Database URL configuration documented: `GIVEBUTTER_DATABASE_URL` environment variable
- [x] Schema verified: 8 tables (all expected tables present)
- [x] Backup directory created and verified writable: `/backups/`
- [x] Backup command documented and tested: `sqlite3 ... .backup ...`
- [x] Restore test procedure documented and verified: Safe, non-destructive
- [x] Pre-deployment checklist created: 8 items
- [x] Post-deployment monitoring checklist created: Daily + weekly items
- [x] Limitations documented: SQLite single-user, immutable design
- [x] Operator responsibilities documented: Backup schedule, retention, testing
- [x] All 15 guardrails confirmed

**Householder v1.1 Database Backup Configuration: COMPLETE AND READY FOR NEXT TASK**

---

## References

- `docs/operatinalizing/V1_1_OPERATOR_FOLDER_SEMANTICS.md` — Folder organization
- `docs/operatinalizing/V1_1_OPERATOR_TASK2_EXPORT_OUTPUT_DIR_CONFIGURATION.md` — Export configuration
- `docs/implementation/release/V1_1_OPERATOR_HANDOFF.md` — Operator handoff package
