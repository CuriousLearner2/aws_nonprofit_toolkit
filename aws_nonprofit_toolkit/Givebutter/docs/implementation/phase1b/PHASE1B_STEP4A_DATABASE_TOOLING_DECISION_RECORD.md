# Phase 1B-Step 4A: Database Tooling Decision Record

**Date:** 2026-06-11  
**Status:** DECISION RECORD (Documentation Only)  
**Type:** Pre-implementation decision for Phase 1B-Step 4  
**Next Step:** Phase 1B-Step 4 implementation (awaiting approval)

---

## 1. Executive Summary

This is a **documentation-only decision record**. It proposes tooling and strategy for Phase 1B-Step 4 (Database Schema & ORM Models) but does NOT implement any database code.

**Purpose:** Establish consensus on database engine, access layer, migration tool, and raw row storage strategy before Phase 1B-Step 4 implementation begins.

**Scope:** Decision record only. No application code, tests, database code, ORM models, migrations, or configuration changes in this step.

---

## 2. Current Baseline

### Phase 1A: Complete with Remediation
- All 8 canonical DonorTrust routes are service-backed
- `scripts/householder/duplicates_service.py` restored as Phase 1A remediation
- All 8 routes return HTTP 200
- Phase 0 UI preserved (no frontend changes)
- No database, ORM, migrations, persistence, export generation, or CRM writeback exists

### Phase 1B-Step 3: Repository Protocol Accepted
- `scripts/householder/repository_contracts.py` defines `ImportRepositoryProtocol`
- Protocol is read-only (8 methods, no writes)
- Protocol methods: `list_imports()`, `get_dashboard()`, `get_validation()`, `get_normalizations()`, `get_households()`, `get_duplicates()`, `get_audit()`, `get_exports()`
- `tests/unit/test_repository_contracts.py` exists (52 tests)

### Test Baseline
- **Current accepted baseline: 340 tests passing**
  - 136 Phase 1A unit tests
  - 152 Phase 1A integration tests
  - 52 Phase 1B-Step 3 protocol tests
- All 8 DonorTrust routes return 200
- Zero regressions

### Database Implementation Status
- Phase 1B-Step 4 has NOT started
- No SQLAlchemy, Flask-SQLAlchemy, Alembic, or Flask-Migrate
- No migrations, ORM models, or database configuration
- No database-backed repository implementation

---

## 3. Decisions to Make

### A. Database Engine

**Question:** Which database engine should Phase 1B use?

**Options:**

1. **SQLite first** — Local SQLite file for development and CI; schema portable to PostgreSQL later
2. **PostgreSQL first** — Production-like database from the start

**Evaluation:**

| Criterion | SQLite First | PostgreSQL First |
|-----------|---|---|
| Local dev simplicity | ✅ Excellent (no setup) | ⚠️ Requires Docker or local install |
| CI simplicity | ✅ Excellent (file-based) | ⚠️ Requires service container |
| Migration path | ✅ Good (SQL is portable) | ⚠️ Locked in from start |
| Deployment readiness | ⚠️ SQLite not for prod | ✅ Production-ready from start |
| Correctness for import-batch scope | ✅ Sufficient (single batch per request) | ✅ Sufficient (same constraints) |
| Test isolation | ✅ Easy (temp file per test) | ⚠️ More complex (transaction rollback) |

**Recommendation:**

✅ **SQLite first for Phase 1B local development and CI.**

Rationale:
- Zero friction for local development (no setup, no container)
- CI simplicity (file-based, no service containers)
- Current scope (import-batch review, single request) does not require PostgreSQL
- Schema can remain portable: use standard SQL, avoid SQLite-specific features
- If future phases require multi-tenant or concurrent production use, migration to PostgreSQL is straightforward with standard SQL schema

---

### B. Database Access Layer

**Question:** How should application code interact with the database?

**Options:**

1. **SQLAlchemy ORM** — Object-relational mapper with declarative models
2. **SQLAlchemy Core** — SQL expression language without full ORM
3. **Raw SQL** — Direct SQL with query builders or string literals

**Evaluation:**

| Criterion | SQLAlchemy ORM | SQLAlchemy Core | Raw SQL |
|-----------|---|---|---|
| Maintainability | ✅ Good (clear relationships) | ✅ Good (explicit SQL) | ⚠️ Error-prone (string concat) |
| Testability | ⚠️ Tricky (ORM state) | ✅ Good (queries are data) | ✅ Good (fixtures) |
| ORM object leakage risk | 🚨 HIGH (models flow into templates) | ✅ LOW (core returns dicts) | ✅ LOW (no models) |
| Repository pattern fit | ⚠️ Medium (must not expose models) | ✅ High (returns dicts/tuples) | ✅ High (returns dicts) |
| Learning curve | ⚠️ Medium (relationships, sessions) | ✅ Low (SQL-like) | ⚠️ High (escaping, types) |

