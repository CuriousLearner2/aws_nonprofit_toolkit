# E2E Test Reliability Guide

This document covers reliability patterns for end-to-end (E2E) browser tests in the Validation Review system.

## Architecture

### Database-Backed E2E Testing

The E2E tests use a fixture that provides a complete isolated environment:

```python
@pytest.fixture
def e2e_database_and_app():
    # 1. Create temporary SQLite database
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    database_url = f'sqlite:///{db_file.name}'
    
    # 2. Initialize schema
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)
    
    # 3. Configure Flask for database mode
    os.environ['HOUSEHOLDER_REPOSITORY'] = 'database'
    os.environ['GIVEBUTTER_DATABASE_URL'] = database_url
    
    # 4. Start Flask in background thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    yield database_url, db_path, app
    
    # 5. Cleanup
    Path(db_path).unlink(missing_ok=True)
```

**Benefits:**
- ✅ Isolated database per test (no cross-test pollution)
- ✅ Deterministic test data (same every run)
- ✅ No external dependencies (self-contained)
- ✅ Fast setup/teardown (temporary file, not disk I/O heavy)
- ✅ Parallel-safe (each test gets own port/database)

## DOM Synchronization Patterns

### ❌ Anti-Pattern: Arbitrary Sleeps

```python
# WRONG - flaky and slow
await email_input.fill('john@example')
await email_input.evaluate("el => el.blur()")
await asyncio.sleep(2)  # Hope 2 seconds is enough everywhere

# Fails on:
# - Slow CI systems (2 seconds not enough)
# - Fast local machines (wasted time)
# - Intermittent network delays
```

### ✅ Pattern: Explicit DOM Waits

```python
# CORRECT - reliable and efficient
await email_input.fill('john@example')
await email_input.evaluate("el => el.blur()")

# Wait for specific DOM state
await page.wait_for_function(
    "() => document.querySelector('.row-status-badge')?.textContent?.trim() === 'Blocking'",
    timeout=5000
)
```

**Why this works:**
- Polls DOM at regular intervals (~100ms)
- Returns immediately when condition becomes true
- Configurable timeout (default 5000ms)
- Fails fast if condition never becomes true

### DOM Wait Examples

**Wait for element to appear:**
```python
await page.wait_for_selector('.row-status-badge', timeout=5000)
```

**Wait for specific text:**
```python
await page.wait_for_function(
    "() => document.querySelector('.row-status-badge')?.textContent?.trim() === 'Blocking'",
    timeout=5000
)
```

**Wait for error state to become visible:**
```python
await page.wait_for_function(
    "() => {
        const input = document.querySelector('input[data-testid=\"email-input\"]');
        const style = window.getComputedStyle(input);
        return style.borderColor.includes('rgb(239');  // Red: rgb(239, 68, 68)
    }",
    timeout=5000
)
```

**Wait for error to clear:**
```python
await page.wait_for_function(
    "() => {
        const input = document.querySelector('input[data-testid=\"email-input\"]');
        const style = window.getComputedStyle(input);
        return !style.borderColor.includes('rgb(239');  // Error cleared
    }",
    timeout=5000
)
```

## Assertion Patterns

### ❌ Anti-Pattern: Conditional Assertions

```python
# WRONG - soft assertion, test passes even on failure
status_text = await status_cell.inner_text()
if status_text == 'Blocking':
    print("✓ Status is Blocking")
else:
    print("⚠ Status is not Blocking")  # Test still passes!
```

### ✅ Pattern: Hard Assertions

```python
# CORRECT - test fails immediately if condition not met
status_text = await status_cell.inner_text()
assert status_text == 'Blocking', f"Expected 'Blocking', got '{status_text}'"

# Or with explanatory message
assert status_text != 'No issues', (
    f"INVARIANT VIOLATED: Status shows 'No issues' but field has error. Got: {status_text}"
)
```

## Test Verification

### Run Single Test

```bash
pytest tests/e2e/test_validation_review_dom.py::test_invalid_email_updates_visible_row_status_and_issues -v
```

Expected output:
```
test_invalid_email_updates_visible_row_status_and_issues PASSED [100%]
✓ A1: Email field shows red error border
✓ A2: Review Status changed to badge
✓ A3: Review Status is 'Blocking' (not 'No issues')
✓ A4: Issues cell shows email error: email — Invalid email format
✓ A5: Email error styling cleared
✓ A6: Review Status recalculated after correction
```

### Run 5-Consecutive Reliability Check

```bash
bash scripts/dev/ux_gate_validation_review.sh
```

