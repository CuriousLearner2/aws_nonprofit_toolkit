# Automation Experiment Decision: Return to Local Workflow

**Date:** 2026-06-11  
**Status:** Experiment Stopped — Returning to Local Claude Code + GitHub Durable Artifacts Model

---

## Summary

We explored GitHub-based Claude Code automation through GitHub Actions and the `anthropics/claude-code-action` GitHub Action.

The developer-agent automation path proved fragile:
- PR state became difficult to verify reliably
- Claude Code reports and GitHub UI/diff state appeared inconsistent
- Phase 1B will introduce higher risk (schema, persistence, data integrity)
- Adding fragile automation now increases risk more than it reduces cost

**Decision:** Stop GitHub-based Claude developer automation. Return to safer hybrid model.

---

## Final Decision

### Development Model

**Local Claude Code** — Primary developer agent
- Developer pastes prompts into Claude Code (local CLI)
- Claude Code writes code, tests, commits locally
- Developer pushes branches and creates PRs manually
- Human reviews and merges PRs on GitHub

**GitHub** — Source of truth for branches, commits, PRs, durable artifacts
- Branches, commits, and PRs remain human-authored or locally-committed
- No remote Claude automation
- No `@claude` GitHub triggers
- No automated branch/PR creation from GitHub comments
- No automated merges

**ChatGPT** — Planning, architecture review, acceptance reasoning
- ChatGPT writes developer prompts and acceptance criteria
- User pastes ChatGPT output into local Claude Code as instructions
- ChatGPT helps reason about architecture and design before implementation

**GitHub Actions** — Deterministic checks only (future consideration)
- Test runners, linters, guardrail checks
- Read-only verification workflows
- No AI-based decision making
- No branch/PR creation or modification

---

## Why We Stopped

### PR State Inconsistency
- Reports from Claude Code about changes made didn't always match GitHub UI
- Difficult to verify that pushed commits reflected intended changes
- Created uncertainty about what was actually on the remote

### Verification Complexity
- Too many layers: local git state, remote git state, GitHub UI cache, Claude's understanding
- When mismatches occurred, unclear which layer was source of truth
- Manual verification required too much context switching

### Phase 1B Risk
- Phase 1B introduces schema, migrations, persistence, and data integrity
- Higher stakes for correctness and rollback capability
- Fragile automation increases risk of data-state desynchronization
- Simpler workflow reduces cognitive load for complex changes

### Cost/Benefit
- Benefit: Reduced manual branch/PR creation
- Cost: Added complexity, verification burden, debugging difficulty
- Net: Not worth it at this stage

---

## Working Model for Phase 1B

### Workflow

1. **ChatGPT Planning (Async)**
   - ChatGPT writes detailed developer prompts
   - Includes acceptance criteria, test strategy, guardrails
   - Output: compact, clear instructions

2. **Local Claude Code (Interactive)**
   - User copies ChatGPT prompt into Claude Code
   - Claude Code works locally: edits, tests, commits
   - Produces compact summary of changes made
   - User can verify locally before pushing

3. **Local Verification (Optional)**
   - Run full test suite locally
   - Inspect diffs locally
   - Debug any issues locally
   - Push when confident

4. **GitHub PR + Review (Human-Driven)**
   - User pushes branch and creates PR manually
   - GitHub Actions run deterministic checks (tests, guardrails)
   - Human reviews PR on GitHub
   - Human merges PR when approved

5. **Feedback Loop**
   - User shares test results, QA findings, or specific artifacts with ChatGPT
   - ChatGPT provides guidance on fixes or next steps
   - Cycle repeats for next task

### Example Phase 1B Task

```
User → ChatGPT: "Plan Phase 1B Step 1: Add household_id to database schema"
ChatGPT → User: [Detailed prompt with schema design, migration strategy, guardrails]
User → Claude Code: [Pastes prompt]
Claude Code → User: [Makes changes, tests locally, summarizes]
User → GitHub: [Creates PR with changes]
GitHub Actions → GitHub PR: [Test results, guardrail check]
User → Review: [Approves PR changes]
User → ChatGPT: [Shares results/feedback for next step]
```

---

## Things Explicitly Deferred

❌ **anthropics/claude-code-action**  
❌ **@claude GitHub triggers**  
❌ **Remote AI branch/PR creation**  
❌ **Auto-merge workflows**  
❌ **Deployment automation**  

These may be reconsidered after Phase 1B completes and is proven stable.

---

## Implementation Status

| Component | Status | Artifact |
|-----------|--------|----------|
| Phase 1A Service-Boundary Pattern | ✅ Complete | All 8 routes migrated |
| Phase 1A Tests | ✅ Complete | 333 targeted tests passing |
| GitHub Automation Experiment | ⏸ Stopped | PR #4 abandoned (no merge) |
| Phase 1B Planning | ⏳ Next | Persistence boundary + schema proposal |

---

## Next Recommended Project Action

**Do not start Phase 1B implementation yet.**

**Next task: Phase 1B documentation-only planning**

1. Create: `PHASE1B_PERSISTENCE_BOUNDARY_AND_SCHEMA_PROPOSAL.md`
   - Design the database schema (household_id field, relationships, constraints)
   - Define persistence boundary (what data lives in database vs. fixtures)
   - Describe migration strategy (fixtures → database gradual migration)
   - Document schema guardrails (no CRM sync, no writeback, Phase 0 UI preservation)
   - Design acceptance criteria (how to verify schema is correct)

2. No code yet:
   - No database creation
   - No ORM setup
   - No migrations
   - No persistence implementation

3. Review & approval:
   - Share schema proposal with stakeholders
   - Get written acceptance before proceeding to Phase 1B Step 1

4. Then start Phase 1B implementation:
   - Use schema proposal as specification
   - Local Claude Code + local testing + GitHub PR workflow
   - Each step: documentation → schema → tests → implementation

---

## Files

- This decision document: `docs/automation/AUTOMATION_EXPERIMENT_DECISION.md`
- Abandoned PR: `automation/claude-github-workflows` (not merged)
- Phase 1A artifacts: Unchanged and preserved
- Phase 1B start: Not started

---

**Decision Owner:** User  
**Rationale:** Risk reduction for Phase 1B, simpler workflow, better verification  
**Status:** ✅ Decided and documented