**Recommendation:**

✅ **SQLAlchemy is allowed ONLY inside database/repository layer.**

Constraints:
- SQLAlchemy ORM models stay in `scripts/householder/database_models.py` (or similar)
- Repository layer (`DatabaseImportRepository`) translates ORM objects → frozen view models
- ORM objects NEVER returned from repository methods
- Repository ALWAYS returns frozen Phase 1A view models (from `service_contracts.py`)
- Services, routes, and templates see only view models, never ORM objects

Rationale:
- ORM provides good schema clarity and relationship expressiveness
- Translation layer at repository boundary prevents model leakage
- Frozen view models remain the contract
- Tests can mock repository without touching ORM

---

### C. Migration Tool

**Question:** How should database schema versions and migrations be managed?

**Options:**

1. **Flask-Migrate/Alembic** — Automatic migration generation with Alembic
2. **Alembic directly** — No Flask wrapper, raw Alembic
3. **Plain SQL migration files** — Manual SQL files with version ordering

**Evaluation:**

| Criterion | Flask-Migrate | Alembic Only | Plain SQL |
|-----------|---|---|---|
| Simplicity | ✅ Good (Flask integration) | ⚠️ Medium (extra config) | ✅ Good (no tool setup) |
| Reversibility | ✅ Full (down migrations) | ✅ Full (down migrations) | ⚠️ Manual (error-prone) |
| Alignment with Flask | ✅ Native Flask integration | ⚠️ Separate tool | ⚠️ Completely manual |
| Future maintainability | ✅ Good (standard tool) | ✅ Good (standard tool) | ⚠️ Custom logic |
| Learning curve | ✅ Low (Flask patterns) | ⚠️ Medium (Alembic itself) | ⚠️ Medium (SQL discipline) |

**Recommendation:**

✅ **Use Flask-Migrate (which uses Alembic) for Phase 1B-Step 4 IF APPROVED.**

Constraints:
- No migration files created in this decision step
- Flask-Migrate/Alembic added as dependencies only in Phase 1B-Step 4 after explicit approval
- All migrations stored in `alembic/versions/` following Flask-Migrate conventions
- Each migration has clear up/down paths
- Migrations are reversible (critical for test isolation)

Rationale:
- Standard Flask pattern (uses Alembic under the hood)
- Automatic migration generation reduces manual error
- Down migrations enable test cleanup
- Clear version tracking for CI/CD

---

### D. Raw Row Storage Strategy

**Question:** How should CSV raw data be stored and accessed?

**Options:**

1. **JSON-only raw row storage** — Store CSV row as JSON blob, no denormalized contact columns
2. **Normalized columns only** — Parse CSV, store as separate contact/address/phone columns, no raw data
3. **Immutable JSON raw row + denormalized contact snapshot** — Store raw CSV as JSON AND denormalized contact columns for efficient queries

**Evaluation:**

| Criterion | JSON Only | Normalized Only | JSON + Normalized |
|-----------|---|---|---|
| Raw data preservation | ✅ Perfect (100% fidelity) | ⚠️ Lost (parsed away) | ✅ Perfect (JSON preserved) |
| Query efficiency | ⚠️ Slow (JSON searches) | ✅ Fast (indexed columns) | ✅ Fast (columns indexed) |
| Audit trail | ✅ Complete (original CSV) | ⚠️ Lossy (normalized values) | ✅ Complete (raw + values) |
| Review workflow support | ⚠️ Slow (must parse per request) | ⚠️ Missing context | ✅ Good (fast + raw context) |
| Storage efficiency | ✅ Small (one JSON) | ✅ Small (columns) | ⚠️ Larger (duplication) |
| Immutability guarantee | ✅ Easy (single blob) | ⚠️ Harder (many columns) | ✅ Easy (both immutable) |

**Recommendation:**

✅ **Store raw CSV row as immutable JSON in `raw_import_rows` AND use `import_contacts` as immutable denormalized contact snapshot.**

Rationale:
- Preserves 100% original data in JSON (audit trail, review context, error recovery)
- Denormalized contact columns enable efficient route queries (validation findings, normalization suggestions, household matches, duplicate detection)
- Both tables immutable after row creation (Phase 1B-Step 4 should never modify)
- Route performance is good (no JSON parsing per request)
- Future cross-import matching can reference `import_contacts` efficiently

**Schema outline (Phase 1B-Step 4 will detail):**

