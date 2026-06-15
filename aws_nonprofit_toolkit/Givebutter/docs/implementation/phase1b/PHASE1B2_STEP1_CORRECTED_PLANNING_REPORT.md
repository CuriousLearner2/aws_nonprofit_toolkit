# Phase 1B2-Step 1: Corrected Database Mode Verification Planning Report

**Date**: 2026-06-12  
**Phase**: 1B2-Step 1 (Planning, Corrected)  
**Status**: Ready for Phase 1B2-Step 2 Implementation

---

## Issue 1: Route Response Types (CORRECTED)

### Finding: All 8 Canonical Routes Render HTML Templates

**Confirmed routes** (from `scripts/uploader/app.py:813-861`):

```python
@app.route('/imports')
def imports_list():
    imports = import_service.get_imports()
    return render_template('imports/list.html', imports=imports)

@app.route('/imports/<import_id>/dashboard')
def import_dashboard(import_id):
    dashboard_data = dashboard_service.get_import_dashboard(import_id)
    return render_template('imports/dashboard.html', batch=..., queue_status=...)

@app.route('/imports/<import_id>/validation')
def import_validation(import_id):
    data = validation_service.get_validation_review(import_id)
    return render_template('imports/validation.html', **data)

# ... and 5 more routes (duplicates, normalizations, households, audit, exports)
```

**All routes use `render_template()`** → Returns HTML, not JSON.

### Existing Integration Test Pattern

Tests confirm HTML-based assertions (from `tests/integration/test_dashboard_route.py`):

```python
def test_dashboard_route_returns_200(self, client):
    response = client.get('/imports/IMP-2025-0101-A/dashboard')
    assert response.status_code == 200

def test_dashboard_contains_batch_id(self, client):
    response = client.get('/imports/IMP-2025-0101-A/dashboard')
    assert b'IMP-2025-0101-A' in response.data  # ← HTML text assertion

def test_dashboard_contains_filename(self, client):
    response = client.get('/imports/IMP-2025-0101-A/dashboard')
    assert b'donors_q1_2025.csv' in response.data  # ← HTML text assertion
```

### Correction from Original Plan

**Original (WRONG)**:
```python
data = json.loads(response.data)  # ❌ Routes don't return JSON
assert data["batch"]["id"] == "IMP-TEST-001"
```

**Corrected (RIGHT)**:
```python
html = response.get_data(as_text=True)  # Get HTML as text
assert response.status_code == 200
assert "IMP-TEST-001" in html  # Text assertion
assert "donors_q1_2025.csv" in html  # Visible content assertion
```

---

## Issue 2: Configuration Precedence (CORRECTED)

### Current Implementation Status

**Good news**: `repository_provider.py` already implements correct precedence:

```python
# Current precedence (CORRECT):
1. config['HOUSEHOLDER_REPOSITORY'] (explicit argument, highest)
2. HOUSEHOLDER_REPOSITORY environment variable
3. Default: 'fixture' (lowest)
```

Code evidence from `scripts/householder/repository_provider.py:65-90`:

```python
def _get_repository_mode(config: Optional[Mapping[str, Any]] = None) -> str:
    # Check config dict first (highest priority)
    if config and "HOUSEHOLDER_REPOSITORY" in config:
        return config["HOUSEHOLDER_REPOSITORY"].lower()
    
    # Check environment variable (medium priority)
    env_mode = os.getenv("HOUSEHOLDER_REPOSITORY", "").lower()
    if env_mode:
        return env_mode
    
    # Default to fixture (lowest priority)
    return "fixture"
```

### What Was Wrong in Original Plan

The original plan proposed adding Flask app context checking **before** checking the explicit config parameter. That would have broken precedence:

```python
# WRONG precedence (what original plan suggested):
if config is None:
    config = flask_app_context_config  # ← Would override env vars
    # Now explicit config = None would still check Flask context
```

### Corrected Precedence with Flask App Context (Optional Enhancement)

**New precedence** (if Flask app context feature is added):

```
1. explicit config parameter (passed to get_import_repository(config))    [HIGHEST]
2. Flask current_app.config (only if config=None AND in Flask context)
3. environment variables (HOUSEHOLDER_REPOSITORY, GIVEBUTTER_DATABASE_URL)
4. fixture default                                                        [LOWEST]
```

**Implementation approach**:

```python
def get_import_repository(config: Optional[Mapping[str, Any]] = None) -> ImportRepositoryProtocol:
    """
    Get repository instance with correct precedence:
    1. Explicit config argument (highest priority)
    2. Flask app context (if no explicit config and in Flask context)
    3. Environment variables
    4. Fixture default (lowest priority)
    """
    
    # If explicit config provided, use it directly without checking other sources
    if config is not None:
        repository_mode = _get_repository_mode(config)
    else:
        # config is None, so check Flask app context
        flask_config = _get_flask_app_config()  # None if not in Flask context
        
        if flask_config:
            # Build config from Flask app context
            config = flask_config
        # else: config remains None, let _get_repository_mode use env vars
        
        repository_mode = _get_repository_mode(config)
    
    # Rest of existing logic...
```

