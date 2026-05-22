# AWS Nonprofit Toolkit Roadmap

**Last Updated:** 2026-05-21  
**Current Focus:** Track 2 (AWS Personalize) Validation → Scale → Integration

---

## Overview

The toolkit uses a **dual-track approach** to nonprofit growth:
- **Track 1 (Acquisition):** Find new donors via Meta lookalikes
- **Track 2 (Retention):** Keep donors engaged via AWS Personalize AI

This roadmap outlines the validation, scaling, and integration phases for both tracks.

---

## Phase 1: Validate the Pipeline (This Week) ⏳

**Goal:** Prove end-to-end functionality with current dataset

**Timeline:** 1-2 hours  
**Status:** Ready to start  
**Owner:** Next available agent

### Tasks

1. **Train Recommender Model** (~15 minutes)
   - Input: 500 imported donor interactions (ACTIVE dataset)
   - Create Personalize solution: `USER_PERSONALIZATION` recipe
   - Create and train solution version
   - Monitor until ACTIVE status

2. **Generate Batch Inference** (~10 minutes)
   - Run trained model on donor list
   - Output: JSON with engagement scores per donor
   - Write to S3: `s3://{bucket}/batch_output/phase1/`

3. **Extract Donor Segments** (~5 minutes)
   - Parse inference results
   - Categorize by engagement level:
     - High (>0.8): "Likely Responders"
     - Medium (0.5-0.8): "Warm Leads"
     - Low (<0.5): "Cold Prospects"
   - Document segment sizes and signal strength

4. **Validate Outputs** (~15 minutes)
   - Do rankings make business sense?
   - Do segments have meaningful differences?
   - Are top-ranked donors actually high-value?
   - Document findings and any anomalies

### Success Criteria

- [ ] Model trains to completion without errors
- [ ] Batch inference generates predictions for all donors
- [ ] Segments are created and categorized
- [ ] Validation confirms rankings correlate with donor value
- [ ] Documentation shows what patterns the model learned

### Deliverables

- ✅ Trained model ARN
- ✅ Batch inference output (JSON)
- ✅ Segment breakdown (counts, characteristics)
- ✅ Validation report (does this work?)
- ✅ Next phase go/no-go decision

### Risk Assessment

**Low Risk:** All infrastructure is ready, data is imported, IAM is configured  
**Assumption:** Data quality is sufficient for model training

---

## Phase 2: Scale to Production Data (1-2 Weeks) 📊

**Goal:** Validate that model performs with 10x+ more donor interactions

**Timeline:** 2-3 hours  
**Depends On:** Phase 1 success  
**Owner:** Agent or team

### Tasks

1. **Prepare Large Dataset** (~30 minutes)
   - Source: `datasets/large_nonprofit_interactions.csv` (5,000+ interactions)
   - Validate format matches schema
   - Check for data quality issues
   - Upload to S3: `s3://{bucket}/nonprofit/interactions/large_interactions.csv`

2. **Create New Dataset in Personalize** (~5 minutes)
   - New dataset group: `nonprofit-donors-large-{timestamp}`
   - New interactions dataset
   - Upload large CSV

3. **Trigger Large-Scale Import** (~varies)
   - Monitor import job
   - Expected time: 15-30 minutes for 5,000 records
   - Verify ACTIVE status

4. **Train Model on Large Dataset** (~20-30 minutes)
   - New solution version
   - Compare metrics with Phase 1
   - Verify coverage and relevance metrics improve or hold

5. **Generate Predictions at Scale** (~10 minutes)
   - Batch inference on full donor base
   - Output to: `s3://{bucket}/batch_output/phase2/`

6. **Validate Scaling** (~30 minutes)
   - Compare Phase 1 vs Phase 2 results
   - Do top segments match expectations?
   - Are patterns stable at 10x scale?
   - Document any differences or degradation

### Success Criteria

- [ ] Large dataset imports successfully
- [ ] Model trains without degradation
- [ ] Predictions generated for all 5,000+ donors
- [ ] Patterns from Phase 1 hold at scale
- [ ] Metrics document model quality

### Deliverables

- ✅ Large dataset import job ARN
- ✅ Trained model on large dataset (ARN)
- ✅ Batch inference results (5,000+ donors)
- ✅ Comparative analysis (Phase 1 vs Phase 2)
- ✅ Scale validation report
- ✅ Go/no-go for Phase 3

### Risk Assessment

**Medium Risk:** Larger dataset may reveal data quality issues  
**Mitigation:** If import/training fails, fall back to Phase 1 data and investigate

---

## Phase 3: Integration & Automation (1 Month+) 🚀

**Goal:** Turn insights into revenue through campaigns and automation

**Timeline:** 2-4 weeks (iterative)  
**Depends On:** Phase 2 success  
**Owner:** Product + engineering team

### 3a. Connect Track 1 & Track 2 (Week 1)

**Objective:** Use Track 2 segments to retarget new donors from Track 1 lookalikes

