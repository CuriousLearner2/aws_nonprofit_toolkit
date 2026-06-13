# Householder v1.1 — User & Stakeholder Communication Package

**Version:** 1.1  
**Status:** Communication Package Complete  
**Date:** 2026-06-13  
**Purpose:** Prepare deployment communications for Householder v1.1 launch

---

## Executive Summary

This document provides reusable communication templates and messaging for all stakeholder groups: internal stakeholders, users/reviewers, support team, and project sponsors. Clear, consistent messaging ensures all parties understand the export-only model, the manual upload requirement, and the support/feedback mechanisms.

---

## Communication Package Overview

**Audience segments:**
1. Internal stakeholders / project owners
2. End users / reviewers
3. Support team
4. Project sponsors / decision-makers

**Key messages (consistent across all):**
- ✓ v1.1 is export-only (no CRM/Givebutter sync)
- ✓ Users manually upload generated CSV to CRM
- ✓ Householder suggests issues; reviewers decide
- ✓ Raw source data stays unchanged
- ✓ All decisions are audit-backed
- ✓ Feedback will inform v1.1.1, v1.2, v2.0 planning

---

## Draft 1: Stakeholder Briefing Outline

**Audience:** Internal stakeholders, project owners, decision-makers

**Delivery:** Email + optional 30-minute meeting

---

### Email: Householder v1.1 Ready for Deployment

**Subject:** Householder v1.1 Approved for Operator Deployment — Briefing Required

---

**Body:**

Householder v1.1 has completed development and passed comprehensive testing (1202 tests passing, zero regressions). The system is ready for operator deployment under an **export-only model.**

**Key Points:**

1. **What v1.1 is:**
   - CSV import and review tool
   - Suggests potential issues (duplicates, normalizations, validation issues, households)
   - Human reviewers make decisions
   - Generates CRM-ready export CSV

2. **What v1.1 is NOT:**
   - NOT a CRM sync tool (no automatic writeback to Givebutter/CRM)
   - NOT a bulk edit tool (decisions are individual)
   - NOT a contact merge tool (metadata only)
   - NOT a multi-user/RBAC system (single operator deployment)

3. **Export-Only Workflow:**
   ```
   User uploads CSV
   ↓
   Householder reviews for issues
   ↓
   Reviewer makes decisions
   ↓
   Householder generates export CSV
   ↓
   User manually uploads export to CRM (not automatic)
   ```

4. **Safety Guarantees:**
   - All decisions are audit-logged
   - Raw source data never modified
   - Full decision history preserved
   - Immutable data design

5. **Operator-Owned Tasks (required before go-live):**
   - ✓ Directory verification (COMPLETE)
   - ✓ Folder semantics codification (COMPLETE)
   - ✓ Export directory configuration (COMPLETE)
   - ✓ Database backup setup (COMPLETE)
   - ✓ HTTPS/network security (COMPLETE)
   - ✓ Support team briefing (COMPLETE)
   - [ ] User communication (this email)
   - [ ] Deployment day smoke tests
   - [ ] Post-launch monitoring

6. **Known Limitations (15 documented):**
   - No bulk actions (designed, deferred to v1.2)
   - No CRM/Givebutter integration (deferred to v2.0+)
   - No contact merging in app (metadata only)
   - No household assignment in app (metadata only)
   - No multi-user RBAC (deferred to v2.0+)
   - No background jobs or async processing
   - [See complete list: V1_1_KNOWN_LIMITATIONS.md]

7. **Post-Launch Feedback Plan:**
   - Week 1: Daily monitoring and support response
   - Weeks 2-4: Regular feedback collection
   - Week 4: Compile feedback to prioritize v1.1.1, v1.2, v2.0 roadmap

8. **Business Case:**
   - v1.1 enables controlled CSV review and export
   - Operators maintain full audit trail
   - Users can validate, normalize, and de-duplicate donor data
   - CRM integration deferred pending usage data and business approval
   - Investment in Phase 1-3 demonstrates sustainable architecture for future expansion

**Next Steps:**

- [ ] Approve v1.1 for operator deployment
- [ ] Confirm deployment date/time with operator
- [ ] Review support team briefing materials
- [ ] Prepare user communication (template attached)
- [ ] Brief user support team
- [ ] Confirm post-launch monitoring plan
- [ ] Finalize deployment/rollback procedures