```
import_batches
  ├─ id (PK)
  ├─ filename
  ├─ upload_timestamp
  └─ ...metadata

raw_import_rows
  ├─ id (PK)
  ├─ batch_id (FK)
  ├─ row_index
  ├─ raw_csv_data (JSON, immutable)
  └─ import_timestamp

import_contacts
  ├─ id (PK)
  ├─ batch_id (FK)
  ├─ raw_import_row_id (FK)
  ├─ first_name
  ├─ last_name
  ├─ email
  ├─ phone
  ├─ address_line1
  ├─ ...normalized fields
  └─ created_timestamp (immutable)

review_decisions  [Phase 1B-Step 6]
  ├─ id (PK)
  ├─ batch_id (FK)
  ├─ contact_id (FK)
  ├─ decision_type (validation, normalization, household, duplicate)
  ├─ decision_value
  └─ created_timestamp
```

---

### E. Initial Phase 1B-Step 4 Implementation Scope

**Question:** What should Phase 1B-Step 4 actually implement?

**Options:**

1. **Schema/migrations/models only** — Define database schema, create migrations, define ORM models; no repository implementation
2. **Schema + seed data** — Schema/migrations/models + fixture import batches for testing
3. **Schema + first repository** — Full schema + new `DatabaseImportRepository` implementation
4. **Full database repository** — Complete swap from fixture to database; all routes tested with DB backend

**Evaluation:**

| Scope | Risk | Reversibility | Test Complexity | Review Load |
|-------|------|---|---|---|
| Schema/migrations/models | ✅ Low (structure only) | ✅ High (migrations reversible) | ✅ Low (schema tests) | ✅ Low (decision boundary) |
| + Seed data | ⚠️ Medium (fixtures needed) | ⚠️ Medium (clean fixtures) | ⚠️ Medium (fixture tests) | ⚠️ Medium (data needed) |
| + First repository | 🚨 High (behavior change) | ⚠️ Medium (can revert) | 🚨 High (parity tests) | 🚨 High (complete swap) |
| Full database repository | 🚨 Critical (full migration) | ⚠️ Low (hard to revert) | 🚨 Critical (all routes) | 🚨 Critical (all routes) |

**Recommendation:**

✅ **Phase 1B-Step 4 should create schema/migrations/models only.**

Rationale:
- Low risk (structure only, no behavior change)
- High reversibility (migrations can roll back)
- Allows review of schema design before repository implementation
- No repository swap in Step 4; fixture repository remains active
- Tests can verify schema structure, not behavior
- Future steps (Step 5, Step 6) handle repository implementation and migration

**Future phase plan:**
- **Step 4:** Schema + migrations + ORM models (this step)
- **Step 5:** Create `DatabaseImportRepository`; add parity tests (fixture vs database)
- **Step 6:** Consider switching default repository (decision to be made at that time)

---

## 4. Non-Negotiable Guardrails

These constraints MUST hold throughout all Phase 1B steps:

### Data Immutability
- ✅ Raw import rows immutable after creation
- ✅ Import contacts immutable after creation
- ✅ Raw CSV data preserved as-is in JSON
- ✅ No retroactive normalization of source data
- ✅ No automatic household grouping

### Decision Recording & Review
- ✅ Reviewer decisions stored separately from raw data
- ✅ No automatic normalization approval (user must confirm)
- ✅ No automatic duplicate resolution; reviewer must explicitly mark same-person or different-person treatment for export staging
- ✅ No automatic household confirmation (user must group)
- ✅ Decisions created only via explicit user review actions (Phase 1B-Step 6+)

### Scope Boundaries
- ✅ Current import batch only (no cross-import matching in Phase 1B)
- ✅ No Givebutter or CRM writeback
- ✅ No real export file generation (metadata-only in Phase 1B)
- ✅ No frontend JavaScript runtime (Flask templates only)

### Architecture Preservation
- ✅ Routes remain service-backed
- ✅ Services remain repository-backed
- ✅ Repository contract (`ImportRepositoryProtocol`) unchanged
- ✅ Repository always returns frozen view models, never ORM objects
- ✅ Templates unchanged (view model shapes preserved)
- ✅ Flask remains the only app server

---

## 5. Proposed Phase 1B-Step 4 Scope (If Approved)

### Allowed in Phase 1B-Step 4

After this decision is accepted, Phase 1B-Step 4 implementation may:

- ✅ Add database dependencies to `pyproject.toml` or `requirements.txt` (Flask-SQLAlchemy, SQLAlchemy, Flask-Migrate)
- ✅ Create SQLAlchemy ORM model classes (e.g., `ImportBatch`, `RawImportRow`, `ImportContact`)
- ✅ Create database initialization code (e.g., `init_db()` function)
- ✅ Create Alembic migration configuration and initial migration files
- ✅ Create schema-only tests (verify table structure, columns, constraints)
- ✅ Create database configuration (e.g., SQLite connection string for dev/test)
- ✅ Create seed data loading for tests (optional)