**Critical safeguard**: Explicit config always takes priority:

```python
# These assertions must always be true:

# Explicit config beats everything
assert get_import_repository({"HOUSEHOLDER_REPOSITORY": "fixture"}, app_config_says_database, env_says_database) 
    == FixtureImportRepository  # ✅ Uses explicit config

# Explicit config beats Flask context
assert get_import_repository({"HOUSEHOLDER_REPOSITORY": "database", "GIVEBUTTER_DATABASE_URL": "..."}, app_config_says_fixture) 
    == DatabaseImportRepository  # ✅ Uses explicit config, not app context
```

---

## Corrected HTML-Based Route Test Strategy

### Route Test Approach (HTML-Based)

**Test structure**: Use Flask test client + HTML assertions, matching existing integration test pattern.

```python
import pytest
from pathlib import Path
import sys

# tests/integration/test_database_mode_routes.py

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.uploader.app import app


@pytest.fixture
def client(monkeypatch, initialized_test_db):
    """Create Flask test client with database mode configured."""
    # Configure database mode via environment variables
    monkeypatch.setenv('HOUSEHOLDER_REPOSITORY', 'database')
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', initialized_test_db)
    
    # Create app in test mode
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestDatabaseModeRoutes:
    """Integration tests verifying routes work with database-backed data."""
    
    def test_imports_list_from_database(self, client):
        """Verify /imports renders from database mode."""
        response = client.get('/imports')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        
        # Verify database-seeded values appear in HTML
        assert 'IMP-TEST-001' in html
        assert 'donors_q1_2025.csv' in html
        assert 'Q1 2025' in html
    
    def test_dashboard_from_database(self, client):
        """Verify /imports/<id>/dashboard renders from database."""
        response = client.get('/imports/IMP-TEST-001/dashboard')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        
        # Verify batch data from database appears in HTML
        assert 'IMP-TEST-001' in html
        assert 'donors_q1_2025.csv' in html
        assert '42%' in html  # Progress from seed data
        
        # Verify queue navigation links exist (route content)
        assert '/imports/IMP-TEST-001/validation' in html
        assert '/imports/IMP-TEST-001/duplicates' in html
    
    def test_validation_from_database(self, client):
        """Verify /imports/<id>/validation renders from database."""
        response = client.get('/imports/IMP-TEST-001/validation')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        
        # Verify batch info appears
        assert 'IMP-TEST-001' in html
        
        # Verify validation review item data from database
        # (Would include seeded validation items - exact values TBD after seed schema review)
        assert 'Validation' in html
        assert '<th' in html  # Table structure exists
    
    def test_normalizations_from_database(self, client):
        """Verify /imports/<id>/normalizations renders from database."""
        response = client.get('/imports/IMP-TEST-001/normalizations')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        
        assert 'IMP-TEST-001' in html
        assert 'Normalization' in html or 'Normaliz' in html
    
    def test_households_from_database(self, client):
        """Verify /imports/<id>/households renders from database."""
        response = client.get('/imports/IMP-TEST-001/households')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        
        assert 'IMP-TEST-001' in html
        assert 'Household' in html or 'Grouping' in html
    
    def test_duplicates_from_database(self, client):
        """Verify /imports/<id>/duplicates renders from database."""
        response = client.get('/imports/IMP-TEST-001/duplicates')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        
        assert 'IMP-TEST-001' in html
        assert 'Duplicate' in html
    
    def test_audit_from_database(self, client):
        """Verify /imports/<id>/audit renders from database."""
        response = client.get('/imports/IMP-TEST-001/audit')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        
        assert 'IMP-TEST-001' in html
        assert 'Audit' in html
        # Audit entries from seed (e.g., "Sarah Lee", "marked as Same Person")
        assert 'Sarah Lee' in html or 'Audit' in html
    
    def test_exports_from_database(self, client):
        """Verify /imports/<id>/exports renders from database."""
        response = client.get('/imports/IMP-TEST-001/exports')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        
        assert 'IMP-TEST-001' in html
        assert 'Export' in html
```

### Why This Approach

1. **Matches existing pattern**: All current integration tests use this HTML assertion approach
2. **Tests full stack**: Route + service + repository chain
3. **Verifies rendering**: Confirms Jinja2 templates work with database data
4. **No JSON parsing**: Avoids false positives from intermediate data structures

---

