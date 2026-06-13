# Householder v1.1.1 Patch Planning

**Status:** PLANNING ONLY  
**Target Release:** TBD (post-v1.1 user feedback)  
**Scope:** Bug fixes and documentation corrections only  
**Release Model:** Export-only (no changes to core architecture)

---

## Patch Scope & Constraints

### v1.1.1 is for:

✓ **Bug fixes** — Issues discovered post-launch  
✓ **Documentation corrections** — Copy, clarity, accuracy  
✓ **Test improvements** — Coverage gaps if discovered  
✓ **Performance tuning** — Minor optimizations  
✓ **Non-functional refinements** — UI copy, error messages  

### v1.1.1 is NOT for:

✗ **New workflows** — No new review types or processes  
✗ **Bulk actions** — Deferred to v1.2 pending demand validation  
✗ **CRM/Givebutter writeback** — Export-only model maintained  
✗ **Schema changes** — No database modifications  
✗ **Auth/RBAC** — No new authentication mechanisms  
✗ **New export formats** — CSV-only maintained  
✗ **Cross-import matching** — Single-batch scope maintained  
✗ **Master data structures** — No master contacts/households  

---

## Known Candidate Issues for v1.1.1

### Documentation Issues (No product behavior change)

**1. Release Notes Wording (COMPLETED)**
- ✓ Fixed: Clarified guardrail wording for export routes
- Status: Already corrected in v1.1
- Impact: Documentation-only, no product behavior change

**2. Release Notes Clarifications (Potential)**
- Issue: Some sections could be clearer for non-technical users
- Scope: Copy improvements, example additions
- Urgency: Low (current notes are accurate)
- Action: Collect user feedback post-launch

**3. User Guide Gaps (Potential)**
- Issue: May discover edge cases not covered in EXPORT_ONLY_WORKFLOW.md
- Scope: Add sections, clarify decision types
- Urgency: Low (guides are comprehensive)
- Action: Collect user feedback during first week of v1.1

**4. Known Limitations Index (Potential)**
- Issue: Users may need quick reference to specific limitation
- Scope: Add table of contents or quick index
- Urgency: Low (full list provided)
- Action: Consider if users request specific limitation frequently

### Code Issues (Small fixes only)

**5. Error Message Improvements (Potential)**
- Issue: Some error messages may be unclear in production
- Scope: Improve wording, add clarification
- Urgency: Only if user feedback indicates confusion
- Action: Monitor support tickets, update copy if needed

**6. Validation Edge Cases (Potential)**
- Issue: Specific field combinations may not validate as expected
- Scope: Fix validation logic for edge cases
- Urgency: Only if users report false positives/negatives
- Action: Track issues, prioritize based on frequency

**7. Export File Formatting (Potential)**
- Issue: CSV output may not match some CRM import formats exactly
- Scope: Adjust column order, format, escaping
- Urgency: Only if CRM import failures reported
- Action: Work with users to identify exact format needed

**8. Performance Issues (Potential)**
- Issue: Batch processing slower than expected for certain data patterns
- Scope: Optimize without changing core logic
- Urgency: Only if users report timeouts for normal batch sizes
- Action: Monitor batch processing times, optimize hot paths

### Test Improvements (Potential)

**9. Integration Test Coverage (Potential)**
- Issue: May discover edge cases during production use not covered by tests
- Scope: Add new integration tests for discovered edge cases
- Urgency: Only if issues discovered in production
- Action: Create tests when issue discovered, fix behavior

**10. Performance Tests (Potential)**
- Issue: Want to establish baseline for larger batch sizes
- Scope: Add performance tests for 100, 250, 500 item batches
- Urgency: Low (system handles 500 items in Phase 3-Step 6)
- Action: Create if needed after gathering production usage data

---

## Patch Decision Criteria

### When to include in v1.1.1:

**Criteria:**
1. **Production Impact** — Users affected or system stability impacted
2. **Scope** — Bug fix, documentation, or performance only (no new features)
3. **Risk** — Very low risk (documentation-only or isolated bug fix)
4. **Testing** — New tests added to prevent regression
5. **Guardrails** — No changes to export-only model or hard guardrails

