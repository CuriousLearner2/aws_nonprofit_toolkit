# Householder v1.1 Known Limitations

**Version:** 1.1  
**Release Date:** 2026-06-12  
**Status:** Current Release

---

## Overview

Householder v1.1 is an **export-only** tool designed for donor import review and CSV export. This document lists features that are not included in this release but may be considered for future versions.

---

## Deferred by Design

### Export-Only Model (Not Integrated)
**Status:** Deferred indefinitely (pending business decision)

**What it means:**
- v1.1 generates CSV files locally
- No automatic sync to Givebutter or any CRM
- No credential storage for external systems
- Users manually upload CSVs to their CRM

**Why deferred:**
- Reduces operational risk (no external API dependencies)
- Simpler first release (core workflow proven)
- Allows user feedback on workflow before adding integration
- Avoids credential management complexity

**Future timeline:** To be evaluated after v1.1 user feedback

---

### Bulk Actions
**Status:** Designed but deferred (not implemented in v1.1)

**What it means:**
- Cannot dismiss all validation issues in one action
- Cannot defer multiple items at once
- Each decision made individually in review queue
- No multi-select or bulk operations

**Affected workflows:**
- Validation: Mark items as valid/invalid one at a time
- Normalizations: Accept/reject suggestions individually
- Duplicates: Mark duplicate pairs one at a time
- Households: Confirm/reject groupings one at a time

**User impact:**
- Larger batches take longer (estimated 5-10 min additional time for 100+ items)
- More repetitive clicks
- Better control over individual decisions

**Why deferred:**
- Marginal UX improvement (bulk actions save ~5 min per batch)
- Implementation adds complexity for optimization
- Users can achieve same result manually (just slower)
- Defers until post-launch user feedback validates demand

**Future timeline:** Candidate for v1.2 if user feedback indicates high demand

**Detailed planning:** See [PHASE3_STEP4B_SAFE_BULK_ACTIONS_REFINEMENT_PLANNING.md](../implementation/phase3/PHASE3_STEP4B_SAFE_BULK_ACTIONS_REFINEMENT_PLANNING.md)

---

## Architectural Constraints

### Single-Batch Scope
**Status:** Current design

**What it means:**
- Each import is processed independently
- No cross-batch duplicate detection
- No cross-batch master contact tracking
- Household groupings are per-batch only

**Workaround:**
- Create a single CSV combining records from multiple sources
- Process as one batch

**Future enhancement:**
- Cross-batch matching requires master contact/household infrastructure
- Out of scope for v1.1

---

### Contact Snapshot Immutability
**Status:** Current design

**What it means:**
- Records cannot be merged in-place
- Contact data cannot be edited
- Only decisions about relationships recorded (not data changes)

**Why:**
- Preserves original data integrity
- Enables decision reversal
- Prevents silent mutations

**Workaround:**
- Correct source data and re-import if needed
- Use normalization decisions for standardization (not mutation)

---

### No Master Contacts or Households
**Status:** Current design

**What it means:**
- No durable contact/household entities across imports
- Each import maintains independent contact structure
- Duplicate decisions are per-batch metadata only

**Why:**
- Avoids cross-batch state management
- Keeps scope focused on current import
- Prevents accidental merges across batches

**Future enhancement:**
- Master contacts would require identity resolution
- Out of scope for v1.1

---

## Workflow Constraints

### No Contact Merging
**Status:** Current design

**What it means:**
- Duplicate decisions record relationship (same person)
- Records are not actually merged
- Export includes duplicate indicator; merge happens in CRM

**Why:**
- Preserves bidirectional traceability
- Allows reversible decisions
- CRM may have merge rules/workflows

**Workaround:**
- Manual merge in CRM after import
- Duplicate decision in Householder helps identify what to merge

---

### No Household Assignment
**Status:** Current design

**What it means:**
- Household suggestions are confirmed/rejected
- Grouping is metadata in export
- No permanent household_id in database

**Why:**
- Avoids modifying contact records
- Keeps decisions lightweight
- CRM can define households differently

**Workaround:**
- Use household grouping metadata in export
- CRM implements household structure

---

### No Cross-CRM Features
**Status:** Current design

**What it means:**
- No check against existing Givebutter/CRM contacts
- No deduplication against CRM data
- No real-time sync feedback

**Why:**
- Avoids credentials and API dependencies
- Keeps workflow offline-capable
- Reduces operational risk

**Workaround:**
- Pre-deduplicate export in CRM
- Use CRM's duplicate detection tools

---

## User Interface Constraints

### Validation-Only Empty States
**Status:** Current design

**What it means:**
- If no validation issues exist, queue is empty
- Message shows "All records validated ✓"
- User can proceed to normalizations

**Constraint:**
- Cannot perform bulk dismiss all in validation
- Must be available but not shown if zero items

---

### Read-Only Preview
**Status:** Current design

**What it means:**
- Export preview is read-only
- Cannot edit values in preview
- Must go back to review queues to change decisions

