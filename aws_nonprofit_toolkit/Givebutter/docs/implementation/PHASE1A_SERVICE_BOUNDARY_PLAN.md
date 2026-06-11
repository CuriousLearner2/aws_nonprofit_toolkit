# Phase 1A Service-Boundary Plan — DonorTrust v1

**Status:** Phase 1A-Steps 1-4 complete (✓ /imports, ✓ /dashboard, ✓ /validation, ✓ /normalizations); Steps 5-8 pending (duplicates, households, audit, exports)

**Purpose:** Define incremental backend architecture path from fixture-backed prototype to service-backed screens.

---

## 1. Purpose of Phase 1A

Phase 1A establishes **service boundaries and data contracts** so that screens can be migrated from fixture-backed to backend-backed **one route at a time** without:

- Rewriting Jinja templates
- Changing accepted Phase 0 UI
- Introducing database persistence
- Adding external system integrations
- Violating safety constraints

Phase 1A creates the **architectural foundation** for Phase 1B (real database) and beyond while keeping the prototype **fully functional and testable** during development.

**Key insight:** Templates should not care whether data comes from fixtures, files, a database, or an API. Service boundaries hide this implementation detail.

---

## 2. Non-Goals of Phase 1A

Phase 1A **explicitly will NOT**:

- [ ] Implement full database schema or migrations
- [ ] Implement real duplicate detection algorithm
- [ ] Implement real field normalization engine
- [ ] Implement real household grouping algorithm
- [ ] Build export file generation or formatting
- [ ] Integrate with Givebutter API or CRM systems
- [ ] Support cross-import batch matching or householding
- [ ] Persist reviewer decisions to database or file
- [ ] Change any accepted Phase 0 screens or routes
- [ ] Introduce React, Vue, Angular, Svelte, or any SPA framework
- [ ] Introduce a separate frontend app server
- [ ] Add npm, Webpack, Vite, or other build tooling
- [ ] Modify existing uploader routes or functionality

---

## 3. Phase 0 UI Must Be Preserved

Phase 1A MUST preserve every accepted Phase 0 element:

- **All 8 routes** remain unchanged
- **All 8 screens** look and function identically
- **Desktop layout** (1280px max-width, responsive design)
- **All visible copy and safety messaging**
- **All interactions** (modals, row selection, button states, form validation)
- **Flask-only server architecture**
- **Jinja2 template rendering**
- **Shared CSS**
- **Vanilla JavaScript interactions**

**Verification:** Existing Phase 0 QA suite should pass without modification during Phase 1A implementation.

---

## 4. Proposed Service-Layer Architecture

After Phase 1A planning, the codebase will be organized to support incremental migration:

```
scripts/householder/
├── __init__.py
├── service_contracts.py          (data contracts / view models)
├── fixture_repository.py          (fixture data provider)
├── import_service.py              (orchestrates data for /imports)
├── dashboard_service.py           (orchestrates data for /dashboard)
├── validation_service.py          (orchestrates data for /validation)
├── duplicate_service.py           (orchestrates data for /duplicates)
├── normalization_service.py       (orchestrates data for /normalizations)
├── household_service.py           (orchestrates data for /households)
├── audit_service.py               (orchestrates data for /audit)
└── export_service.py              (orchestrates data for /exports)
```

**Key principle:** Each service module returns **plain data structures** (dicts, dataclasses, or TypedDicts), not ORM objects. Templates remain decoupled from persistence layer.

---

## 5. Contract-First Data Approach

Each screen is backed by a service function that defines a **contract** (input/output shape). Service functions currently return fixture-shaped data; later they can return database data without changing templates.

### Proposed service function signatures:

```python
# Import list screen
def get_imports(
    offset: int = 0,
    limit: int = 20,
) -> list[ImportSummary]

# Dashboard screen
def get_import_dashboard(
    import_id: str,
) -> ImportDashboardViewModel

# Validation review screen
def get_validation_review(
    import_id: str,
    filters: dict | None = None,  # future: allow status filter
) -> ValidationReviewViewModel

# Duplicate review screen (single candidate)
def get_duplicate_review(
    import_id: str,
    candidate_id: str | None = None,  # if None, return first
) -> DuplicateReviewViewModel

# Normalization review screen (single suggestion)
def get_normalization_review(
    import_id: str,
    suggestion_id: str | None = None,  # if None, return first
) -> NormalizationReviewViewModel

# Household review screen (single suggestion)
def get_household_review(
    import_id: str,
    suggestion_id: str | None = None,  # if None, return first
) -> HouseholdReviewViewModel

# Audit log screen
def get_audit_log(
    import_id: str,
    filters: dict | None = None,  # future: allow action type filter
) -> AuditLogViewModel

# Export console screen
def get_export_console(
    import_id: str,
) -> ExportConsoleViewModel
```

---

## 6. View Model Definitions

Templates must receive **clean view models**, not ORM objects. View models are plain dataclasses or TypedDicts.

### Proposed view-model types:

```python
# Data shape for /imports screen
@dataclass
class ImportSummary:
    id: str
    filename: str
    uploaded_at: str  # ISO format or relative time
    record_count: int
    status: str  # e.g., "In Review", "Pending Export", "Exported"
    progress: int  # 0-100

# Data shape for /dashboard screen
@dataclass
class ImportDashboardViewModel:
    batch: ImportBatch
    queue_status: QueueStatus

@dataclass
class ImportBatch:
    id: str
    filename: str
    progress: int  # 0-100

@dataclass
class QueueStatus:
    duplicates_pending: int
    validation_issues: int
    normalizations_pending: int
    households_pending: int

# Data shape for /validation screen
@dataclass
class ValidationReviewViewModel:
    batch: ImportBatch
    validation_issues: list[ValidationRow]
    queue_status: QueueStatus
    total_records: int

@dataclass
class ValidationRow:
    id: str
    date: str
    name: str
    email: str
    phone: str
    amount: str
    address: str
    issue_type: str | None  # "missing-required", "format-invalid", etc.
    issue_description: str | None

# Data shape for /duplicates screen
@dataclass
class DuplicateReviewViewModel:
    batch: ImportBatch
    candidate: DuplicateCandidateViewModel

@dataclass
class DuplicateCandidateViewModel:
    id: str
    contact_a: ContactInfo
    contact_b: ContactInfo
    supporting_evidence: list[str]
    conflicting_evidence: list[str]

@dataclass
class ContactInfo:
    id: str
    name: str
    email: str
    phone: str
    address: str

# Data shape for /normalizations screen
@dataclass
class NormalizationReviewViewModel:
    batch: ImportBatch
    current_suggestion: NormalizationSuggestionViewModel | None
    current_suggestion_index: int
    total_suggestions: int

@dataclass
class NormalizationSuggestionViewModel:
    id: str
    contact_name: str
    field_name: str
    original_value: str
    suggested_value: str
    normalization_type: str

# Data shape for /households screen
@dataclass
class HouseholdReviewViewModel:
    batch: ImportBatch
    current_household: HouseholdSuggestionViewModel | None
    current_household_index: int
    total_households: int

@dataclass
class HouseholdSuggestionViewModel:
    id: str
    suggested_name: str
    address: str
    confidence: str  # e.g., "98%"
    proposed_members: list[str]
    evidence: list[str]
    conflicts: list[str]

# Data shape for /audit screen
@dataclass
class AuditLogViewModel:
    batch: ImportBatch
    audit_log: list[AuditEntryViewModel]

@dataclass
class AuditEntryViewModel:
    timestamp: str  # ISO format or relative time
    reviewer: str
    action: str  # e.g., "marked-duplicate", "confirmed-household"
    details: str
    status: str  # e.g., "Validation Passed", "Needs Review"

# Data shape for /exports screen
@dataclass
class ExportConsoleViewModel:
    batch: ImportBatch
    export_options: list[ExportCardViewModel]
    staged_record_count: int
    total_decisions: int
    household_count: int
    recent_exports: list[ExportHistoryEntryViewModel]

@dataclass
class ExportCardViewModel:
    title: str
    description: str
    key: str  # for identifying which export type
    format_options: list[str] | None

@dataclass
class ExportHistoryEntryViewModel:
    filename: str
    export_type: str
    generated_timestamp: str
    file_size: str
    id: str
```

