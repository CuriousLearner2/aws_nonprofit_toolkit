# Householder v1.1 — Support Team Readiness & Briefing

**Version:** 1.1  
**Status:** Support Briefing Complete  
**Date:** 2026-06-13  
**Audience:** Support team, operators, and user-facing staff  
**Purpose:** Prepare support team for Householder v1.1 launch and user inquiries

---

## Executive Summary

Householder v1.1 is a **review and export tool** with no CRM/Givebutter integration. Users upload CSVs, Householder suggests issues (duplicates, normalizations, households, validation), reviewers make decisions, and v1.1 generates a CRM-ready CSV export. Users manually upload the export to their CRM.

**Critical point:** This is fundamentally different from a CRM sync tool. Support team must understand and clearly communicate the export-only model to users.

---

## What Householder v1.1 Is

✓ **Export-only workflow tool:**
- Users upload raw Givebutter/source CSVs
- Householder reviews for data issues (duplicates, normalizations, validation)
- Reviewers make decisions (accept, flag, followup, reject)
- Householder generates CRM-ready CSV export
- Users manually upload export to their CRM

✓ **Audit-backed decision system:**
- Every reviewer decision is logged
- Full audit trail of what decision was made and when; user attribution depends on deployment/infrastructure context and is not provided by v1.1 itself
- Decisions are reversible (new decision creates new audit entry)

✓ **Immutable source data:**
- Raw import rows never modified
- Original Givebutter export CSV unchanged
- Decisions apply only to review/export, not to source

✓ **Human-in-the-loop:**
- Householder suggests (duplicates, normalizations, households)
- Reviewer decides (accept, reject, defer, or request clarification)
- System does not auto-decide or auto-modify data

---

## What Householder v1.1 Is NOT

✗ **Not a CRM sync tool** — No Givebutter/CRM writeback  
✗ **Not a contact database** — No permanent contact records  
✗ **Not a master data system** — No cross-import matching  
✗ **Not a bulk edit tool** — Bulk actions not implemented (deferred to v1.2)  
✗ **Not a multi-user app** — No RBAC, user accounts, or per-user permissions  
✗ **Not a merge tool** — No contact merging (duplicate decisions create metadata only)  
✗ **Not a household assignment tool** — No permanent `household_id` (grouping is metadata)  

---

## Key Folder Semantics for Support

Support must understand these folder meanings and explain them to users:

### Source/Review Files

**`review/approved`**
- Human-approved source/review files ready for export
- NOT generated export output
- Example: "Givebutter_Donations_2026-06-13__APPROVED__20260613-1130.csv"
- May still contain issues; means reviewer accepts this version as basis for export

**`review/flagged`**
- Files with visible data or file issues (bad data, format errors, duplicates)
- Requires operator investigation and action

**`review/followup`**
- Files needing external context, approval, or clarification
- Requires operator to reach out to appropriate person

**`review/rejected`**
- Files rejected by reviewer
- Not proceeding to export

### Generated Artifacts

**`exports/`** (EXPORT_OUTPUT_DIR)
- Generated Householder CSV export files
- Ready for manual CRM/Givebutter upload
- Different from `review/approved` (which is source files)
- Example: "export_householder_batch_001_20260613.csv"

---

## Common Questions and Answers

### Q: Does Householder sync directly to Givebutter or our CRM?

**A:** No. v1.1 is export-only. Here's the workflow:
1. User uploads CSV to Householder
2. Householder suggests issues
3. Reviewer makes decisions
4. Householder generates export CSV
5. **User manually uploads export CSV to their CRM** (not automated)

If the user expects automatic sync, explain: "That's deferred to v2.0+ pending business approval."

---

### Q: Where do generated exports go?

**A:** Generated exports are saved to:
```bash
EXPORT_OUTPUT_DIR="/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports"
```

The user downloads from the Householder interface. The file is ready to upload to their CRM.

---

### Q: Is `review/approved` the same as the export folder?

**A:** No. Critical distinction:

- **`review/approved`** = human-approved source CSV files (original, unchanged)
- **`exports/`** = generated Householder export artifacts (processed, normalized, deduplicated)

Think of it as:
- Input folder: `review/approved` (what the source file was approved as)
- Output folder: `exports/` (what Householder generated from that input)

---

### Q: What is the difference between `flagged` and `followup`?

**A:** 

**Flagged:** There's an issue visible in the file itself.
- Examples: bad data, invalid email/phone, format error, too many duplicates
- Action: Investigate the data quality issue; may need to request corrected file

**Followup:** No visible issue, but need external context/approval before deciding.
- Examples: "Is this the final file?" "Do we want to include this campaign?" "Can you confirm the source?"
- Action: Reach out to appropriate person/team for clarification

**Decision rule:** If you can see the problem in the file → flagged. If you need to ask someone else → followup.

---

### Q: Can I bulk dismiss issues or decisions?

**A:** No. Bulk actions (bulk dismiss, bulk defer, bulk confirm) are designed but deferred to v1.2. v1.1 requires individual decisions.

If user wants bulk actions: "That's on the v1.2 roadmap. We're collecting usage data post-launch to prioritize it."

---

### Q: Can Householder merge or de-duplicate my contacts?

**A:** No. Householder identifies potential duplicates and lets the reviewer decide:
- **Same person?** → Decision recorded, metadata created
- **Different people?** → Decision recorded, kept separate
- **Defer?** → Needs more review, mark for followup

Householder does NOT merge contacts in the app. The export CSV reflects these decisions, and the user decides how to handle merging in their CRM.

---

### Q: Can Householder assign households or group people?

**A:** Householder identifies potential household members and lets the reviewer decide:
- **Same household?** → Decision recorded, grouping metadata created
- **Different households?** → Decision recorded, kept separate
- **Defer?** → Needs more review, mark for followup

Householder does NOT permanently assign `household_id` in the app. Grouping is metadata only. The export CSV reflects these decisions.

---

### Q: Can users edit or correct source data in the app?

**A:** No. Source data remains unchanged. If data needs correction:
1. User corrects the source CSV externally (in spreadsheet)
2. User re-uploads corrected CSV to Householder
3. Householder reviews again
4. Reviewer makes new decisions

The old import is archived; the corrected import is reviewed separately.

---

### Q: Export generation is blocked. Why?

**A:** Common reasons:
1. **Unresolved validation issues** — Some records failed validation. User must review and accept/reject/flag them.
2. **Unresolved duplicates** — Some duplicate pairs not yet decided. User must decide same/different/defer.
3. **Unresolved households** — Some household groups not yet decided. User must decide confirm/reject/defer.
4. **Unresolved normalizations** — Some suggested normalizations not yet accepted/rejected.

The error message should tell which blocker type. User must resolve ALL blockers before export.

---

### Q: What if export generation still fails?

**A:** Check:
1. `EXPORT_OUTPUT_DIR` is configured: `export EXPORT_OUTPUT_DIR="/path/to/exports"`
2. Directory exists: `ls -ld $EXPORT_OUTPUT_DIR`
3. Directory is writable: `touch $EXPORT_OUTPUT_DIR/.test && rm $EXPORT_OUTPUT_DIR/.test`
4. Directory is NOT `review/approved` (common mistake)

If still failing, escalate to engineering with export batch ID and error message.

---

### Q: What if the user expects CRM/Givebutter writeback?

**A:** CRM integration is deferred to v2.0+ pending:
- Business approval and risk review
- Cross-import identity matching (future Phase 2+)
- Comprehensive master-data design
- User feedback on v1.1 demand

Current guidance: "v1.1 is export-only. We're collecting feedback post-launch to prioritize CRM integration for v2.0."

---

### Q: Why doesn't Householder know who made each decision?

**A:** v1.1 has no user model or RBAC. The audit trail records:
- What decision was made
- When it was made
- Which batch/item it applies to

But not who made it (no user tracking in app).

