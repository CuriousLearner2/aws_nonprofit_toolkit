# Claude Code Guidelines for Givebutter Project

## Testing

### E2E Tests - Critical Requirements

Based on incident 2026-06-01 where hidden selectors caused cascade timeouts:

**NEVER do this:**
```python
# ❌ BLOCKED by pre-commit hook
await page.wait_for_selector('input[type="file"]')
```

**ALWAYS do this:**
```python
# ✅ REQUIRED
await page.wait_for_selector('div.drop-zone', timeout=5000)
```

**Pattern for every action:**
```python
# Action
await button.click()

# Wait for observable completion
await page.wait_for_selector(evidence_of_completion, timeout=5000)

# Then proceed
next_operation()
```

### Test Verification

Before committing E2E tests:
```bash
# 1. Check for hidden selectors (pre-commit hook blocks these)
grep -r "wait_for_selector('input\[type=\"file\"\]')" tests/e2e/

# 2. Run new tests individually first
pytest tests/e2e/test_e2e_YOUR_FILE.py::test_your_test -v

# 3. Run full suite with timing
pytest tests/e2e/ -v --durations=10

# 4. Check total execution time (should be < 2 minutes)
time pytest tests/e2e/ -q
```

### Key Testing Documents

- **[SKILL_RESILIENT_TEST_DESIGN.md](SKILL_RESILIENT_TEST_DESIGN.md)** - Comprehensive guide for writing resilient tests
- **[E2E_TEST_RELIABILITY.md](E2E_TEST_RELIABILITY.md)** - Project-specific reliability guidelines and monitoring

### Common Issues

| Issue | Solution | Docs |
|-------|----------|------|
| Test hangs/times out | Check for hidden element selectors or missing `wait_for_selector()` | SKILL_RESILIENT_TEST_DESIGN.md § Issue 1 |
| Race condition (test passes locally, fails in CI) | Add explicit waits after async operations | SKILL_RESILIENT_TEST_DESIGN.md § Issue 2 |
| One test failure blocks others | Use unique filenames, cleanup in `finally:` blocks | SKILL_RESILIENT_TEST_DESIGN.md § Issue 3 |
| Suite takes > 2 minutes | Check for cumulative timeouts, add aggressive limits | SKILL_RESILIENT_TEST_DESIGN.md § Issue 4 |

---

## Workflow

### Before Running Tests
```bash
cd aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter
source .venv/bin/activate
```

### Running Tests

**Development Strategy:**
- **Default (daily use):** Unit + Integration tests (1263 tests, ~11 seconds)
- **Quality Gate (fast validation):** Review Screen regression suite (15 tests, ~2.4 seconds)
- **Browser Interaction:** Playwright DOM tests (automatic Flask startup, ~5 seconds per test)
- **Full suite:** All unit + integration + E2E (~25 seconds total)

```bash
# Standard: Unit + Integration only (RECOMMENDED for development)
pytest tests/unit tests/integration -q

# With details
pytest tests/unit tests/integration -v --tb=short

# Parallel (faster on multi-core)
pytest tests/unit tests/integration -n auto

# Quality gate: Fast regression tests for Validation Review
bash scripts/dev/quality_gate_review_screen.sh

# E2E browser test (starts Flask automatically with database mode)
pytest tests/e2e/test_validation_review_dom.py -v

# E2E test with 5-run reliability check
bash scripts/dev/ux_gate_validation_review.sh

# Single test with debugging
pytest tests/e2e/test_validation_review_dom.py::test_invalid_email_updates_visible_row_status_and_issues -vv -s
```

### E2E Infrastructure (Database-Backed)

The E2E tests use a database-backed Flask fixture that:
- Creates a temporary SQLite database per test
- Configures Flask for database mode (`HOUSEHOLDER_REPOSITORY=database`)
- Seeds test data (ImportBatch, RawImportRow, ImportContact)
- Starts Flask in a background thread
- Provides deterministic, isolated test environment

**Example E2E test pattern:**
```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_validation_review_dom(e2e_database_and_app):
    """Playwright browser test with database-backed Flask."""
    database_url, db_path, flask_app = e2e_database_and_app
    
    # Seed test data
    Session = sessionmaker(bind=create_db_engine(database_url))
    session = Session()
    batch = ImportBatch(id='test-batch', ...)
    session.add(batch)
    session.commit()
    
    # Launch browser and test
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto('http://127.0.0.1:8001/imports/test-batch/validation')
```