---

## 7. Fixture Adapter / Repository Pattern

To avoid rewriting templates during backend migration, Phase 1A introduces a **fixture adapter** that serves fixture data through the same service interface.

### Suggested module: `fixture_repository.py`

```python
class FixtureRepository:
    """Serves fixture data. Can be swapped for SQLiteRepository later."""

    def get_imports(self, offset: int = 0, limit: int = 20) -> list[ImportSummary]:
        """Return fixture import list."""
        return self._load_imports_fixture()

    def get_import_dashboard(self, import_id: str) -> ImportDashboardViewModel:
        """Return fixture dashboard data."""
        return self._load_dashboard_fixture(import_id)

    # ... more methods for each service function
```

**Purpose:**
- Keeps templates and routes stable
- Allows backend to be built "behind the scenes"
- Enables one-screen-at-a-time migration
- Maintains Phase 0 QA compatibility

---

## 8. Repository Abstraction for Future Persistence

Phase 1A does not implement persistence, but it plans the abstraction:

```python
class Repository(ABC):
    """Abstract base. Implementations: FixtureRepository, SQLiteRepository, etc."""

    @abstractmethod
    def get_imports(self, offset: int = 0, limit: int = 20) -> list[ImportSummary]:
        pass

    @abstractmethod
    def get_import_dashboard(self, import_id: str) -> ImportDashboardViewModel:
        pass

    # ... more abstract methods
```

**Why:**
- Routes and services never directly depend on persistence implementation
- Swapping FixtureRepository for SQLiteRepository requires no template or route changes
- Testing remains fixture-friendly even after database is added

---

## 9. Safety Boundaries That Must Be Preserved

Phase 1A must enforce these constraints in every service function:

### Raw import rows are immutable
- Services never modify or persist the original CSV/import data
- All changes affect only **export staging**, not raw records

### Current import batch only
- Services always operate within a single import batch context
- No cross-batch matching or householding in Phase 1A

### No automatic operations
- No "Auto-apply all suggestions"
- No "Approve all duplicates"
- No "Sync with CRM"
- Every decision must be explicit, human-made, and logged

### No external integrations
- Services do not call Givebutter API
- Services do not write to external CRM or database
- Services do not sync with Stitch, Zapier, or any external system

### Decisions must be audit-logged
- Once persistence is added, every reviewer decision must be logged with timestamp, reviewer, action, and context
- Audit log is immutable reference of what happened

---

## 10. Route-by-Route Migration Strategy

Routes should be migrated in this preferred sequence:

| Order | Route | Reason |
|---|---|---|
| 1 | `/imports` | Simplest; no import_id parameter |
| 2 | `/imports/<import_id>/dashboard` | Quick win; returns aggregate counts |
| 3 | `/imports/<import_id>/validation` | Complex table but no user input processing |
| 4 | `/imports/<import_id>/duplicates` | Medium complexity; single-item view |
| 5 | `/imports/<import_id>/normalizations` | Single-item pagination pattern |
| 6 | `/imports/<import_id>/households` | Single-item with modal |
| 7 | `/imports/<import_id>/audit` | Read-only, large list |
| 8 | `/imports/<import_id>/exports` | No data persistence needed |

**For each route migration:**

1. Create corresponding service function with contract
2. Create view model dataclass or TypedDict
3. Update route to call service instead of using fixtures directly
4. Verify rendered HTML is **identical** to before
5. Run Phase 0 QA smoke test on that route
6. Commit and document in Phase 1A changelog

---

## 11. First Implementation Candidate: `/imports` Route

After Phase 1A planning is approved, the recommended first implementation step is the smallest safe unit of work:

### Phase 1A-Step-1: Import List Route Migration

```
Goal: Migrate /imports route from fixture to service layer
      without changing UI or breaking Phase 0 QA.

Changes:
  1. Create scripts/householder/__init__.py
  2. Create scripts/householder/service_contracts.py with view models
  3. Create scripts/householder/fixture_repository.py
  4. Create scripts/householder/import_service.py with get_imports()
  5. Update scripts/uploader/app.py @app.route('/imports') to use service
  6. Add smoke test: route returns 200 and renders identically
  7. Verify existing Phase 0 QA still passes

Size: ~300-400 lines of code (mostly type definitions)
Risk: Low (no UI change, no persistence, single route)
Verification: Phase 0 QA still passes, route rendering unchanged
```

