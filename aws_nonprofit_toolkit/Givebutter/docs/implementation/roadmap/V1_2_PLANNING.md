# Householder v1.2 Roadmap Planning

**Status:** PLANNING DOCUMENT ONLY  
**Target Release:** TBD (Q3/Q4 2026, pending validation)  
**Planning Phase:** Pre-implementation (validation of demand required before commitment)  
**Release Model:** Export-only maintained; minor features within scope  

---

## v1.2 Vision

v1.1 proved the export-only workflow. v1.2 focuses on **usability improvements** based on collected user feedback from v1.1 production usage.

**Core hypothesis:** Users may request bulk operations and concurrent user improvements once they use the tool at scale.

**Decision criteria:** Only implement if v1.1 user feedback validates demand (frequency > 20% of batches, or explicit feedback from multiple users).

---

## Candidate Features for v1.2

### Tier 1 Candidates (High Priority If Demand Validated)

#### 1. Safe Bulk Actions (Deferred from Phase 3-Step 4B)

**Status:** Planning document exists (PHASE3_STEP4B_SAFE_BULK_ACTIONS_REFINEMENT_PLANNING.md)

**Scope:**
- Bulk defer duplicate decisions (safe: independent operations)
- Validation-only bulk dismiss (safe: validation issues are independent)
- Explicit preview before bulk action
- Confirmation dialog for safety
- Full audit trail per decision (not bulk records)
- Reversible (can override any decision)

**Not included in bulk actions:**
- Bulk accept normalizations (requires careful decisions)
- Bulk confirm households (requires careful decisions)
- Bulk merge contacts (not in scope)
- Bulk mark duplicate "same_person" (requires careful decisions)

**Estimated effort:** 2-3 weeks (design already exists)  
**Risk level:** Low (design completed, isolated scope)  
**Demand validation needed:** Yes — track bulk action frequency in v1.1  

**How to validate demand:**
- Count how many batches have >50 duplicate deferrals
- Count how many batches have >50 validation issues
- Survey users on time spent in review queues
- Track support requests mentioning "repetitive" or "bulk"

---

#### 2. Concurrent User Conflict Detection

**Status:** Known limitation in v1.1 (last decision wins, no locking)

**Scope:**
- Detect when another user made a decision on same item
- Show warning before saving decision
- Allow user to reload decision or override
- Log conflict in audit trail

**Design approach:**
- Add `last_modified_by` and `last_modified_at` to ReviewDecision
- Check before saving if decision was modified by different user
- Show modal with "Reload/Override" options

**Not included:**
- Pessimistic locking (locks entire batch)
- Batch-level locks (prevents collaboration)
- Real-time notifications

**Estimated effort:** 1-2 weeks  
**Risk level:** Low (adds fields, no behavioral changes)  
**Demand validation needed:** Yes — track multi-user batches in v1.1  

**How to validate demand:**
- Monitor usage patterns (single vs multiple users per batch)
- Track support requests about lost work
- Ask users about concurrent editing scenarios

---

### Tier 2 Candidates (Medium Priority)

#### 3. Audit Log Export

**Status:** Known limitation (audit visible in UI only)

**Scope:**
- Export audit trail as CSV
- Include filters (date range, user, action type)
- Full audit history available for compliance

**Not included:**
- Real-time audit streaming
- Database-level audit tables
- Signed audit records

**Estimated effort:** 1-2 weeks  
**Risk level:** Low (read-only export)  
**Demand validation needed:** Yes — compliance/audit requirements  

**How to validate demand:**
- Ask customers about compliance needs
- Track requests for audit exports
- Understand regulatory environment

---

#### 4. Improved Documentation Index

**Status:** Guides exist but may need better navigation

**Scope:**
- Searchable documentation index
- FAQ section
- Glossary of terms
- Common workflows index
- Troubleshooting guide

**Not included:**
- Video tutorials (out of scope)
- In-app tutorials (out of scope)
- Interactive wizards