If user needs user attribution, that's deferred to v2.0+ with proper user model implementation.

---

### Q: Can I access Householder remotely or from home?

**A:** Depends on deployment:

**Local network:** Ask operator: "Is Householder accessible from my network?"

**Remote access:** Operator configures this with VPN, reverse proxy, or SSO. Ask: "How do I access Householder?"

**Access control:** Is via deployment environment (VPN, proxy, firewall), not the app itself.

---

### Q: Do I need a password or login?

**A:** No. v1.1 has no login system. Access is controlled by:
- Localhost binding (if local-only)
- VPN/firewall (if private network)
- Reverse proxy with SSO (if internet-exposed)

Ask operator: "How do I access Householder?" They'll explain access method.

---

### Q: Can I export just part of a batch?

**A:** No. Export is batch-wide. All records in the batch are exported together.

If user wants selective export, that's deferred to v1.2 roadmap.

---

### Q: Can I re-import a batch after exporting?

**A:** Yes. You can upload the same source CSV again as a new batch. It will be a separate import with no decisions carried over.

---

## Troubleshooting Guide

### Issue: Export Directory Not Configured

**Symptoms:** Export button doesn't work; error mentions missing directory

**Check:**
```bash
echo $EXPORT_OUTPUT_DIR
```

Should show:
```
/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports
```

**Fix:** Operator must set environment variable before starting app:
```bash
export EXPORT_OUTPUT_DIR="/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports"
```

---

### Issue: Export Directory Not Writable

**Symptoms:** Export fails with permission error

**Check:**
```bash
touch $EXPORT_OUTPUT_DIR/.test && rm $EXPORT_OUTPUT_DIR/.test
```

Should succeed without error.

**Fix:** Operator must verify directory permissions:
```bash
ls -ld $EXPORT_OUTPUT_DIR
# Should show: drwxr-xr-x or similar (755)
chmod 755 $EXPORT_OUTPUT_DIR  # If needed
```

---

### Issue: Export File Doesn't Appear in exports/

**Symptoms:** Export says "success" but file not found

**Check:**
1. Correct directory: `ls -l $EXPORT_OUTPUT_DIR`
2. File naming: Files should be `export_*.csv`
3. Timestamp: Most recent file should have today's date

**Fix:**
- Verify EXPORT_OUTPUT_DIR is configured correctly (not `review/approved`)
- Check directory permissions (should be writable)
- Re-run export and check immediately

If still missing, escalate to engineering with batch ID and timestamp.

---

### Issue: User Expects CRM Sync

**Symptoms:** User asks "When will my CRM be updated?" or "Did the donation sync?"

**Explanation:**
"v1.1 is export-only. You must manually upload the generated CSV to your CRM. The sync is not automatic."

If user wants automatic sync: "That's deferred to v2.0+. We're collecting feedback post-launch to prioritize it."

---

### Issue: User Confuses review/approved and exports/

**Symptoms:** User asks "Why is the approved file different from the export?"

**Explanation:**
- **`review/approved`** = Your original source file after review (unchanged source data)
- **`exports/`** = Householder-generated CSV ready for CRM (normalized, deduplicated, with decision metadata)

Think: Input vs Output. Source vs Generated.

---

### Issue: User Can't Distinguish flagged vs followup

**Symptoms:** User marks wrong folder or is confused about action required

**Decision rule:**
- **See a data problem in the file?** → flagged
- **Need to ask someone else?** → followup

Examples:
- "This CSV has a bad email address" → flagged (visible problem)
- "Is this the final CSV from the fundraiser?" → followup (need to ask)

---

### Issue: User Sees Blocked Export

**Symptoms:** Export button says "blocked" with list of blockers

**Common blockers:**
1. Unresolved validation issues
2. Unresolved duplicates
3. Unresolved households
4. Unresolved normalizations

**Fix:** User must go through each review queue and make decisions (accept, reject, or defer).

Expected time: 10-20 minutes per 100-record batch.