**This is NOT approved.** It is recommended as the next step after Phase 1A planning is accepted.

---

## 12. Phase 1A Acceptance Criteria

Phase 1A will be considered complete when all of the following are true:

- [ ] `scripts/householder/` directory structure created
- [ ] `service_contracts.py` defines all view models (dataclasses or TypedDicts)
- [ ] `fixture_repository.py` can serve all fixture data through service interface
- [ ] At least one service module (e.g., `import_service.py`) implemented
- [ ] At least one route (e.g., `/imports`) migrated to use service layer
- [ ] Migrated route renders **identically** to Phase 0 (pixel-perfect HTML match)
- [ ] No database schema, migrations, or persistence added
- [ ] No ORM objects exposed to templates
- [ ] Existing uploader routes still work
- [ ] Phase 0 QA suite still passes without modification
- [ ] Documentation updated with service boundary definitions
- [ ] Next steps clearly documented for Phase 1B (database implementation)

---

## 13. Relationship to Phase 1B and Beyond

After Phase 1A, Phase 1B will:

- Create SQLite schema for imports, contacts, suggestions, decisions, audit log
- Implement `sqlite_repository.py` with same abstract interface as `fixture_repository.py`
- Swap repository implementations (no route/template changes)
- Begin recording actual reviewer decisions to database
- Preserve all Phase 0 and Phase 1A UI unchanged

---

## 14. Documentation to Be Created in Phase 1A

- [ ] `scripts/householder/README.md` — service module overview
- [ ] `scripts/householder/service_contracts.py` docstrings — view model documentation
- [ ] `docs/implementation/PHASE1A_COMPLETION_REPORT.md` — Phase 1A final status
- [ ] `docs/architecture/SERVICE_BOUNDARIES.md` — detailed service interface definitions
- [ ] Route-specific migration guides for Phase 1B

---

## 15. Known Unknowns and Deferred Decisions

The following decisions are **intentionally deferred** pending Phase 1A completion:

| Decision | Why Deferred | Will Be Decided In |
|---|---|---|
| SQLite vs PostgreSQL vs other database | No persistence needed yet | Phase 1B planning |
| Whether to use ORM or raw SQL | No persistence needed yet | Phase 1B planning |
| Reviewer authentication/authorization | No persistence needed yet | Phase 2 planning |
| Suggestion engine algorithms | Real data needed first | Phase 1B+ planning |
| Export file format and generation | Data persistence needed first | Phase 2 planning |
| Givebutter integration | Business logic needed first | Phase 3+ planning |

---

## Appendix A: Source-of-Truth References

For Phase 1A implementation decisions, consult this hierarchy:

1. **Householder PRD v2.6 (UX-aligned)** — product/backend contract
2. **UX_SUMMARY.md** — canonical 8-screen workflow
3. **Phase 0 Acceptance Record** — accepted prototype specification
4. **Accepted screen specs** — detailed visible UI and copy requirements
5. **ADAPTATION_DOCUMENT** — repository reality and constraints
6. **HOUSEHOLDER_IMPLEMENTATION_PLAN-v2.6** — implementation sequencing

Conflicts should be resolved by escalating to product before implementation.

---

## Appendix B: Phase 1A Does NOT Require

Phase 1A planning intentionally does NOT require:

- ❌ Database schema design
- ❌ Data migration planning
- ❌ Reviewer authentication design
- ❌ Suggestion engine design
- ❌ Export format specification
- ❌ Givebutter API design
- ❌ Performance optimization analysis
- ❌ Load testing or scaling analysis

These are Phase 1B+, Phase 2, Phase 3+ concerns.

---

**Status:** Ready for Phase 1A Planning Review

**Next action:** Approval to proceed with Phase 1A-Step-1 implementation (Import List route migration).

**Do NOT proceed without explicit approval.**