Expected output:
```
==================================
UX Gate: Validation Review Screen
Running browser DOM smoke test 5 times...
==================================

Run 1/5...
✓ Run 1 passed (4.86s)

Run 2/5...
✓ Run 2 passed (4.80s)

Run 3/5...
✓ Run 3 passed (4.81s)

Run 4/5...
✓ Run 4 passed (4.83s)

Run 5/5...
✓ Run 5 passed (4.82s)

==================================
✓ UX gate passed (5/5 runs)
==================================
```

### Run Fast Quality Gate

```bash
bash scripts/dev/quality_gate_review_screen.sh
```

Expected output:
```
==================================
Quality Gate: Validation Review Screen
Running fast integration tests...
==================================

test_autosave_invalid_email_returns_blocking_status PASSED [ 6%]
test_autosave_valid_email_clears_errors PASSED [ 13%]
... (13 more tests)
test_get_effective_values_after_autosave PASSED [100%]

======================= 15 passed in 2.47s ========================
✓ Quality gate passed
```

## Invariant Being Tested

**Review Status Invariant:**
> No visible field-level Error may coexist with Review Status = "No issues"

The test verifies:
1. When email field has red error border → Review Status shows "Blocking" (not "No issues")
2. When email error clears → Review Status recalculates to "No issues" or drops blocking status

## Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| Single browser test | ~5s | Playwright overhead: ~2s startup + ~3s interaction |
| 5-run gate | ~25s | Linear scaling (no parallelization) |
| Quality gate (15 tests) | ~2.4s | No browser, API-level testing |
| Full suite | ~25s | E2E (5s) + unit/integration (11s) + gate (2.4s) |

**Why performance is good:**
- DOM waits use polling, not fixed sleeps (no wasted time)
- Temporary database is fast (in-memory SQLite equivalent)
- Flask thread startup is quick once port is available
- Assertions fail fast (don't continue on soft failures)

## Troubleshooting

### Test Times Out (> 5 seconds per wait)

**Likely causes:**
1. DOM element never reaches expected state
2. Autosave endpoint not responding
3. Flask server crashed

**Diagnosis:**
```bash
# Check Flask is running
lsof -i :8001

# Check for JavaScript errors in browser
# (Add: page.on('console', lambda msg: print(msg)) in test)

# Check that wait condition is valid
# (Try simpler condition first)
```

**Fix:**
- Increase timeout if system is slow: `timeout=10000`
- Verify autosave endpoint is working (check Flask logs)
- Simplify wait condition (e.g., just wait for element to exist)

### Test Passes Locally, Fails in CI

**Likely causes:**
1. Timing assumptions (2-second sleep not enough on CI)
2. Port conflicts (8001 already in use)
3. Missing Playwright dependencies

**Fix:**
- Use explicit waits, not sleeps
- Verify port 8001 is available before test
- Ensure Playwright is installed: `playwright install chromium`

### Flaky: Test Passes Sometimes, Fails Sometimes

**Likely causes:**
1. Race condition in autosave
2. Insufficient wait timeout
3. DOM state is inconsistent

**Fix:**
- Increase timeout slightly
- Add explicit wait before assertion
- Verify autosave endpoint returns consistent response

## Key References

- **CLAUDE.md** — Givebutter testing guidelines and setup
- **tests/e2e/test_validation_review_dom.py** — Reference implementation
- **scripts/dev/ux_gate_validation_review.sh** — 5-run reliability harness
- **scripts/dev/quality_gate_review_screen.sh** — Fast regression gate

## Contributing New E2E Tests

Before writing a new browser test:

1. **Check if you need E2E at all**
   - API-level test? Use Flask test client (faster, more stable)
   - User workflow? Use browser test (DOM interaction essential)

2. **Use the fixture pattern**
   ```python
   @pytest.mark.e2e
   @pytest.mark.asyncio
   async def test_my_feature(e2e_database_and_app):
       database_url, db_path, flask_app = e2e_database_and_app
       # Test here
   ```

3. **Use explicit waits, not sleeps**
   - For every action, add a wait for observable completion
   - Use `page.wait_for_function()` for DOM state changes

4. **Use hard assertions**
   - Every verification should be `assert condition`, not `if/else`
   - Include descriptive messages for failures

5. **Run 5 times to verify reliability**
   ```bash
   for i in {1..5}; do
       pytest tests/e2e/test_my_feature.py -v || exit 1
   done
   ```

6. **Keep test isolated**
   - Use unique database per test
   - Clean up resources in fixture teardown
   - Don't rely on test execution order

---

**Last updated:** 2026-06-17  
**Maintainer:** Givebutter E2E test suite