**Questions?** Contact [operator/PM name].

---

## Draft 2: User Release Announcement

**Audience:** End users, reviewers, operators

**Delivery:** Email sent before/at deployment

---

### Email: Householder v1.1 is Live — Export-Only Review & Export Tool

**Subject:** Householder v1.1 Launch: How to Use the New Export-Only Review Tool

---

**Body:**

Householder v1.1 is now live! We're excited to share this new **export-only review and export tool** for validating and preparing your donor CSVs for CRM import.

**What is Householder v1.1?**

Householder helps you:
1. Upload raw Givebutter/donor CSVs
2. Review suggested data issues (duplicates, normalizations, validation problems, household matches)
3. Make decisions about each issue (accept, reject, defer)
4. Generate a CRM-ready export CSV
5. Manually upload the export to your CRM

**What's New in v1.1:**

- ✓ Readiness dashboard shows exactly what's blocking export
- ✓ Decision history is fully audit-backed
- ✓ Raw source data always stays unchanged
- ✓ Export files go to dedicated location for download
- ✓ Folder organization is semantic and clear

**Important: Export-Only Model**

⚠️ **Householder does NOT automatically sync to your CRM or Givebutter.**

You must:
1. Use Householder to review and make decisions
2. Generate the export CSV
3. **Manually upload the export CSV to your CRM**

This gives you control over the import process.

**How to Start:**

1. **Upload CSV:** Go to upload page, select your Givebutter CSV
2. **Review Issues:** Work through validation, normalization, duplicate, and household queues
3. **Check Readiness:** Review dashboard to see what's blocking export
4. **Generate Export:** Once ready, generate the export CSV
5. **Download & Upload:** Download from Householder and manually upload to your CRM

Estimated time per batch: 15-30 minutes depending on data quality and batch size.

**Where to Get Help:**

- **Quick Start Guide:** [EXPORT_ONLY_WORKFLOW.md]
- **Reviewer Guide:** [REVIEWER_WORKFLOW.md]
- **Known Limitations:** [V1_1_KNOWN_LIMITATIONS.md]
- **Support Contact:** [support email/channel]

**What's NOT Included (Yet):**

- ✗ Automatic CRM sync (you manually upload the export CSV)
- ✗ Bulk actions (decisions are individual)
- ✗ Contact merging in the app (metadata only)
- ✗ Household assignment in the app (metadata only)
- ✗ Multi-user accounts or permissions

These are deferred to future versions pending business approval and user feedback.

**We Want Your Feedback!**

This is v1.1. We're collecting feedback to prioritize future features:
- What worked well?
- What was confusing?
- What would you prioritize for v1.2?

We'll share a brief feedback form in Week 1. Your input directly shapes our roadmap.

**Questions or Issues?**

Contact [support email] with:
- What you were trying to do
- What happened instead
- Your batch ID (if applicable)

Thank you for using Householder v1.1!

---

## Draft 3: Reviewer Quick-Start

**Audience:** Human reviewers using the tool

**Delivery:** On-screen message + email

---

### Quick-Start Guide: Review & Export in 5 Steps

**1. Upload Your CSV**

Go to Upload page → Select your Givebutter export → Click Upload

Wait for processing (shows record count and any issues found).

---

**2. Review Issues**

Four review queues appear if issues are found:

| Queue | What to Do | Decision Options |
|-------|-----------|------------------|
| **Validation** | Review records with validation failures | Accept / Reject |
| **Normalization** | Review suggested field cleanups (formatting, typos) | Accept / Reject |
| **Duplicates** | Review potential duplicate records | Same Person / Different / Defer |
| **Households** | Review records that might be same household | Confirm / Reject / Defer |

*Tip: Start with Validation, then Normalization, then Duplicates, then Households.*

---

**3. Check Readiness**

Go to Readiness Dashboard:
- ✓ Green = ready to export
- ⚠️ Orange = issues blocking export
- Shows exactly what's left to decide

---

**4. Generate Export**

Once ready:
- Click "Generate Export"
- Wait for processing
- Export CSV is created in `exports/` directory

---

**5. Download & Upload to CRM**

- Download the export CSV from Householder
- **Manually upload to your CRM** (not automatic)
- Done!

---

