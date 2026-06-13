# Export-Only Workflow Guide

**Version:** 1.1  
**Release Status:** Current  
**Model:** Export-only (no CRM/Givebutter writeback)

---

## Overview

Householder v1.1 is an **export-only** tool for nonprofit donor import management. The system helps you review, decide, and export clean donor data as CSV files—but does not write data back to Givebutter or any CRM.

**Core Principle:** The system suggests. The reviewer decides. Raw data stays unchanged.

---

## The Four Safeguards

### 1. **System Suggests, Reviewer Decides**
- The system identifies potential issues (validation problems, possible duplicates, normalization opportunities)
- The system never makes decisions automatically
- Every decision is made by a human reviewer
- Every decision is recorded in the audit trail

### 2. **Raw Data Stays Unchanged**
- Original import records are never modified
- Contact information is never merged or overwritten
- No deletions or permanent changes to source data
- If you change your mind, you can always start over

### 3. **Decisions Are Audit-Backed**
- Every decision (validation override, duplicate determination, normalization acceptance) is logged
- Who decided, when they decided, and why (notes) are recorded
- Complete history allows you to understand the path to export
- No silent changes or automatic updates

### 4. **Exports Are Local CSV Artifacts**
- Generated CSV files are stored locally on your server
- No data is sent to Givebutter during this phase
- CRM writeback is a future enhancement (not in v1.1)
- You control when and where to upload to your CRM

---

## Typical Workflow

### Step 1: Upload Import File
1. Navigate to **Imports**
2. Click **Upload New Import**
3. Select your CSV file (donor list)
4. System processes and creates review queues

### Step 2: Review & Validate
**Route:** Validation Review

- System shows records that failed basic validation
- **Issues might include:** Invalid email, missing required field, malformed phone
- **Your options:** Mark as valid (override) or mark as invalid (confirm issue)
- **Tip:** Each override is recorded; you can see your reasoning in audit trail

### Step 3: Review & Normalize
**Route:** Normalizations Review

- System suggests data cleanup opportunities
- **Examples:** Standardize email domain, format phone to consistent pattern, proper-case name
- **Your options:** Accept suggested normalization or reject it
- **Tip:** Rejections keep original data; accepted changes appear in export

### Step 4: Review Duplicates
**Route:** Possible Duplicates

- System identifies likely duplicates (same address, very similar names, etc.)
- **Your options:** Mark as same person, mark as different people, or defer decision
- **Tip:** Duplicate decisions affect which records appear in final export

### Step 5: Review Households
**Route:** Households Review

- System suggests grouping related records (family members, business partners)
- **Your options:** Confirm household grouping or reject it
- **Tip:** Households appear as meta-information in export; don't affect individual records

### Step 6: Check Export Readiness
**Route:** Export Readiness Dashboard

- See summary of batch status
- Check if all validation, duplicate, normalization, and household decisions are complete
- **Status shows:** ✓ Export Ready or ⚠️ Export Blocked
- If blocked, dashboard links directly to work needed

### Step 7: Generate & Download CSV
**Route:** Export Console

1. Review what will be exported (preview)
2. Click **Generate CSV** (creates local file)
3. Click **Download** (retrieves to your computer)
4. Import to your CRM manually (separate process)

### Step 8: Track Export History
**Route:** Recent Exports

- See all previously generated CSVs
- Timestamps show when each export was created
- Audit trail available for each export's decisions

---

## Key Concepts

### **Blockers vs. Warnings**

- **Blockers** prevent export (e.g., invalid data that can't be resolved)
- **Warnings** are informational (e.g., unusual but valid phone number)
- Warnings don't block export; blockers do

### **Batch**
A single import file and all associated decisions (validation, normalizations, duplicates, households).

### **Review Item**
A specific issue flagged by the system (one validation problem, one duplicate pair, one normalization suggestion, one household grouping).

### **Review Decision**
Your response to a review item (valid, invalid, accept normalization, same person, different person, defer, confirm household, reject household).

### **Audit Trail**
Complete record of who decided what, when, and why. Helps explain export results and track changes over time.

### **Export Readiness**
Batch is ready for export when:
- All blockers are resolved (or batch has zero blockers)
- All validation issues are decided
- Duplicate, normalization, and household reviews are complete

### **CSV Export**
Final output file containing:
- All records (with normalizations applied if accepted)
- Household grouping information (if applicable)
- Deduplicated data (if duplicate decisions were made)
- Ready to upload to your CRM

---

## Safety Guarantees

### ✓ **No Automatic Changes**
Nothing happens without a human decision. No silent updates.

### ✓ **No Data Loss**
Original data is preserved. You can always reprocess the import with different decisions.

### ✓ **No CRM Impact** (v1.1)
Data stays local until you manually upload. No risk of unintended changes in Givebutter.

### ✓ **Full Reversibility**
If you realized you made a wrong decision, you can re-review that item and change your decision. Audit trail shows both decisions.

### ✓ **Complete Traceability**
Every decision is recorded with reviewer, timestamp, and notes. You can always explain why the export looks the way it does.

---

## Common Questions

### Q: Can I undo a decision?
**A:** Yes. Re-open the item in its queue, make a new decision. Both decisions appear in audit trail. The most recent decision is used in export.

### Q: What if I upload the wrong file?
**A:** No problem. Decisions are tied to the batch. Start a new import with the correct file. The incorrect batch remains available (archived) for reference.

### Q: Can I edit the import data?
**A:** No. System is read-only on source data. You can only make review decisions. If you need to change source data, fix the CSV and upload as a new import.

### Q: How do I know what the export will contain?
**A:** Use the **Export Preview** to see exactly which records will be included, with normalizations applied. Preview is always up-to-date with your current decisions.

### Q: Can I export a partial batch?
**A:** No. Export generates all records in the batch (applying all decisions). If you want to export a subset, create a filtered CSV and upload as a separate import.

### Q: Who can see the audit trail?
**A:** (Depends on your deployment's RBAC.) Typically, users who can access the import can see decisions and audit history. Check with your administrator.

### Q: Is there a time limit to make decisions?
**A:** No. Reviews can be paused and resumed. Decisions persist until you change them.

### Q: Can I make decisions without committing to export?
**A:** Yes. You can make all decisions, verify readiness, and generate preview—but skip the final download if you're not ready yet.

---

## Workflow Checklist

- [ ] Import CSV file
- [ ] Complete Validation Review (resolve all blockers)
- [ ] Complete Normalizations Review
- [ ] Complete Duplicates Review
- [ ] Complete Households Review
- [ ] Check Export Readiness Dashboard (confirm ✓ Export Ready)
- [ ] Review Export Preview (verify content)
- [ ] Generate CSV Export
- [ ] Download CSV file
- [ ] Manual upload to CRM (outside this system)

---

## Known Limitations (v1.1)

- **No bulk actions** — Decisions are made individually (not in bulk)
- **No CRM writeback** — No automatic sync to Givebutter
- **No master contacts** — Each import is independent
- **No cross-import matching** — Duplicates detected only within a batch
- **No contact merge** — Decisions track duplicates; don't merge records
- **No household assignment** — Grouping is metadata only

See [V1_1_KNOWN_LIMITATIONS.md](../release/V1_1_KNOWN_LIMITATIONS.md) for details.

---

## Getting Help

- **Validation issues unclear?** → Check validation error message in queue
- **Normalization too aggressive?** → Reject it; original data appears in export
- **Not sure if duplicate?** → Defer decision; re-review later
- **Export blocked?** → Export Readiness Dashboard shows what's needed
- **Data looks wrong in preview?** → Check audit trail for all decisions