## Proposed Repository Provider Precedence Tests

### New unit tests for `repository_provider.py`:

```python
# tests/unit/test_repository_provider_precedence.py

import pytest
import os
from scripts.householder.repository_provider import get_import_repository
from scripts.householder.fixture_repository import FixtureImportRepository
from scripts.householder.database_repository import DatabaseImportRepository


class TestRepositoryProviderPrecedence:
    """Test configuration precedence in repository provider."""
    
    def test_explicit_config_beats_environment(self, monkeypatch):
        """Explicit config parameter takes priority over environment variables."""
        # Set environment to database
        monkeypatch.setenv('HOUSEHOLDER_REPOSITORY', 'database')
        monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///ignored.db')
        
        # Explicit config says fixture
        repo = get_import_repository(config={'HOUSEHOLDER_REPOSITORY': 'fixture'})
        
        # Must use fixture, not environment's database
        assert isinstance(repo, FixtureImportRepository)
    
    def test_explicit_config_database_url_beats_environment(self, monkeypatch):
        """Explicit database URL beats environment variable."""
        monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///env.db')
        
        # Explicit config specifies different URL
        config = {
            'HOUSEHOLDER_REPOSITORY': 'database',
            'GIVEBUTTER_DATABASE_URL': 'sqlite:///explicit.db'
        }
        repo = get_import_repository(config=config)
        
        # Must use explicit URL, not environment URL
        assert isinstance(repo, DatabaseImportRepository)
        assert repo.database_url == 'sqlite:///explicit.db'
    
    def test_environment_used_when_explicit_config_none(self, monkeypatch):
        """Environment variables used when explicit config is None."""
        monkeypatch.setenv('HOUSEHOLDER_REPOSITORY', 'database')
        monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///env.db')
        
        # Pass None explicitly - should use environment
        repo = get_import_repository(config=None)
        
        assert isinstance(repo, DatabaseImportRepository)
        assert repo.database_url == 'sqlite:///env.db'
    
    def test_environment_used_when_no_explicit_config(self, monkeypatch):
        """Environment variables used when get_import_repository() called with no args."""
        monkeypatch.setenv('HOUSEHOLDER_REPOSITORY', 'fixture')
        
        # Call with no arguments - should use environment
        repo = get_import_repository()
        
        assert isinstance(repo, FixtureImportRepository)
    
    def test_fixture_default_when_nothing_configured(self, monkeypatch):
        """Fixture is default when nothing is configured."""
        # Clear environment
        monkeypatch.delenv('HOUSEHOLDER_REPOSITORY', raising=False)
        monkeypatch.delenv('GIVEBUTTER_DATABASE_URL', raising=False)
        
        # Call with no config, no environment
        repo = get_import_repository(config=None)
        
        assert isinstance(repo, FixtureImportRepository)
    
    def test_database_mode_without_url_raises_error(self):
        """Database mode without URL raises ValueError."""
        with pytest.raises(ValueError) as exc:
            get_import_repository(config={'HOUSEHOLDER_REPOSITORY': 'database'})
        
        assert 'Database mode requested but no database URL' in str(exc.value)
    
    def test_invalid_repository_mode_raises_error(self):
        """Invalid repository mode raises ValueError."""
        with pytest.raises(ValueError) as exc:
            get_import_repository(config={'HOUSEHOLDER_REPOSITORY': 'invalid_mode'})
        
        assert 'Invalid HOUSEHOLDER_REPOSITORY mode' in str(exc.value)
    
    def test_explicit_config_empty_dict_uses_defaults(self, monkeypatch):
        """Empty explicit config dict still takes precedence but uses defaults."""
        monkeypatch.setenv('HOUSEHOLDER_REPOSITORY', 'database')
        monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///env.db')
        
        # Pass empty dict - should use defaults (fixture), not environment
        repo = get_import_repository(config={})
        
        assert isinstance(repo, FixtureImportRepository)
```

---

## Proposed Test Database Setup (Unchanged from Original Plan)

### Database Infrastructure
- **Type**: SQLite (temporary)
- **Location**: pytest tmpdir fixture
- **Scope**: Per-test isolation
- **Cleanup**: Automatic via pytest

### Seed Data Requirements
- 1 import batch: `IMP-TEST-001`
- 5 raw import rows (contacts)
- 5 import contacts
- 4 review items (validation, normalization, duplicate, household)
- Review item subjects (map items to contacts)
- 2 review decisions (for audit trail)
- 3 audit log entries

[Seed implementation details unchanged from original plan]

---

## Configuration for Phase 1B2 Tests

### Test Database Configuration Approach

**Recommended**: Use environment variables via pytest monkeypatch

