# Householder v1.1 Release Notes

**Version:** 1.1  
**Release Date:** 2026-06-13  
**Release Model:** Export-Only (No CRM Integration)  
**Status:** Production Ready

---

## What's New in v1.1

### P0 Critical Fixes

**Export Directory Configuration Validation**
- System now validates export directory configuration at startup
- Clear error messages guide users to fix missing or inaccessible directories
- Prevents silent export failures due to configuration issues

**Blocked Export Messaging**
- When export cannot proceed, users see enumerated blockers (validation issues, normalization rejections, duplicate deferrals, household rejections)
- Action-oriented messaging directs users to specific review queues
- No ambiguous "export failed" messages

**Empty State Messaging**
- Review queues show clear "All [category] valid ✓" messages when items complete
- Users understand workflow progress at a glance
- Guidance to proceed to next review stage

**Recent Exports Limit (50 items)**
- Exports console shows most recent 50 exports
- Older exports remain in system but not displayed in list
- Improves console performance for users with large export histories

### Export Readiness Dashboard

**New Feature: Batch-Level Readiness Visibility**
- One-page status view showing whether batch is ready for export
- Displays:
  - Ready/Blocked status badge
  - Blocker enumeration with counts (validation issues, rejections, deferrals)
  - Warning details (decision coverage, edge cases)
  - Review queue status cards (items in each queue, progress)
- Navigation links to pending work
- Replaces need to manually check each review queue

**Readiness Checks**
- Export is BLOCKED if any validation issues remain
- Export is BLOCKED if any normalization rejections exist
- Export is BLOCKED if any household rejections exist
- Export is BLOCKED if any duplicate items deferred (no decision)
- Export is READY when all decisions complete and no blockers remain

### Enhanced Documentation

**User Workflow Guide** (`EXPORT_ONLY_WORKFLOW.md`)
- Complete 8-step workflow: Upload → Validate → Normalize → Duplicates → Households → Readiness → Export → Download
- Four safeguards explained: suggests (not decides), decides (in review queues), data unchanged (immutable), audit logged (full trail)
- Key concepts: blockers vs warnings, reversibility, audit trail access
- Common questions answered
- Workflow checklist for users

**Reviewer Workflow Guide** (`REVIEWER_WORKFLOW.md`)
- Decision types per review category
  - **Validation:** Mark as valid or invalid
  - **Normalizations:** Accept suggestion or reject with note
  - **Duplicates:** Same person, different person, or defer decision
  - **Households:** Confirm grouping or reject
- Navigation tips, decision reversal instructions
- Best practices and scenarios
- Notes guidance and error handling

**Known Limitations** (`V1_1_KNOWN_LIMITATIONS.md`)
- 15 documented limitations with rationale and future timeline
- Clearly marks features as "out of scope for v1.1" vs "designed but deferred" vs "architectural constraint"
- Future enhancement candidates identified (bulk actions, CRM integration, cross-batch matching, etc.)
- User feedback encouraged for prioritizing future work

### Safety Model Reinforced

**Export-Only Architecture**
- No CRM/Givebutter API integration in v1.1
- No automatic data sync to external systems
- No credential storage for external services
- Users manually upload CSV to their CRM
- Reduces operational risk; workflow proven before integration

**Data Immutability Guarantees**
- Raw import rows never modified
- Contact snapshots never merged or changed
- Decisions recorded as metadata; source data unchanged
- Enables complete decision reversal
- Audit trail preserves all changes

**Audit Trail Complete**
- Every decision logged with timestamp, user, decision type, notes (if applicable)
- Full decision history visible in UI
- Immutable append-only records
- Enables compliance and dispute resolution

---

## What's NOT Included in v1.1

### Intentionally Deferred

**Bulk Actions** (Designed; v1.2 if demand validated)
- Cannot bulk dismiss validation issues
- Cannot bulk defer decisions
- Each decision made individually in review queue
- Estimated 5-10 min additional time for 100+ item batches
- Deferred pending post-launch user feedback

**CRM/Givebutter Integration** (Export-only model)
- No automatic sync to Givebutter
- No API credential management
- No real-time writeback
- Manual CSV import to CRM (user-controlled)
- Reduces risk; allows workflow validation before integration

**Master Contacts/Households** (v2.0 if cross-batch needed)
- Each import independent
- No cross-batch duplicate detection
- No cross-batch household grouping
- No durable master contact structure
- Keeps scope focused on current import

**Contact Merging** (CRM responsibility)
- Duplicate decisions recorded as metadata
- Records not actually merged in Householder
- CRM performs merge during import
- Preserves bidirectional traceability

### Architectural Constraints

**Single-Batch Scope**
- One batch processed independently
- No multi-batch operations
- Workaround: combine sources in single CSV

**No Field-Level Access Control**
- All users with Householder access see all fields
- No column-level permissions
- Recommendation: limit access at infrastructure level

**No In-Line Editing**
- Cannot modify records in review queues
- Correction method: fix source CSV and re-import
- Normalization decisions for standardization (not mutation)