**Why:**
- Keeps audit trail clean (decisions in queues)
- Prevents inconsistent state

**Workaround:**
- Use review queues to change decisions
- Regenerate preview

---

### No In-Line Editing
**Status:** Current design

**What it means:**
- Cannot edit records in review queues
- Cannot change contact data
- Only decisions (mark valid, accept/reject suggestion) allowed

**Why:**
- Preserves data integrity
- Prevents accidental mutations

**Workaround:**
- Correct source CSV and re-import
- Use normalization decisions for standardization

---

## Known Issues / Limitations

### Batch Size Performance
**Status:** Tested up to 500 items

**What it means:**
- System handles 50-500 item batches efficiently
- Larger batches may experience slower UI response
- No technical limit, but recommended max ~500 items

**Workaround:**
- Split large imports into multiple batches

---

### Browser Session Duration
**Status:** No session timeout (currently unlimited)

**What it means:**
- Long-running review sessions won't timeout
- Browser back button may cause session state issues
- Closing and reopening browser is safe

**Recommendation:**
- Avoid using browser back button during review
- Use in-app navigation (Back to Dashboard, etc.)

---

### Concurrent User Edits
**Status:** No locking mechanism

**What it means:**
- Multiple users can review same batch simultaneously
- Last decision wins (overwrites prior decision)
- No conflict detection

**Recommendation:**
- Assign batches to single reviewer
- Communicate who's reviewing each batch

---

## Export Constraints

### CSV-Only Output
**Status:** Current design

**What it means:**
- Export format is comma-separated values only
- No JSON, Excel, or other formats
- Suitable for import to most CRMs

**Future formats:**
- Out of scope for v1.1

---

### No Export Scheduling
**Status:** Current design

**What it means:**
- Exports generated on-demand
- No scheduled/automated export runs
- No integration with background jobs

**Workaround:**
- Manual export; can be done frequently

---

### No Export Validation
**Status:** Current design

**What it means:**
- Export doesn't validate CRM compatibility
- No pre-upload checking against CRM schema
- Errors discovered during CRM import

**Workaround:**
- Test import to CRM before production
- Check export preview for obvious issues

---

## Security Constraints

### No Export Encryption
**Status:** Current design

**What it means:**
- CSV files stored in plaintext on server
- No at-rest encryption of downloads
- Standard file system security applies

**Recommendation:**
- Use HTTPS for all connections
- Secure server file system
- Use SFTP/SSH for downloads in sensitive environments

---

### No Field-Level Access Control
**Status:** Current design

**What it means:**
- Users who can access batch see all fields
- No column-level permissions
- No sensitive field masking

**Recommendation:**
- Limit Householder access to trusted users only (at infrastructure level)
- All users with access see all fields in all batches
- Consider network-level or application-level access restrictions

---

### No Audit Log Export
**Status:** Current design

**What it means:**
- Audit trail visible in UI
- Cannot export audit trail as standalone file
- No API access to audit data

**Workaround:**
- Screenshots of audit trail pages
- Database-level query if direct access available

---

## Operations Constraints

### Single Server Deployment
**Status:** Current design

**What it means:**
- No built-in clustering or load balancing
- Single point of failure
- No automatic failover

**Recommendation:**
- Deploy on reliable infrastructure
- Regular backups of database
- Monitor uptime

---

### No Backup / Recovery Tools
**Status:** Current design

**What it means:**
- Standard database backups apply
- No built-in export/import of batch state
- No point-in-time recovery tools

**Recommendation:**
- Database backups per your standard procedures
- Test restore procedures

---

## Timeline for Future Enhancements

**Candidate Features (Pending User Feedback):**
1. Bulk actions (v1.2 if validated)
2. CRM integration (v2.0 if business decision approved)
3. Cross-batch matching (v2.0 if master data needed)
4. Contact merging (v2.0 if required by workflow)
5. Additional export formats (v2.0 if requested)
6. Concurrent user conflict detection (v1.2 if multi-user common)

**Out of Scope:**
- Full contact/household master data
- Real-time CRM sync
- Two-way sync (CRM → Householder)
- Scheduled exports
- Field-level access control

---

## Documentation References

- [EXPORT_ONLY_WORKFLOW.md](../user-guide/EXPORT_ONLY_WORKFLOW.md) — User workflow guide
- [REVIEWER_WORKFLOW.md](../user-guide/REVIEWER_WORKFLOW.md) — Detailed reviewer guide
- [PHASE3_STEP4B_SAFE_BULK_ACTIONS_REFINEMENT_PLANNING.md](../implementation/phase3/PHASE3_STEP4B_SAFE_BULK_ACTIONS_REFINEMENT_PLANNING.md) — Bulk actions planning (deferred)

---

## Feedback

**Have feedback on these limitations?**
- Contact product team
- Submit feature request
- Provide use case details

**Your input helps prioritize future enhancements.**