---

### Issue: User Reports Missing or Malformed Data

**Symptoms:** "A record is missing!" or "The data looks wrong!"

**Check:**
1. Is it in the original source CSV? (Check `review/approved` source file)
2. Did the user mark it valid or invalid in validation review?
3. Is it in the export? (Check `exports/` export CSV)

**Explanation:**
- If missing from source: It wasn't in the original Givebutter export
- If marked invalid: Won't appear in export (validation decision)
- If marked valid but not in export: Escalate to engineering

---

### Issue: User Asks Who Made Each Decision

**Symptoms:** "Who approved this duplicate decision?" or "Who made this validation call?"

**Answer:** v1.1 has no user tracking. The audit log shows decisions but not who made them.

If user needs user attribution: "That's deferred to v2.0+ with proper user model implementation."

---

### Issue: Database Backup/Restore Question

**Symptoms:** User asks "Do you have backups?" or "Can I restore old data?"

**Answer:** Database backups are operator-managed. See:
```
docs/operatinalizing/V1_1_OPERATOR_TASK3_DATABASE_BACKUP_CONFIGURATION.md
```

For users: "Backups are maintained by the operations team. If you have data concerns, escalate to engineering."

---

### Issue: User Reports Security/Access Concern

**Symptoms:** "I was able to access another user's data!" or "The app is not secure!"

**Action:** Escalate immediately to engineering. Include:
- Exact steps to reproduce
- What unauthorized access/behavior occurred
- When it was discovered

---

## Escalation Triggers

Escalate **immediately** to engineering if:

1. **Data mutation suspected**
   - User reports data changed unexpectedly
   - Source CSV rows appear modified

2. **Audit trail missing decision**
   - Decision made but not logged
   - Audit log shows gaps

3. **Export file missing after successful generation**
   - Export says "success" but file not in `exports/`
   - Repeated issue

4. **Path traversal or security concern**
   - User reports accessing files outside expected directories
   - Unexpected URL patterns working

5. **Unexpected external API call**
   - Network monitoring shows call to Givebutter/CRM
   - Unexpected external service contacted

6. **Credential exposure**
   - API keys or passwords visible in logs
   - Database credentials exposed

7. **Database corruption or data loss**
   - Audit trail has gaps
   - Data integrity issues detected

8. **Backup failure**
   - Backups not being created
   - Restore tests failing

9. **User cannot complete core workflow**
   - Upload fails
   - Review decisions don't save
   - Export generation always fails

10. **Unexpected behavior inconsistent with documentation**
    - Something doesn't work as documented
    - Feature works differently than described

---

## Issue Categorization for Roadmap Planning

When users report issues or request features, categorize as:

### v1.1.1 Patch Candidates (Fix bugs)
- Export always fails for large batches
- Validation decision not saving
- Audit log not recording correctly
- File permission issues
- Critical data loss

### v1.2 Feature Candidates (Next release)
- Bulk dismiss/defer/confirm
- Export only subset of batch
- Selective export by record
- Enhanced filtering/search
- Better UI/UX for large batches
- Performance improvements for 10K+ rows

### v2.0+ Business Decisions (Long-term roadmap)
- CRM/Givebutter writeback
- Multi-user with RBAC
- Cross-import identity matching
- Master contact database
- Household assignment
- Contact merging
- Advanced household matching
- User authentication/SSO

### Not Planned (Out of scope)
- Bulk editing source data (stays immutable by design)
- Contact merge in app (metadata only)
- Permanent household_id assignment (metadata only)
- Background jobs (async processing)
- Real-time CRM sync (intentionally manual export-only model)

---

## Support Ticket Template

**When opening support ticket for engineering:**