### When to defer to v1.2:

**Criteria:**
1. **Feature Request** — Requests for new capabilities
2. **Large Scope** — Changes affecting multiple components
3. **Architectural Impact** — Requires design changes
4. **Bulk Actions** — Any bulk action requests (defer to v1.2 pending demand validation)
5. **CRM Integration** — Any writeback requests (defer to v2.0+ pending business decision)

---

## Patch Release Process

### Issue Identification
1. User reports issue in support channel
2. Support verifies issue is reproducible
3. Determine if v1.1.1 candidate or defer to v1.2+

### Issue Investigation
1. Reproduce issue locally
2. Write test case demonstrating issue (if code-level)
3. Determine root cause
4. Assess impact and scope
5. Verify no guardrail violations

### Fix Implementation
1. Create fix (minimal scope)
2. Add or update test to prevent regression
3. Verify all 1202 tests still pass
4. Document change in commit message

### Testing
1. Run full test suite
2. Manual testing of fixed scenario
3. Regression testing (verify no side effects)
4. Performance testing (if applicable)

### Release
1. Create patch commit: `v1.1.1-patch-<issue>`
2. Update CHANGELOG with patch note
3. Update release notes if needed
4. Tag release: `v1.1.1`
5. Deploy to production
6. Monitor for issues

---

## Tracking Template for v1.1.1 Candidates

When issues are reported post-launch, track them here:

```markdown
### Issue: [Issue Title]
- **Reported:** [Date]
- **Reporter:** [Name/Team]
- **Impact:** [Describe who/what is affected]
- **Scope:** [Bug fix / Documentation / Performance / Test]
- **Severity:** [Critical / High / Medium / Low]
- **Root Cause:** [What's wrong]
- **Fix Scope:** [Minimal description of fix]
- **Guardrail Impact:** [None / Clarification needed]
- **Status:** [OPEN / IN PROGRESS / RESOLVED / DEFERRED]
- **Target Release:** [v1.1.1 / v1.2 / v2.0]
```

---

## Known v1.1 Limitations That May Generate v1.1.1 Requests

### Likely v1.1.1 Candidates (If Issues Found)
- Validation error message clarity
- Normalization suggestion wording
- Duplicate detection edge cases
- Export file format adjustments
- Documentation clarifications

### Likely Deferred to v1.2
- Bulk actions (demand validation required)
- Concurrent user improvements
- Audit log export
- Documentation index

### Likely Deferred to v2.0
- CRM/Givebutter integration (business decision required)
- Master contacts/households (cross-batch scope)
- Contact merging in application (CRM responsibility)
- Additional export formats (business requirements)

---

## Post-v1.1 Feedback Collection

### Support Ticket Categories to Monitor:
1. **User Confusion** — Misunderstanding features (possible doc issue)
2. **Configuration Issues** — Export directory, environment setup
3. **Workflow Questions** — How to complete a specific task
4. **Data Issues** — Unexpected validation failures, formatting problems
5. **Performance** — Slow batch processing for large imports
6. **Feature Requests** — Bulk actions, CRM sync, other capabilities

### Weekly Review:
- [ ] Categorize all support issues
- [ ] Identify patterns (same question multiple times = doc issue)
- [ ] Track bug reports (distinguished from feature requests)
- [ ] Evaluate urgency (critical = v1.1.1 candidate)
- [ ] Plan patches if needed

---

## v1.1.1 Release Guardrails

All v1.1 hard guardrails MUST remain in place:

✓ No CRM/Givebutter API calls  
✓ No credentials added  
✓ No writeback routes  
✓ No auth/RBAC changes  
✓ No bulk actions  
✓ No background jobs  
✓ No new export formats  
✓ No source-data mutations  
✓ No contact mutations  
✓ No contact merge  
✓ No contact deletion  
✓ No household_id assignment  
✓ No schema changes  
✓ No cross-import matching  
✓ No master contacts/households  

**Export-only model maintained. All guardrails enforced.**

---

## Version Information

**Product:** Householder  
**Base Version:** v1.1  
**Patch Version:** v1.1.1  
**Status:** Planning only (no issues identified yet)

**Release cadence:** Only if issues discovered in production.