### NOT Allowed in Phase 1B-Step 4

- ❌ No route handler changes
- ❌ No service function changes
- ❌ No template or UI changes
- ❌ No repository implementation (no `DatabaseImportRepository`)
- ❌ No write/decision APIs (Phase 1B-Step 6)
- ❌ No repository swap (fixture repository still active)
- ❌ No real export file generation
- ❌ No Givebutter/CRM integration
- ❌ No cross-import matching logic

### Expected Deliverables for Phase 1B-Step 4

If approved:

1. `scripts/householder/database_models.py` — SQLAlchemy ORM model definitions
2. `alembic/` directory — Alembic configuration and migrations
3. `alembic/versions/0001_initial_schema.py` — Initial migration
4. `scripts/householder/database_init.py` — Database initialization function
5. `tests/unit/test_database_models.py` — Schema structure tests
6. Updated `pyproject.toml` or `requirements.txt` with database dependencies
7. `PHASE1B_STEP4_COMPLETION_RECORD.md` — Implementation record

---

## 6. Acceptance Criteria for This Decision Record

This decision record is acceptable if:

✅ Documentation-only (no implementation)  
✅ Makes clear tooling recommendations for each decision  
✅ Does not add application code, tests, or database code  
✅ Does not modify routes, services, or templates  
✅ Does not create ORM models, migrations, or configuration  
✅ Preserves all Phase 1A and Phase 1B-Step 3 guardrails  
✅ Defines a narrow, reversible Phase 1B-Step 4 scope  
✅ Clarifies what is in-scope vs out-of-scope for Step 4  
✅ Identifies open questions for Step 4 approval  

---

## 7. Open Questions for Phase 1B-Step 4 Approval

Before Phase 1B-Step 4 implementation begins, these questions should be resolved:

### Dependency Management
- **Q1:** Should database dependencies be added to `pyproject.toml` and committed, or discussed separately before Step 4?
  - Current guidance: Allowed in Step 4 if approved

### Test Database Strategy
- **Q2:** Should Step 4 tests use in-memory SQLite (`:memory:`) or temporary file-based SQLite?
  - In-memory pros: Fast, no temp files
  - Temp file pros: Debugging, can inspect with sqlite3 CLI
  - Current guidance: Temp file recommended for debuggability

### ORM Framework Choice
- **Q3:** Should models be pure SQLAlchemy declarative models or Flask-SQLAlchemy models?
  - Pure SQLAlchemy pros: No Flask coupling
  - Flask-SQLAlchemy pros: Flask integration
  - Current guidance: Recommend pure SQLAlchemy (less coupling)

### Migration Strategy
- **Q4:** Should migrations be auto-generated or hand-written?
  - Auto-generated: `alembic revision --autogenerate`
  - Hand-written: Manual control, safer
  - Current guidance: Can use auto-generate if careful review before commit

### Model Relationships
- **Q5:** Should ORM models define relationships (e.g., `ImportBatch.raw_rows`), or stay flat?
  - Relationships pros: Convenience
  - Flat pros: Simpler, no lazy-loading issues
  - Current guidance: Flat is safer for this phase

### Fixture Data
- **Q6:** Should Step 4 include seed data (e.g., test import batch with sample contacts) or leave to Step 5?
  - Current guidance: Optional in Step 4; required before Step 5 tests

---

## 8. Decision Sign-Off

This decision record establishes tooling consensus for Phase 1B-Step 4 implementation.

**Decisions Made:**
- ✅ Database engine: **SQLite first** (portable schema, easy local dev/CI)
- ✅ DB access layer: **SQLAlchemy ORM** (inside repository layer only, never exposed)
- ✅ Migration tool: **Flask-Migrate/Alembic** (standard Flask pattern)
- ✅ Raw row storage: **Immutable JSON + denormalized contact snapshot** (preservation + efficiency)
- ✅ Step 4 scope: **Schema/migrations/models only** (low risk, reversible, high-quality review)

**Guardrails Reaffirmed:**
- ✅ Raw data immutable
- ✅ Decisions stored separately
- ✅ No automatic approvals
- ✅ Current batch only
- ✅ No Givebutter/CRM writeback
- ✅ No real export generation
- ✅ Flask-only, no frontend runtime

**Next Step:**
Phase 1B-Step 4 implementation may begin once this decision record is approved.

---

**Document Status:** ✅ DECISION RECORD COMPLETE  
**Implementation Status:** Not started (awaiting approval)  
**Code Changes:** None  
**Test Changes:** None  
**Database Code Added:** None  

---

**Completion Date:** 2026-06-11  
**Related to:** Phase 1B-Step 4 implementation planning  
**Approved by:** [Pending user approval]  
**Next document:** PHASE1B_STEP4_COMPLETION_RECORD.md (after implementation)
