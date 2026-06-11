# DonorTrust v1 Implementation Guide

**Current Status:** Phase 0 FULLY ACCEPTED ✓ | Phase 1A Planning COMPLETE

---

## Phase Status

### Phase 0: Clickable Prototype (ACCEPTED)

Phase 0 delivered a **fixture-backed clickable prototype** with all 8 DonorTrust screens fully functional:

- ✓ Imports list
- ✓ Import dashboard
- ✓ Possible duplicates review
- ✓ Validation review (10-column table)
- ✓ Normalizations review
- ✓ Households review
- ✓ Audit log
- ✓ Export console

**Documentation:** See `docs/completion-records/phase0/PHASE0_ACCEPTANCE_RECORD.md`

**QA Artifacts:** `testing/qa-artifacts/phase0/`

### Phase 1A: Service-Boundary Planning (CURRENT)

Phase 1A is **planning-only**. It defines incremental backend architecture without implementing persistence.

**Documentation:** See `docs/completion-records/phase1a/PHASE1A_SERVICE_BOUNDARY_PLAN.md`

**Status:** Phase 1A-Step 1 completed and accepted. Phase 1A-Step 2 awaiting approval.

---

## Architecture Constraints (All Phases)

These constraints apply to Phase 0 and all future phases:

### Server
- ✓ **Existing Flask app only** (`scripts/uploader/app.py`)
- ✗ No separate frontend runtime
- ✗ No Node.js, Express, or other backend

### Frontend
- ✓ **Server-rendered Jinja2 templates**
- ✓ **Shared CSS** (`donortrust.css`)
- ✓ **Minimal vanilla JavaScript** (no libraries)
- ✗ No React, Vue, Angular, Svelte, or SPA framework
- ✗ No npm, Webpack, Vite, Rollup, or build tooling
- ✗ No TypeScript, Babel, or transpilers

### Data
- ✓ **Phase 0:** Fixture data only
- ✓ **Phase 1A:** Service boundary planning (no persistence)
- ✓ **Phase 1B+:** Optional SQLite or PostgreSQL (when approved)
- ✗ No ORM objects exposed to templates
- ✗ No Givebutter/CRM integration until Phase 3+

---

## Source-of-Truth Hierarchy

For implementation decisions, consult in this order:

1. **Householder PRD v2.6 (UX-aligned)** — product contract
2. **UX_SUMMARY.md** — canonical 8-screen workflow
3. **Phase 0 Acceptance Record** — prototype specification
4. **Accepted screen specs** — visible UI and copy requirements
5. **PHASE1A_SERVICE_BOUNDARY_PLAN.md** — architectural direction
6. **ADAPTATION_DOCUMENT-v2.6** — repository constraints

---

## Recommended Next Step: Phase 1A-Step-1

After Phase 1A planning is approved, implement:

**Import List Route Migration**

- Create `scripts/householder/service_contracts.py` (view models)
- Create `scripts/householder/fixture_repository.py` (fixture provider)
- Create `scripts/householder/import_service.py` (service function)
- Migrate `/imports` route to use service layer
- Verify Phase 0 QA still passes

**Size:** ~300-400 lines of code | **Risk:** Low | **Time:** 2-4 hours

**Not yet approved.** Requires explicit approval before implementation.

---

## Key Files

### Core Implementation
- `scripts/uploader/app.py` — Flask routes (8 new routes added in Phase 0)
- `scripts/uploader/fixtures.py` — mock data
- `scripts/uploader/templates/` — 8 Jinja2 screens
- `scripts/uploader/static/css/donortrust.css` — styling
- `scripts/uploader/static/js/donortrust-interactions.js` — interactions

### Documentation
- `docs/ux/UX_SUMMARY.md` — canonical workflow
- `docs/completion-records/phase0/PHASE0_ACCEPTANCE_RECORD.md` — Phase 0 final spec
- `docs/completion-records/phase1a/PHASE1A_SERVICE_BOUNDARY_PLAN.md` — Phase 1A direction
- `docs/completion-records/phase1a/PHASE1A_STEP1_COMPLETION_RECORD.md` — Phase 1A-Step 1 sign-off
- `docs/PRDs/Householder/Householder_PRD-v2.6-UX-aligned.md` — product spec
- `docs/PRDs/Implementation/HOUSEHOLDER_IMPLEMENTATION_PLAN-v2.6-UX-aligned.md` — sequencing

---

## How to Run Phase 0

```bash
cd scripts/uploader
python3 app.py
```

Then visit: http://127.0.0.1:8000/imports

All 8 screens load with fixture data. No database required.

---

## Important Constraints for All Developers

Before implementing any feature:

1. **Check the Phase 0 Acceptance Record** — don't change accepted UI
2. **Follow the service-boundary plan** — create contracts first, implementation second
3. **Preserve Flask-only architecture** — no new app servers
4. **Keep templates plain** — no ORM objects
5. **Use vanilla JS only** — no frameworks
6. **Enforce safe vocabulary** — no merge/sync/auto-*/approve-all/CRM-writeback
7. **Preserve audit trail copy** — all decisions are logged

---

## When to Escalate

Escalate to product before implementation if:

- You want to change an accepted Phase 0 screen or route
- You want to add a new route not in the 8-screen spec
- You want to change the architecture (Flask → other, add frameworks, etc.)
- You want to add external integrations (Givebutter, CRM, etc.)
- You're unsure about source-of-truth documentation

---

## Status of Each Phase

| Phase | Status | Duration | Deliverable |
|---|---|---|---|
| Phase 0 | ✓ ACCEPTED | Complete | Fixture-backed prototype |
| Phase 1A-Step 1 | ✓ ACCEPTED | Complete | Service boundary for /imports route |
| Phase 1A-Step 2+ | ⏳ PLANNED | TBD | Additional route migrations (dashboard, etc.) |
| Phase 1B | ⏳ DEFERRED | TBD | SQLite backend + decision persistence |
| Phase 2 | ⏳ DEFERRED | TBD | Authentication + authorization |
| Phase 3+ | ⏳ DEFERRED | TBD | Givebutter integration, exports, etc. |

---

**Last updated:** 2026-06-11  
**Next review:** After Phase 1A-Step-1 approval and implementation