**Need Help?**

- **Confused about an issue?** Hover over the issue for details
- **Want to defer a decision?** Choose "Defer" and come back later
- **Data looks wrong?** Contact support with your batch ID

---

## Draft 4: Support Team Announcement

**Audience:** Support team

**Delivery:** Email + meeting

---

### Email: Support Team — Householder v1.1 Launch Briefing

**Subject:** v1.1 Launch: Support Team Briefing & Resources

---

**Body:**

Householder v1.1 launches [DATE]. Your role is critical to a successful launch and post-launch support.

**What You Need to Know:**

v1.1 is an **export-only review tool**, NOT a CRM sync tool. Users must manually upload generated exports to their CRM.

**Key Resources:**

1. **Support Readiness Guide** (complete briefing)
   ```
   docs/operatinalizing/V1_1_OPERATOR_TASK5_SUPPORT_READINESS.md
   ```
   Contains:
   - 15+ common Q&A with answers
   - 13 troubleshooting scenarios
   - 10 escalation triggers
   - Issue categorization framework
   - Support ticket template

2. **Release Notes** (what changed)
   ```
   docs/release/V1_1_RELEASE_NOTES.md
   ```

3. **Known Limitations** (what's not in v1.1)
   ```
   docs/release/V1_1_KNOWN_LIMITATIONS.md
   ```

4. **User Guides** (user-facing documentation)
   ```
   docs/user-guide/EXPORT_ONLY_WORKFLOW.md
   docs/user-guide/REVIEWER_WORKFLOW.md
   ```

**Pre-Launch Preparation:**

- [ ] Read support readiness guide (1 hour)
- [ ] Review common Q&A section
- [ ] Review troubleshooting scenarios
- [ ] Familiarize with escalation triggers
- [ ] Save support ticket template
- [ ] Confirm support contact information is in user comms

**Day 1 Support Focus:**

- [ ] Monitor for deployment issues
- [ ] Respond quickly to early user questions
- [ ] Document any unexpected issues
- [ ] Escalate immediately if:
  - Data mutation suspected
  - Export always fails
  - Security concern
  - User cannot complete basic workflow

**Week 1 Feedback Collection:**

- [ ] Track common questions
- [ ] Identify confusion points
- [ ] Note feature requests
- [ ] Document workarounds being used
- [ ] Report to PM by end of week

**Categorizing User Feedback:**

Use these categories for future roadmap planning:

- **v1.1.1 patches:** Critical bugs (export failures, decisions not saving)
- **v1.2 features:** Nice-to-have (bulk actions, selective export, filtering)
- **v2.0+ decisions:** Major features (CRM sync, RBAC, contact merging)

**Key Support Messages:**

When users ask:

**"Does Householder sync to our CRM?"**
→ "No, v1.1 is export-only. You generate an export CSV in Householder and manually upload it to your CRM."

**"Can I bulk approve issues?"**
→ "No, bulk actions are on the v1.2 roadmap. v1.1 requires individual decisions per issue."

**"Can Householder merge duplicate contacts?"**
→ "No, Householder identifies duplicates and lets you decide. Merging happens in your CRM after export."

**"Why can't I see who made each decision?"**
→ "v1.1 doesn't have user tracking. The audit log records what decision was made and when, but not who made it."

**Questions?** Contact [operator/PM] or review support readiness guide.

---

## FAQ: Users & Stakeholders

### 1. Does Householder sync to Givebutter or CRM?

**No.** v1.1 is export-only. You manually upload the generated CSV to your CRM.

---

### 2. Where do generated exports go?

Generated exports are saved to the `exports/` directory, configured at:
```bash
EXPORT_OUTPUT_DIR="/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports"
```

You download from Householder and upload to your CRM.

---

### 3. Is `review/approved` the same as `exports/`?

**No. Critical difference:**

- **`review/approved`** = human-approved source CSV files (original, unchanged)
- **`exports/`** = generated Householder export files (processed, normalized)

Think: Input folder vs Output folder.

---

### 4. What does `flagged` mean?

Files flagged have a **visible issue in the data or file itself:**
- Bad/suspicious donor data
- Invalid email or phone
- Format error or corruption
- Too many duplicates
- Wrong columns

**Action:** Investigate the data issue. May need to request corrected CSV.

---

### 5. What does `followup` mean?

Files in followup need **external context, approval, or clarification:**
- "Is this the final CSV from the fundraiser?"
- "Do we want to include this campaign?"
- "Can you explain this field?"

**Action:** Reach out to appropriate person/team for clarification.

---

### 6. What does `approved` mean?

**Approved means:** "This version of the source file is acceptable to proceed with processing."

It does NOT mean the file is perfect. It means the reviewer has accepted/resolved enough issues that this version can move forward.

---

### 7. Can I edit source data in the app?

**No.** Source data stays unchanged. If data needs correction:
1. Fix the CSV externally
2. Re-upload as a new batch
3. Householder reviews the new batch separately

---

### 8. Can I bulk dismiss or bulk approve issues?

**No.** v1.1 requires individual decisions per issue. Bulk actions are on the v1.2 roadmap.

---

### 9. Can Householder merge contacts?

**No.** Householder identifies duplicates and lets you decide (same person / different person / defer). Merging happens in your CRM after export.

---

### 10. Can Householder assign households?

**No.** Householder suggests household groupings and lets you decide (confirm / reject / defer). The CRM determines household assignment.

---

### 11. Why can't I see who made each decision?

v1.1 doesn't track individual users. The audit log shows what decision was made and when, but not who made it.

If you need user attribution, that's planned for v2.0+ as part of a proper multi-user implementation.

---

### 12. What if export is blocked?

The readiness dashboard shows exactly what's blocking export. Common blockers:
- Unresolved validation issues
- Unresolved duplicates
- Unresolved households
- Unresolved normalizations

**Solution:** Go through each queue and make decisions (accept/reject/defer). Estimated 15-30 minutes per batch.

---

### 13. What if export generation still fails?

Check:
1. Is `EXPORT_OUTPUT_DIR` configured? (Ask operator)
2. Is the directory writable? (Ask operator)
3. Is the directory NOT `review/approved`? (Common mistake)

If still failing, contact support with your batch ID and error message.

---

### 14. How do I report issues?

Contact support with:
- What you were trying to do
- What happened instead
- Your batch ID (if applicable)
- Error message (if shown)

**Support will categorize as:**
- Bug fix (v1.1.1)
- Feature request (v1.2 or v2.0+)
- Documentation gap

---

### 15. How do I request future features?

Submit feature requests through support. We categorize feedback for roadmap planning:

- **v1.2 candidates:** Bulk actions, selective export, filtering
- **v2.0+ candidates:** CRM integration, RBAC, contact merging
- **Out of scope:** Intentional design decisions (immutability, export-only model)

Your feedback directly shapes our roadmap!

---

## Feedback Collection Plan

### Week 1: Immediate Feedback

During first week of go-live:
- [ ] Monitor support tickets
- [ ] Track common user questions
- [ ] Note confusion points
- [ ] Document workarounds being used

### Week 2-4: Structured Feedback

Collect structured feedback on:
- Was the export-only model clear?
- Was the readiness dashboard useful?
- Were review queues understandable?
- Were folder semantics clear?
- Did you need bulk actions? (% saying yes)
- Did you expect CRM/Givebutter sync? (% surprised)
- Were error messages helpful?
- How large were your batches?
- What slowed you down?

### Week 4: Compilation & Analysis

- [ ] Compile all feedback into categories
- [ ] Identify patterns and trends
- [ ] Measure demand signals (% wanting bulk actions, % wanting CRM sync)
- [ ] Assess pain points and workarounds
- [ ] Brief stakeholders on findings
- [ ] Recommend v1.1.1 patches vs v1.2 features vs v2.0+ business decisions

### Feedback Categories

**v1.1.1 Patch Candidates** (fix bugs):
- Export failures
- Decision not saving
- Audit trail gaps
- Data integrity issues

**v1.2 Feature Candidates** (next release):
- Bulk actions (60%+ demand triggers prioritization)
- Selective export
- Filtering/search
- Performance improvements
- UI/UX enhancements

**v2.0+ Business Decisions** (long-term roadmap):
- CRM/Givebutter writeback (75%+ demand triggers business case)
- Multi-user RBAC (30%+ demand triggers requirement)
- Contact merging
- Household assignment
- Cross-import identity matching

**Out of Scope** (by design):
- Source data mutation (intentional immutability)
- Automatic contact changes (intentional review-driven)
- Async/background processing (intentional sync model for v1.1)

---

## Post-Launch Survey Questions

**Optional: Include in Week 1 email**

```
Quick 2-minute survey to shape Householder's future:

1. How clear was the export-only model?
   ☐ Very clear  ☐ Somewhat clear  ☐ Confusing  ☐ Very confusing

2. How useful was the readiness dashboard?
   ☐ Very useful  ☐ Somewhat useful  ☐ Not useful

3. What was the hardest part?
   ☐ Understanding export-only model
   ☐ Using the review queues
   ☐ Finding files in folder structure
   ☐ Something else: ________

4. How large were your batches?
   ☐ 1-100  ☐ 101-500  ☐ 501-1000  ☐ 1000+

5. What would help most for v1.2?
   ☐ Bulk actions  ☐ Filtering  ☐ Better UX  ☐ Performance  ☐ Other: ________

6. Would CRM/Givebutter sync be valuable to you?
   ☐ Critical  ☐ Nice to have  ☐ Not needed

7. Any bugs or issues? (optional)
   ________________________________________

Thank you for helping shape Householder's future!
```

---

## Escalation & Contact Guidance

### For Users:

**Issue Type → Contact**

| Issue | Contact | Urgency |
|-------|---------|----------|
| How do I...? | Support team | Normal |
| Data looks wrong | Support team | Normal |
| Export is blocked | Support team | Normal |
| Export fails | Support team | High |
| Security concern | Operator + Security | Immediate |
| Data missing | Support team | High |

### Support Contact Information

**Email:** [support email]  
**Slack:** [support channel]  
**Hours:** [support hours]  
**Response time:** [SLA]

### For Support Team:

**Escalate to Engineering Immediately If:**
- Data mutation suspected
- Audit trail missing decisions
- Export file missing after success
- Security/access concern
- External API call detected
- Database corruption
- User cannot complete basic workflow

---

## 15 Hard Guardrails (User/Stakeholder Perspective)

v1.1 will NOT:

✓ **Sync to CRM** — Export-only, users upload manually  
✓ **Merge contacts** — Duplicate decisions create metadata only  
✓ **Assign households** — Grouping decisions, CRM assigns  
✓ **Do bulk actions** — Individual decisions required  
✓ **Modify source data** — Raw files stay unchanged  
✓ **Track users** — No individual user identification  
✓ **Require login** — Access is deployment-managed  

These features are available or planned for v2.0+ only.

---

## Sign-Off

**User & Stakeholder Communication Package: COMPLETE**

- [x] Communication package summary created
- [x] Stakeholder briefing outline drafted
- [x] User release announcement drafted
- [x] Reviewer quick-start guide drafted
- [x] Support team announcement drafted
- [x] FAQ section (15 questions) created
- [x] Feedback collection plan documented
- [x] Post-launch survey questions provided
- [x] Escalation guidance included
- [x] All messaging consistent (export-only, manual upload, review-driven)
- [x] All guardrails confirmed

**User & Stakeholder Communication Package: READY FOR DEPLOYMENT**

---

## Usage Instructions

**Before Go-Live:**

1. Customize drafts with:
   - Actual names/emails/channels
   - Deployment date/time
   - Any org-specific details

2. Send stakeholder briefing (Draft 1)

3. Brief support team using (Draft 4)

**At Go-Live:**

1. Send user announcement (Draft 2)

2. Make reviewer quick-start (Draft 3) available in-app

**Post-Launch (Week 1):**

1. Distribute feedback survey

2. Monitor support and categorize feedback

3. Track demand signals

**Week 4:**

1. Compile feedback

2. Brief stakeholders on findings

3. Recommend v1.1.1 / v1.2 / v2.0+ priorities

---

## References

- `docs/operatinalizing/V1_1_OPERATOR_TASK5_SUPPORT_READINESS.md` — Complete support briefing
- `docs/release/V1_1_RELEASE_NOTES.md` — What changed
- `docs/release/V1_1_KNOWN_LIMITATIONS.md` — Known limitations
- `docs/user-guide/EXPORT_ONLY_WORKFLOW.md` — User workflow guide
- `docs/user-guide/REVIEWER_WORKFLOW.md` — Reviewer guide
