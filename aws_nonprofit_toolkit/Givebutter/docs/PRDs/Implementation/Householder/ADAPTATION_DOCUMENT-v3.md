# Householder v1 Repository Adaptation Document

**Date:** 2026-06-08  
**Phase:** 1 of 4 (Repository Inspection Complete)  
**Status:** Ready for Phase 2 approval

---

## UX Alignment Note (2026-06-11)

This repository adaptation document remains valid after the PRD v2.6 UX alignment. The repository facts have not changed: the existing Givebutter Processor is still file-based, the validation functions still require an adapter wrapper, and Householder still introduces SQLite as the new persistence layer.

Use this document for **repository reality** only. Use the following hierarchy for product and implementation decisions:

1. **Householder PRD v2.6 UX-aligned** — product contract and backend guardrails.
2. **UX_SUMMARY.md** — canonical 8-screen workflow and visible UI vocabulary.
3. **Accepted screen specs** — source of truth for screen-level copy/layout.
4. **HOUSEHOLDER_IMPLEMENTATION_PLAN v2.6 UX-aligned** — execution sequence.
5. **This adaptation document** — actual repository paths, existing processor functions, and integration constraints.

If an implementation detail in this document appears to conflict with PRD v2.6 or accepted screen specs, preserve the repository fact but follow the newer PRD/screen spec for route names, visible UI copy, and product behavior.


## Executive Summary

Inspection of the Givebutter Processor repository is complete. **All required validation functions exist and can be directly imported.** No missing dependencies. The current Flask app uses file-based CSV storage (no database). **Householder will introduce SQLite as the first new dependency.** See section 10 for blockers and recommendations.

---

## 1. Processor Location & Validation Functions

**Processor File:** `/scripts/processor.py` (783 lines, v2.5)

### Validation Functions Found ✅

All three required validation functions are available and importable.

#### a) `fuzzy_match()`
- **File:** `/scripts/processor.py:495-502`
- **Signature:** `fuzzy_match(str1: str, str2: str, threshold: float = 0.70) -> bool`
- **Return:** Boolean (True if match score >= threshold)
- **Uses:** SequenceMatcher for normalized string comparison
- **Note:** PRD refers to "fuzzy_email_match" but actual function is `fuzzy_match()`. Will need adapter wrapper.

#### b) `validate_phone()`
- **File:** `/scripts/processor.py:207-285`
- **Signature:** `validate_phone(record: Dict, header_map: Dict, rules: Dict) -> Tuple[str, Optional[str], Optional[str]]`
- **Return:** `(tier, reason, suggestion)` tuple
- **Note:** Full validation function. May need to extract normalization logic separately.

#### c) `validate_email()`
- **File:** `/scripts/processor.py:283-380`
- **Signature:** `validate_email(record: Dict, header_map: Dict, rules: Dict, reference: Dict) -> Tuple[str, Optional[str], Optional[str]]`
- **Return:** `(tier, reason, suggestion)` tuple
- **Dependencies:** `rules` (email_typos), `reference` (patterns)

### Adapter Functions Needed ✅

No implementations needed; wrappers only.

---

## 2. CSV Column Mapping

### Source Data: Givebutter Export

**Sample File Inspected:** `/test_data/realistic_export.csv` (real Givebutter export, 2 records)

**Exact Givebutter Header Row:**
```
Transaction ID,Payout ID,Status,Date,Name,Email,Phone,Address 1,Address 2,City,State,Zip,Country,Amount,Processing Fee,Givebutter Fee,Fees Covered,Campaign Title,Payment Method,utm_source,utm_medium
```

**Total Columns:** 21 core columns

### Householder Target Mapping

| Householder Field | Source Column | Processor Key |
|-------------------|---------------|---------------|
| `full_name` | `Name` | `name` |
| `email` | `Email` | `email` |
| `phone` | `Phone` | `phone` |
| `address_line_1` | `Address 1` | `address_1` |
| `city` | `City` | `city` |
| `state` | `State` | `state` |
| `postal_code` | `Zip` | `zip` |
| `zip5` | Derived from `Zip` | Computed |
| `amount_cents` | `Amount` | `amount` |
| `campaign_title` | `Campaign Title` | `campaign` |
| `donation_date` | `Date` | `date` |

### Extraction Safety ✅

Raw CSV values preserved exactly as received in test data.

---

## 3. Database Pattern

**Status:** ❌ No database used. File-based CSV storage only.

- **Storage:** CSV files in `/review/processing/`
- **Persistence:** Pandas read/write
- **No ORM:** No SQLAlchemy or migration tool

### Householder Strategy ✅

**Decision:** Introduce **SQLite + SQLAlchemy**

- Use Flask-Migrate for migrations
- Database file: `/givebutter.db`
- In-memory SQLite for tests

---

## 4. Flask App Structure

**Entry Point:** `/scripts/uploader/app.py` (697 lines)

**Routes:** Upload, file listing, validation

**Patterns:** Try/except at route level, JSON responses

**Test Framework:** pytest + Playwright

---

## 5. ORM Patterns

**Status:** ❌ No ORM. Pure Python with dicts.

### Householder Pattern ✅

- Suggestion engines return plain dicts
- Persistence happens in dedicated module
- Never pass session-bound ORM objects

---

## 6. Error Handling

**Processor Pattern:** Simple logging

**Flask Pattern:** Route-level try/except with JSON errors

**Householder:** Continue same patterns

---

## 7. Test Infrastructure

**Framework:** pytest (7.4.3)

**Directories:**
- `/tests/unit/` - Unit tests
- `/tests/integration/` - Integration tests
- `/tests/e2e/` - End-to-end tests with Playwright

**CRITICAL:** E2E tests must wait for observable completion, never for hidden elements.

---

## 8. Deployment Config

**Env Vars:**
- `ADMIN_TOKEN` - Optional bearer token

**Startup:** `python scripts/uploader/app.py`

**No Docker/systemd:** Manual run only

### Householder Changes ✅

1. Extend `.env` with `DATABASE_URL`
2. Add `flask db upgrade` to startup
3. Test setup: in-memory SQLite

---

## 9. PRD vs. Repository Alignment

### Key Differences

| Area | PRD Expected | Actual | Status |
|------|--------------|--------|--------|
| Validation functions | `fuzzy_email_match()`, etc. | `fuzzy_match()`, `validate_phone()`, `validate_email()` | Adapter needed ✅ |
| Database | Possibly existing | CSV files only | New schema ✅ |
| CSV columns | Example names | Real Givebutter export | Mapped ✅ |

---

## 10. Safe to Proceed?

### Blockers: None ✅

**All critical items verified:**
- ✅ Validation functions exist and importable
- ✅ CSV columns mapped to real export
- ✅ Flask/test infrastructure ready
- ✅ Database strategy identified
- ✅ ORM patterns compatible

### Next Phase

**Phase 2:** Design SQLAlchemy models and migrations

---

## Sign-Off

**Ready for Phase 2?** ✅ **YES**

No blockers. Proceed with database schema design.