**CSV-Only Export**
- No JSON, Excel, or proprietary formats
- Suitable for import to most CRMs
- Plaintext on server (no encryption)

**No Export Scheduling**
- On-demand generation only
- No background jobs or scheduled runs
- Manual export; can be generated frequently

**No Export Validation**
- Against CRM schema: errors discovered during CRM import
- Workaround: test import before production

---

## Performance Characteristics

### Batch Size
- **Tested to:** 500 items
- **Recommended:** 50-500 item batches
- **Larger batches:** May experience slower UI response
- **Workaround:** Split large imports

### Browser Session
- No session timeout (currently unlimited)
- Closing and reopening browser is safe
- Avoid browser back button during active review

### Concurrent Users
- Multiple users can review same batch simultaneously
- Last decision wins (no conflict detection)
- Recommendation: assign batches to single reviewer

### Export Generation
- Synchronous operation (user waits for completion)
- <1 second typical for 100-500 item batches
- CSV streamed directly to browser

---

## Security Notes

### File Handling
- Path traversal attacks blocked
- Symlink escapes prevented
- Files downloaded securely with access control

### Data Protection
- HTTPS recommended for all connections
- Use SFTP/SSH for downloads in sensitive environments
- Secure server file system
- Standard database backups apply

### Access Control
- Infrastructure-level RBAC (no application-level auth changes)
- All users with Householder access see all fields
- Consider network-level restrictions if needed

---

## Guardrails Enforced

v1.1 maintains strict boundaries:

✓ **No CRM/Givebutter API calls** — Export-only  
✓ **No credentials required** — No external auth  
✓ **No writeback routes** — Export routes read-only  
✓ **No auth/RBAC changes** — Uses existing context  
✓ **No bulk actions** — Individual decisions only  
✓ **No background jobs** — Synchronous operations  
✓ **No new export formats** — CSV-only  
✓ **No source-data mutations** — Raw rows unchanged  
✓ **No contact mutations** — Contact snapshots unchanged  
✓ **No contact merge** — Decisions create metadata; CRM merges  
✓ **No contact deletion** — No deletion operations  
✓ **No household assignment** — Grouping is metadata only  
✓ **No schema changes** — Zero database modifications  
✓ **No cross-import matching** — Single-batch scope  
✓ **No master contacts** — Each import independent  

---

## Quality Metrics

### Test Coverage
```
Unit tests:        760 passing
Integration tests: 442 passing
Total:            1202 passing
Regressions:        0
Execution time:  ~13 seconds
```

### Critical Workflows Verified
- ✓ Upload and validation workflow
- ✓ Review queue operations (all 4 types)
- ✓ Export readiness computation
- ✓ Export preview generation
- ✓ Export file download
- ✓ Audit trail logging and access
- ✓ Error handling and messaging

### Security Tests
- ✓ Path traversal blocked
- ✓ Symlink escapes prevented
- ✓ Batch isolation enforced
- ✓ Read-only routes verified
- ✓ No external API calls detected

---

## Upgrade Path

**From v1.0 to v1.1:**
- No breaking changes
- New readiness dashboard available immediately
- Documentation and UX improvements deploy transparently
- Existing imports continue working as before

**Future Versions:**
- v1.1.1 (patch): bug fixes, performance improvements
- v1.2 (minor): bulk actions (if validated), concurrent user improvements
- v2.0 (major): CRM integration, cross-batch matching, master data

---

## Getting Started with v1.1

1. **Read:** [User Workflow Guide](../user-guide/EXPORT_ONLY_WORKFLOW.md)
2. **Review:** [Known Limitations](V1_1_KNOWN_LIMITATIONS.md)
3. **Upload:** CSV file with donor/contact records
4. **Review:** Work through validation, normalizations, duplicates, households queues
5. **Check:** Readiness dashboard shows export is ready
6. **Export:** Generate CSV file
7. **Download:** Save file locally
8. **Import:** Upload CSV to your CRM (manual step)

**Need help?** See [Reviewer Workflow Guide](../user-guide/REVIEWER_WORKFLOW.md) for decision-specific guidance.

---

## Feedback & Support

**Have questions about v1.1?**
- Review [Known Limitations](V1_1_KNOWN_LIMITATIONS.md)
- Check [User Workflow Guide](../user-guide/EXPORT_ONLY_WORKFLOW.md)
- Contact support with specific use cases

**Have feature requests?**
- Bulk actions (v1.2 candidate)
- CRM integration (v2.0 candidate)
- Additional export formats (v2.0 candidate)
- Concurrent user conflict detection (v1.2 candidate)

**Your input shapes future releases.**

---

## Technical Summary

**Product:** Householder  
**Release:** v1.1  
**Model:** Export-Only (No CRM Integration)  
**Architecture:** Review workflow + CSV export  
**Database:** SQLite with audit trail  
**Deployment:** Single server, synchronous operations  
**Compliance:** Immutable audit trail, no external mutations  

**v1.1 is production-ready for export-only donor import management.**