**Estimated effort:** 1-2 weeks  
**Risk level:** Minimal (documentation-only)  
**Demand validation needed:** No — always useful  

---

#### 5. Performance Testing & Optimization

**Status:** Tested to 500 items; larger batches untested

**Scope:**
- Performance testing for 500, 1000, 5000 item batches
- Identify bottlenecks
- Optimize hot paths
- Caching improvements if needed
- Database query optimization

**Not included:**
- Architectural changes
- Background job processing
- Pagination of review queues

**Estimated effort:** 2-3 weeks  
**Risk level:** Low (optimization only)  
**Demand validation needed:** Yes — track large batch usage in v1.1  

**How to validate demand:**
- Monitor batch size distribution
- Track performance complaints
- Measure actual processing times in production

---

### Tier 3 Candidates (Low Priority / Future Consideration)

#### 6. Enhanced Validation Messaging

**Status:** Current messages are clear but may have edge cases

**Scope:**
- Better explanations for validation failures
- Suggestions for fixing invalid data
- Examples of valid data formats

**Not included:**
- Validation rule changes
- Automatic corrections
- Smart suggestions

**Estimated effort:** 1-2 weeks  
**Risk level:** Minimal  
**Demand validation needed:** Yes — track validation confusion in support  

---

#### 7. Normalization Suggestion Improvements

**Status:** Current suggestions work but may miss some patterns

**Scope:**
- Better duplicate name detection
- Phone number normalization improvements
- Email parsing enhancements
- Format consistency rules

**Not included:**
- Machine learning-based suggestions
- Third-party enrichment
- External data matching

**Estimated effort:** 2-3 weeks  
**Risk level:** Low (suggestions are non-binding)  
**Demand validation needed:** Yes — track normalization acceptance rates  

---

## Features Explicitly NOT in v1.2

### Deferred to v2.0+ (Business Decision Required)

**CRM/Givebutter Integration** (Phase 4+)
- Requires comprehensive risk review
- Credential management complexity
- API failure handling
- Idempotency guarantees
- Partial writeback handling
- Timeline: v2.0+ only if business approves

**Master Contacts/Households** (v2.0+)
- Requires cross-batch matching design
- Identity resolution complexity
- Cross-batch scope expansion
- Timeline: v2.0+ only if needed

**Contact Merging** (v2.0+)
- Currently CRM responsibility
- Would require design validation
- Timeline: v2.0+ only if workflow requires

**Additional Export Formats** (v2.0+)
- Currently CSV-only
- JSON/Excel support deferred
- Timeline: v2.0+ if requested by customers

---

## v1.2 Acceptance Criteria

All v1.2 work must meet:

### Product
- [x] Export-only model maintained
- [x] No CRM/Givebutter integration
- [x] No credentials added
- [x] No schema changes unless required
- [x] All v1.1 features work identically
- [x] All 1202 tests still pass
- [x] New tests for new features
- [x] Zero regressions

### Documentation
- [x] Release notes updated
- [x] User guides updated if needed
- [x] Known limitations updated
- [x] Deferred features documented

### Data Safety
- [x] No source-data mutations
- [x] No contact mutations
- [x] No contact merging
- [x] No deletion operations
- [x] Audit trail complete
- [x] Decisions remain reversible

### Security
- [x] No new security issues
- [x] Path traversal blocked
- [x] Symlink escapes prevented
- [x] Batch isolation maintained
- [x] No external API calls

---

## Demand Validation Template

For each candidate feature, track:

```markdown
### Feature: [Feature Name]

**v1.1 Tracking Metrics:**
- Support requests mentioning feature: [N]
- User feedback surveys requesting: [Y/N]
- Estimated users affected: [N]
- Estimated time savings: [X minutes/batch]
- User feedback summary: [Quote or summary]

**v1.2 Decision:**
- [ ] High demand validated — implement in v1.2
- [ ] Medium demand — consider for v1.2 if time permits
- [ ] Low/no demand — defer to future
- [ ] Explicitly rejected by users — remove from roadmap

**Decision date:** [Date]  
**Decision makers:** [Names]
```