```
Issue Title: [Brief description]

v1.1 Component:
  [ ] Upload/Validation
  [ ] Normalization Review
  [ ] Duplicate Review
  [ ] Household Review
  [ ] Export/Readiness
  [ ] Database/Backup
  [ ] Security/Access
  [ ] Performance/Other

Severity:
  [ ] Critical (blocks workflow)
  [ ] High (significant impact)
  [ ] Medium (workaround exists)
  [ ] Low (minor issue)

Steps to Reproduce:
1. 
2. 
3. 

Expected Result:
[What should happen]

Actual Result:
[What actually happens]

Batch ID: [If applicable]
User: [If applicable]
Timestamp: [When issue occurred]

Attachments:
- Error log excerpt (if available)
- CSV sample (if applicable)
```

---

## Post-Launch Feedback Collection

During first week of deployment, collect feedback on:

1. **What worked well?**
   - Which features are most useful?
   - Which workflows are smooth?

2. **What's confusing?**
   - Does export-only model make sense?
   - Are folder semantics clear?
   - Are decision rules understood?

3. **What's missing or blocked?**
   - Which features do users ask for?
   - What workarounds are needed?
   - Which workflows are slow?

4. **Demand signals:**
   - How many users need bulk actions? (60%+ indicates v1.2 priority)
   - How many users need CRM sync? (75%+ indicates v2.0 business case)
   - How many users need multi-user/RBAC? (30%+ indicates v2.0 priority)

---

## Known Limitations Support Script

When user hits a known limitation, use this script:

**"That feature is deferred to [version] based on feedback and business priorities. Here's why v1.1 doesn't have it:"**

1. **Bulk actions** → v1.2 (designed but not implemented; collecting usage data)
2. **CRM writeback** → v2.0+ (requires identity matching; business approval needed)
3. **Contact merging** → v2.0+ (requires master data design; affects other systems)
4. **Household assignment** → v2.0+ (permanent ID affects downstream systems)
5. **Multi-user RBAC** → v2.0+ (requires authentication system; not v1.1 scope)
6. **Export subsets** → v1.2 (designed but deferred; validating demand)
7. **Background jobs** → v1.2+ (not v1.1 scope; all operations synchronous)

**Always close with:** "We're collecting feedback post-launch. If this feature is critical for your workflow, please let us know — it helps us prioritize the roadmap."

---

## 15 Hard Guardrails (Support Perspective)

Support team should know these will NOT change in v1.1:

✓ **No CRM/Givebutter integration** — Export-only, no writeback  
✓ **No contact merging** — Duplicate decisions create metadata only  
✓ **No household assignment** — Grouping is metadata only  
✓ **No bulk actions** — All decisions individual  
✓ **No source data mutation** — Raw files unchanged  
✓ **No user model** — No login, no RBAC, no user tracking  
✓ **No authentication** — Access is deployment/infrastructure managed  

---

## Sign-Off

**Support Team Briefing: COMPLETE**

- [x] What v1.1 is (export-only workflow tool)
- [x] What v1.1 is not (CRM sync, contact database, bulk tool, multi-user RBAC)
- [x] Key folder semantics explained
- [x] 15+ common Q&A with clear answers
- [x] Troubleshooting guide with solutions
- [x] Escalation triggers identified
- [x] Issue categorization framework
- [x] Support ticket template
- [x] Feedback collection guidance
- [x] Known limitations script
- [x] Guardrails confirmed

**Support team is prepared to brief and support users for Householder v1.1.**

---

## References

- `docs/operatinalizing/V1_1_OPERATOR_FOLDER_SEMANTICS.md` — Folder semantics (detailed)
- `docs/operatinalizing/V1_1_OPERATOR_TASK2_EXPORT_OUTPUT_DIR_CONFIGURATION.md` — Export path config
- `docs/operatinalizing/V1_1_OPERATOR_TASK3_DATABASE_BACKUP_CONFIGURATION.md` — Backup procedures
- `docs/operatinalizing/V1_1_OPERATOR_TASK4_HTTPS_NETWORK_SECURITY.md` — Security/access
- `docs/release/V1_1_RELEASE_NOTES.md` — Release notes (user-facing)
- `docs/release/V1_1_KNOWN_LIMITATIONS.md` — Limitations documentation