**Tasks:**
1. Identify new donors acquired via Track 1 campaigns
2. Run Track 2 inference on these new donors
3. Map segments to campaign strategies:
   - High engagement → nurture/upsell emails
   - Medium engagement → multi-touch campaigns
   - Low engagement → re-engagement sequences
4. Document handoff process

**Success Criteria:**
- [ ] New donors are segmented within 24 hours of acquisition
- [ ] Campaign mapping is clear and documented
- [ ] Personalization is applied in email/SMS

### 3b. Set Up Recurring Runs (Week 1-2)

**Objective:** Automate Track 2 retraining as new data arrives

**Tasks:**
1. Schedule monthly retraining (after new donor data accumulates)
2. Automate batch inference runs
3. Update segment assignments for all donors
4. Document refresh schedule and data dependencies

**Success Criteria:**
- [ ] Monthly retrain schedule is in place
- [ ] Batch inference runs automatically
- [ ] Results update donor segments in CRM
- [ ] Monitoring alerts on failures

### 3c. Build Campaign Workflows (Week 2-3)

**Objective:** Create templated campaigns for each segment

**Tasks:**
1. Develop email/SMS templates for each segment type
2. Create decision trees for multi-touch campaigns
3. Document optimal contact timing (by segment)
4. Set up A/B tests to measure segment-specific lift

**Success Criteria:**
- [ ] Campaigns are live for at least 2 segments
- [ ] Email/SMS templates are mapped to donor segments
- [ ] A/B tests measure impact
- [ ] CRM integration is working

### 3d. Measure & Iterate (Week 3-4+)

**Objective:** Track performance and refine segmentation

**Tasks:**
1. Monitor engagement metrics by segment
2. Calculate lift vs. non-personalized baseline
3. Identify top signals driving engagement
4. Refine model weights based on campaign results
5. Document learnings

**Success Criteria:**
- [ ] Engagement metrics tracked and reported
- [ ] Segment-specific ROI calculated
- [ ] Refinements tested and validated
- [ ] Results shared with stakeholders

### Deliverables

- ✅ Integration documentation (Track 1 ↔ Track 2)
- ✅ Campaign workflow templates
- ✅ Automation scripts/scheduled jobs
- ✅ Performance dashboard (engagement by segment)
- ✅ ROI analysis and learnings
- ✅ Recommendations for next iteration

### Risk Assessment

**Medium-High Risk:** Depends on campaign execution and data pipeline reliability  
**Mitigation:** 
- Phase gate reviews between sub-phases
- Automated monitoring and alerts
- Fallback to manual campaigns if automation fails

---

## Parallel: Track 1 (Acquisition) Status

**Current:** Lookalike audience populating (2-4 hours)  
**Next:** Use lookalike for ad campaigns once READY status confirmed

**Dependency:** No blockers on Track 2; can proceed independently

---

## Success Metrics

### Phase 1 (Validation)
- ✅ Pipeline runs end-to-end without errors
- ✅ Model generates meaningful rankings
- ✅ Segments are created and distinct

### Phase 2 (Scale)
- ✅ Large dataset imports successfully
- ✅ Model quality maintained at 10x scale
- ✅ Patterns are stable and predictable

### Phase 3 (Revenue Impact)
- ✅ New donors are segmented within 24 hours
- ✅ Personalized campaigns show >15% engagement lift
- ✅ Segment-specific ROI is positive
- ✅ Automation runs reliably (>99% uptime)

---

## Timeline Summary

| Phase | Duration | Start | End | Dependency |
|-------|----------|-------|-----|------------|
| **1: Validate** | 1-2 hrs | Now | This week | None |
| **2: Scale** | 2-3 hrs | Next week | Week 2 | Phase 1 ✅ |
| **3: Integrate** | 2-4 weeks | Week 2 | Week 4+ | Phase 2 ✅ |

**Total: ~1 month to full integration**

---

## Critical Path

```
START → Phase 1 Validation ✅
         ↓
         Phase 2 Scale ✅
         ↓
         Phase 3a Connect Tracks
         ↓
         Phase 3b Automation
         ↓
         Phase 3c Campaigns
         ↓
         Phase 3d Measure & Iterate
         ↓
         LIVE REVENUE IMPACT
```

---

## Decisions Needed

- [ ] **Timing:** When should Phase 1 start? (Recommend: this week)
- [ ] **Owner:** Who leads each phase? (Agent vs. human team)
- [ ] **Data:** Use large dataset for Phase 2, or stick with small? (Recommend: large)
- [ ] **Campaigns:** Email-first for Phase 3c, or multi-channel? (Recommend: email + SMS)

---

## Notes

- All phases assume AWS free tier coverage (no cost overruns expected)
- Track 1 can proceed in parallel; no blocker dependencies
- Each phase has clear success criteria for go/no-go decisions
- Documentation and learnings are captured at each phase

---

## Links

- **Current Status:** See `AGENT_START_HERE.md`
- **How to Execute:** See `QUICKSTART.md`
- **Technical Details:** See `PIPELINE_ARCHITECTURE.md`
- **Operations:** See `OPERATIONS_GUIDE.md`