---

## v1.2 Planning Timeline

### Months 1-2 (Post-v1.1 Launch)
- [ ] Collect v1.1 user feedback
- [ ] Monitor support issues
- [ ] Track usage patterns (batch sizes, user patterns, decision types)
- [ ] Survey users on feature requests
- [ ] Analyze bulk action demand
- [ ] Analyze concurrent user patterns

### Month 3
- [ ] Analyze collected data
- [ ] Validate demand for Tier 1 candidates
- [ ] Make v1.2 feature commitments
- [ ] Schedule implementation kickoff

### Month 4+ (If Approved)
- [ ] Implement validated features
- [ ] Add tests for new features
- [ ] Update documentation
- [ ] Final QA and deployment

---

## Roadmap Decision Points

### Bulk Actions Go/No-Go (Month 3)

**Go to v1.2 if:**
- [ ] >20% of batches have >50 validation issues OR
- [ ] >20% of batches have >20 duplicate deferrals OR
- [ ] Explicit feedback from 3+ customers requesting bulk operations OR
- [ ] Support burden from repetitive clicking shows clear demand

**No-Go if:**
- [ ] <5% of batches have significant bulk operations potential
- [ ] Users report individual decisions are manageable
- [ ] No explicit customer feedback
- [ ] Implement in v1.3+ only if demand emerges later

### Concurrent User Features Go/No-Go (Month 3)

**Go to v1.2 if:**
- [ ] >30% of batches are reviewed by multiple users OR
- [ ] Support reports of lost work due to concurrent edits (>2 reports) OR
- [ ] Explicit customer request for multi-user support

**No-Go if:**
- [ ] <10% of batches are multi-user
- [ ] No support issues reported
- [ ] Users can work around with process (assign batches to users)

---

## Guardrails for v1.2

### Must maintain:

✓ **Export-only model** — No CRM/Givebutter writeback  
✓ **Data immutability** — No source-data or contact mutations  
✓ **Audit trail** — All changes logged  
✓ **Security** — No external API calls, no credentials  
✓ **Reversibility** — Decisions remain changeable  
✓ **Single-batch scope** — No cross-batch operations  

### Allowed changes:

✓ **UI improvements** — Bulk action UI, conflict detection UI  
✓ **Performance** — Optimization, caching  
✓ **Documentation** — Guides, FAQ, index  
✓ **Testing** — New tests for new features  
✓ **Schema additions** — Only if non-breaking (e.g., new columns, no deletions)  

### Forbidden changes:

✗ **CRM writeback** — No external sync  
✗ **Master data** — No cross-batch entities  
✗ **Contact merging** — CRM responsibility  
✗ **New formats** — CSV-only  
✗ **Background jobs** — Synchronous operations only  

---

## Communication & Transparency

### v1.2 Roadmap Communication

**To Users (Post-v1.1 Launch):**
- "v1.1 is here! Tell us what you need next."
- "We're considering bulk actions for v1.2 based on your feedback."
- "Help us prioritize: what saves you the most time?"

**To Stakeholders (Month 3):**
- "Based on v1.1 feedback, here's what we're building in v1.2."
- "Customer demand validated for: [features]"
- "Timeline: [target date]"

**To Support Team (Month 3):**
- "v1.2 will include these improvements"
- "Here's what's still not in scope"
- "Here's how to respond to feature requests"

---

## Version Information

**Product:** Householder  
**Base Version:** v1.1  
**Next Version:** v1.2  
**Status:** Planning only (no implementation started)

**Release criteria:** User demand validation required before commitment.

**Timeline:** TBD (Q3/Q4 2026 pending feedback and business approval)