```python
@pytest.fixture
def client(monkeypatch, initialized_test_db):
    """Configure test app for database mode."""
    # Set environment variables for database mode
    monkeypatch.setenv('HOUSEHOLDER_REPOSITORY', 'database')
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', initialized_test_db)
    
    # Create Flask app (uses default config, services will check env vars)
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client
```

**Why environment variables** (not Flask app config):
- Simpler test setup (no app.config modification)
- Matches real-world deployment pattern
- Works with existing repository_provider implementation
- Explicit, testable configuration

**Why not Flask app context** (for Phase 1B2):
- Not needed for initial verification
- Can be added later as optional enhancement
- Adds complexity to repository_provider
- Environment variables are sufficient

---

## Risk Assessment (Updated)

### Risk 1: Service Config Parameter Not Used by Routes
**Status**: CONFIRMED OK
- Routes call services with no config parameter → services use default (fixture)
- Database mode tests will set environment variables
- Repository provider will detect environment and use database mode
- **Mitigation**: ✅ Environment variables + monkeypatch

### Risk 2: HTML Assertions May Be Too Loose
**Status**: LOW (fixtures provide deterministic values)
- Seed data values are known and specific
- Route HTML includes visible content from database
- Can verify specific contact names, batch IDs, counts
- **Mitigation**: Use specific values from seed data in assertions

### Risk 3: Schema Mismatch
**Status**: MEDIUM (needs verification in Step 2)
- Schema.sql must exist and match Option C
- DatabaseImportRepository ORM models must align
- **Mitigation**: Verify schema before seed implementation

### Risk 4: Existing Integration Tests May Conflict
**Status**: LOW (using separate file + separate database)
- New tests in `test_database_mode_routes.py`
- Separate temporary database
- Existing fixture tests use fixture data
- **Mitigation**: ✅ Isolation via separate file and database

---

## Updated Implementation Recommendation for Phase 1B2-Step 2

### Implementation Order

1. **Create test database infrastructure** (`tests/integration/conftest.py`)
   - tmpdir fixture for database
   - Schema loading
   - Seed data function

2. **Verify schema** (manual inspection)
   - Confirm Option C tables exist
   - Verify no typed tables created
   - Match database models to schema

3. **Implement seed data** (`tests/integration/seed_database.py`)
   - Insert minimal but complete test data
   - Verify seed completes without errors

4. **Add repository provider precedence tests** (`tests/unit/test_repository_provider_precedence.py`)
   - Verify explicit config priority
   - Verify environment variable fallback
   - Verify default behavior

5. **Implement database mode route tests** (`tests/integration/test_database_mode_routes.py`)
   - 8 tests (one per route)
   - HTML assertions matching existing pattern
   - Database-seeded values verified

6. **Run baseline verification**
   ```bash
   pytest tests/unit tests/integration
   ```
   - All 812 existing tests must pass
   - New precedence tests: 8 tests
   - New route tests: 8 tests

7. **Create Phase 1B2 completion record**
   - Document results
   - Confirm all routes verified
   - Confirm fixture mode unchanged

---

## Confirmation: What Must NOT Change

✅ **Explicitly preserved**:
- Route signatures (no parameters added)
- Template structure (no render changes)
- Service signatures (config param optional)
- All 812 fixture-mode tests (must pass)
- Fixture default behavior
- Database opt-in requirement
- No write APIs
- No export file generation
- No CRM writeback
- No automatic actions

---

## Summary: Ready for Phase 1B2-Step 2

| Aspect | Status | Evidence |
|--------|--------|----------|
| Routes return HTML | ✅ Confirmed | `render_template()` in all 8 routes |
| Test strategy corrected | ✅ HTML assertions | Matches existing integration tests |
| Config precedence correct | ✅ Explicit config wins | Already in repository_provider.py |
| Flask context optional | ✅ Future enhancement | Can be added without breaking precedence |
| Environment variables ready | ✅ Supported | Repository provider checks env vars |
| Seed data strategy | ✅ Minimal/complete | 5 contacts, 4 items, 3 audit entries |
| Test isolation | ✅ Separate file/db | temp database via pytest fixture |
| Risk areas identified | ✅ 4 risks assessed | All have mitigations |

---

## Recommendation: READY FOR PHASE 1B2-STEP 2

**Go/No-Go**: ✅ **GO**

**Phase 1B2-Step 2 should proceed with**:
1. HTML-based route assertions (not JSON)
2. Environment variables for database mode configuration
3. Explicit config precedence preservation
4. 8 database-mode integration tests
5. Repository provider precedence unit tests

**Phase 1B2-Step 2 implementation can begin immediately**. No blocking issues.

---

**Baseline verification command**:
```bash
cd aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter
pytest tests/unit tests/integration -v
```

**Expected result**: 812 tests passing (existing baseline intact)