### After Committing

1. **Pre-commit hook** automatically validates E2E tests (no hidden selectors)
2. **Quality gate runs** - `bash scripts/dev/quality_gate_review_screen.sh` (15 tests, ~2.4s)
3. **Browser gate runs** - `bash scripts/dev/ux_gate_validation_review.sh` (5 consecutive runs, ~5s each)
4. **CI/CD** (when configured) runs full suite with timeout=120s
5. **Monitor results** - flag any test taking > 15 seconds consistently

---

## Database

Givebutter uses SQLite for testing:
```bash
# Inspect test database
sqlite3 givebutter.db "SELECT * FROM donations LIMIT 5;"

# Never commit test databases
# They're gitignored by design
```

---

## Environment

### Required
- Python 3.14+
- Poetry/Pip for dependencies (see requirements.txt)
- Flask app runs on http://127.0.0.1:8000

### Optional
- Playwright browsers (installed on first test run)
- pytest plugins (asyncio, xdist for parallelization)

---

## Problem Solving

### If E2E tests hang

1. **Kill the process**
   ```bash
   pkill -f "pytest tests/e2e"
   pkill -f "Flask"  # Background Flask threads
   lsof -i :8001 | grep -v LISTEN | awk '{print $2}' | xargs kill -9  # Force kill port 8001
   ```

2. **Check for hidden selectors**
   ```bash
   grep -r "wait_for_selector('input\[type=\"file\"\]')" tests/e2e/
   ```

3. **Verify ports are available**
   ```bash
   lsof -i :8000  # Upload app
   lsof -i :8001  # E2E test app
   ```

4. **Check database cleanup**
   ```bash
   ls -la /tmp/*.db 2>/dev/null | wc -l  # Should be minimal
   ```

5. **Refer to**
   - SKILL_RESILIENT_TEST_DESIGN.md (general patterns)
   - E2E_TEST_RELIABILITY.md (project-specific)
   - givebutter_e2e_test_incident.md (incident details)

### If browser test fails intermittently

**Replace arbitrary sleeps with explicit waits:**
- ❌ Don't use: `await asyncio.sleep(2)`
- ✅ Do use: `await page.wait_for_function("() => document.querySelector('.selector')?.textContent?.trim() === 'expected'", timeout=5000)`

**Common synchronization patterns:**
```python
# Wait for DOM element to appear
await page.wait_for_selector('.row-status-badge', timeout=5000)

# Wait for specific text content
await page.wait_for_function(
    "() => document.querySelector('.row-status-badge')?.textContent?.trim() === 'Blocking'",
    timeout=5000
)

# Wait for error state to clear
await page.wait_for_function(
    "() => !window.getComputedStyle(document.querySelector('input')).borderColor.includes('rgb(239')",
    timeout=5000
)
```

**Verify assertions are hard (not conditional):**
- ❌ Don't use: `if status == 'Blocking': pass  # soft assertion`
- ✅ Do use: `assert status == 'Blocking'  # hard assertion - test fails if not true`

---

## Key References

| Document | Purpose | When to Use |
|----------|---------|-------------|
| [SKILL_RESILIENT_TEST_DESIGN.md](SKILL_RESILIENT_TEST_DESIGN.md) | Comprehensive guide to resilient test design | Writing new E2E tests, debugging flakiness |
| [E2E_TEST_RELIABILITY.md](E2E_TEST_RELIABILITY.md) | Project-specific reliability guidelines | Quick reference, monitoring commands |
| [givebutter_e2e_test_incident.md](../../../.claude/projects/-Users-gautambiswas-Claude-Code/memory/givebutter_e2e_test_incident.md) | Historical incident analysis | Understanding why these patterns matter |

---

## For Future Contributors

Before you start working on tests in this project:
1. Read [SKILL_RESILIENT_TEST_DESIGN.md](SKILL_RESILIENT_TEST_DESIGN.md) (30 min)
2. Run the verification checklist in [E2E_TEST_RELIABILITY.md](E2E_TEST_RELIABILITY.md)
3. Familiarize yourself with [givebutter_e2e_test_incident.md](../../../.claude/projects/-Users-gautambiswas-Claude-Code/memory/givebutter_e2e_test_incident.md) (context: why these rules exist)

---

**Last updated:** 2026-06-17  
**Status:** Active (E2E infrastructure and browser DOM tests added)
