# Skill: Designing Resilient Test Plans & Test Cases

## Overview

This skill captures lessons learned from debugging cascading E2E test failures in browser automation (Playwright). It provides a framework for designing test plans that prevent the 4 most common failure modes: hidden selectors, race conditions, test interdependencies, and cumulative timeouts.

**Use this skill when:**
- Designing a new test plan or test suite
- Writing browser automation tests (Selenium, Playwright, Puppeteer)
- Debugging flaky tests that work locally but fail in CI
- Scaling tests to multiple environments

---

## The 4 Failure Modes

### 1. Hidden Element Selectors (The Immediate Blocker)
**What happens:** Test tries to interact with invisible elements, causing 30-second timeouts per test.

**Root cause:** Browser automation tools cannot click, type, or check properties of hidden elements. Hidden elements are technically in the DOM but have CSS `display: none` or are covered by other elements.

**Red flags in test code:**
```python
# ❌ ANTI-PATTERN: Assuming element exists = element is interactive
file_input = page.query_selector('input[type="file"]')
await file_input.click()  # ← Timeout if input is hidden

# ✅ PATTERN: Wait for visibility before interaction
await page.wait_for_selector('div.drop-zone', visible=True)
file_input = page.query_selector('input[type="file"]')
await file_input.click()  # ← Now safe
```

**Prevention checklist:**
- [ ] Every interaction preceded by explicit visibility wait
- [ ] Waits target visible containers, not hidden form inputs
- [ ] Timeout set to 5-8 seconds (detects real problems quickly)
- [ ] Tests fail fast rather than hanging

---

### 2. Race Conditions (The Silent Killer)
**What happens:** Test proceeds before the application is ready, causing inconsistent failures.

**Root cause:** Asynchronous operations (page loads, API calls, DOM updates) complete at unpredictable times. Tests that check for element existence without waiting suffer race conditions.

**Example scenario:**
```
Time 0s:   Test uploads file
Time 0.5s: Test looks for "Review" button (doesn't exist yet, test passes)
Time 1s:   Flask app processes file
Time 2s:   JavaScript renders Review button
           ↑ But test already failed 1s ago
```

**Red flags in test code:**
```python
# ❌ ANTI-PATTERN: No wait between action and assertion
await upload_button.click()
review_button = page.query_selector('button:has-text("Review")')  # May not exist yet
await review_button.click()  # Timeout: button is None

# ✅ PATTERN: Wait for expected state after action
await upload_button.click()
await page.wait_for_selector('text=/processed|records/', timeout=5000)
review_button = page.query_selector('button:has-text("Review")')
await review_button.click()
```

**Prevention strategies:**
1. **Explicit state waits** - Always wait for observable changes after actions
   ```python
   action()  # Click, submit, etc.
   await page.wait_for_selector(evidence_of_completion)
   ```

2. **Idempotent waits** - Waits should succeed if condition already met
   ```python
   # Good: already loaded? returns immediately
   await page.wait_for_selector('.loaded-content', timeout=5000)
   
   # Bad: will timeout if content already loaded when wait starts
   await page.wait_for_selector('.loading-spinner', timeout=5000)
   ```

3. **Timeout-based polling** - For custom conditions
   ```python
   async def wait_for_condition(page, condition_fn, timeout_ms=5000):
       start = time.time()
       while time.time() - start < timeout_ms / 1000:
           if condition_fn():
               return True
           await asyncio.sleep(0.1)
       raise TimeoutError(f"Condition not met after {timeout_ms}ms")
   ```

---

### 3. Test Interdependencies (The Cascade Amplifier)
**What happens:** One failing test blocks all subsequent tests due to shared state.

**Root cause:** Tests share resources (Flask app fixture at session scope, shared database, file system). State from failed test pollutes next test's environment.

**Scenario:**
```
Test 1: ❌ Fails (file left in /uploads)
Test 2: ❌ Tries to upload same-named file, gets conflict
Test 3: ⏸️  Waits for Test 1-2 to complete
Test 4: ⏸️  Waiting...
...
Result: Full suite hangs while waiting for Test 1's 30-second timeout
```

**Prevention strategies:**

1. **Unique identifiers per test**
   ```python
   # ❌ BAD: All tests use same filename
   csv_file = temp_dir / "sample.csv"
   
   # ✅ GOOD: Each test has unique file
   test_id = f"{test_name}_{uuid.uuid4()}"
   csv_file = temp_dir / f"sample_{test_id}.csv"
   ```

2. **Explicit cleanup**
   ```python
   async def test_upload():
       try:
           # Test code
           await upload_file()
       finally:
           # Always cleanup, even if test fails
           await cleanup_uploaded_files()
   ```

3. **Fixture isolation strategy**
   ```python
   # Session scope: fast, but shared state
   @pytest.fixture(scope="session")
   def flask_app():
       return start_app()
   
   # Module scope: balance between isolation and speed
   @pytest.fixture(scope="module")
   def flask_app():
       return start_app()
   
   # Function scope: maximum isolation, slowest
   @pytest.fixture(scope="function")
   def flask_app():
       return start_app()
   ```

4. **State reset between tests**
   ```python
   @pytest.fixture(autouse=True)
   def cleanup(temp_dir):
       yield
       # Called after each test
       shutil.rmtree(temp_dir / "uploads", ignore_errors=True)
   ```

---

### 4. Cumulative Timeouts (The Scaling Problem)
**What happens:** Suite takes 20+ minutes as number of tests grows; CI jobs timeout.

**Root cause:** Each hidden selector timeout = 30 seconds. With 43 tests, some failing = 30s × number_of_failures = long wait.

**Prevention strategies:**

1. **Aggressive timeout limits**
   ```python
   # Detect problems quickly
   await page.wait_for_selector(selector, timeout=5000)  # 5 seconds
   
   # Not:
   await page.wait_for_selector(selector, timeout=30000)  # 30 seconds (Playwright default)
   ```

2. **Fail-fast on configuration errors**
   ```python
   # ✅ Fail immediately if Flask not responding
   response = await page.goto("http://127.0.0.1:8000", timeout=2000)
   assert response.status == 200, "Flask app not running"
   
   # Instead of silently timing out waiting for page load
   ```

3. **Parallel test execution**
   ```bash
   # Run tests in parallel to cap total time
   pytest tests/e2e/ -n 4  # 4 parallel workers
   
   # If test A hangs, others still progress
   ```

4. **Monitoring & alerting**
   ```bash
   # Set CI timeout shorter than individual test timeout
   # If full suite takes > 120s, kill and fail
   timeout 120 pytest tests/e2e/ -v
   
   # Alerts if any test takes > 15s consistently
   pytest tests/e2e/ -v --durations=0 | grep ">" | grep -v "0\.[0-9][0-9]s"
   ```

---

## Test Plan Design Checklist

### Before Writing Tests

- [ ] **Understand the system's async boundaries**
  - What operations are async? (API calls, DOM renders, file I/O)
  - What are observable completion signals? (Text appearing, element enabled, HTTP response)

- [ ] **Define fixture scope strategy**
  - Can tests share a database/app instance safely? → session/module scope (fast)
  - Do tests need isolation? → function scope (slow but safe)
  - Can you reset state between tests? → session scope + cleanup

- [ ] **Plan cleanup strategy**
  - What files/state will tests create?
  - How will they be cleaned up?
  - Who's responsible: test, fixture, or CI job?

- [ ] **Set timeout budgets**
  - Individual operation: 5-8 seconds
  - Full test: 15-30 seconds
  - Full suite: target < 2 minutes (for CI efficiency)

### While Writing Tests

- [ ] **Every action gets a wait**
  ```python
  await button.click()
  await page.wait_for_selector(evidence_of_completion)
  ```

- [ ] **Waits are specific, not generic**
  ```python
  # ❌ Too generic (waits for any text)
  await page.wait_for_selector('body', timeout=5000)
  
  # ✅ Specific (waits for actual result)
  await page.wait_for_selector('text=/records|PASS|WARNING|FAIL/', timeout=5000)
  ```

- [ ] **No hidden element interactions**
  - Grep for `input[type="file"]` in test code
  - If found, use `wait_for_selector('div.drop-zone')` instead

- [ ] **Test names reflect what they prove**
  ```python
  # ❌ Vague
  def test_upload():
  
  # ✅ Clear: declares expectation
  def test_upload_csv_with_special_characters():
  def test_file_input_accepts_csv():
  ```

### After Writing Tests

- [ ] **Run locally multiple times**
  ```bash
  for i in {1..5}; do pytest tests/e2e/ -q || break; done
  ```
  If any run fails, there's a race condition or timeout issue.

- [ ] **Check execution time**
  ```bash
  pytest tests/e2e/ -v --durations=10
  ```
  Red flag: any single test > 15 seconds (usually indicates timeout issue)

- [ ] **Lint for anti-patterns**
  ```bash
  # Check for hidden selectors
  grep -r "wait_for_selector('input\[type=\"file\"\]')" tests/e2e/
  
  # Check for missing waits before interactions
  grep -r "query_selector.*\n.*click()" tests/e2e/
  ```

- [ ] **Pre-commit hook validation**
  ```bash
  # Install hook to block problematic patterns
  cat > .git/hooks/pre-commit << 'EOF'
  grep -r "wait_for_selector('input\[type=\"file\"\]')" tests/e2e/ && exit 1
  exit 0
  EOF
  chmod +x .git/hooks/pre-commit
  ```

---

## Common Pitfalls & How to Avoid Them

| Pitfall | Why It's Bad | Prevention |
|---------|-------------|-----------|
| `query_selector()` without preceding `wait_for_selector()` | Race condition - element may not exist yet | Always wait for visibility before interaction |
| `wait_for_selector('body')` | Too generic, passes immediately even if page broken | Wait for specific outcome (text, element class, etc.) |
| Session-scoped fixtures without cleanup | One test's files block next test | Use `finally:` blocks or `@pytest.fixture(autouse=True)` cleanup |
| Hidden element selectors (`input[type="file"]`) | Playwright cannot interact, 30s timeout | Wait for visible parent container instead |
| No timeout on waits | Hangs forever if condition never met | Always set timeout (5-8s for visibility, 30s max) |
| Async assertions | Tests pass before result arrives | Add `await asyncio.sleep()` before checking results |
| Same filename in multiple tests | File conflict locks tests together | Use UUID or test-scoped temp directories |
| Assertions without page waits | False positives if content renders async | `await page.wait_for_selector()` → then assert |

---

## Example: Good Test Structure

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_upload_csv_with_special_characters(flask_app_running, temp_dir):
    """Test uploading CSV with Unicode names preserves data correctly."""
    from playwright.async_api import async_playwright
    
    # Setup: Create test data with unique identifier
    test_id = "special_chars_" + uuid.uuid4().hex[:8]
    csv_file = temp_dir / f"{test_id}.csv"
    csv_file.write_text("""Donation ID,Date,Donor Name,Email
GB001,2026-06-01,José García,jose@gmail.com
GB002,2026-06-01,李明,li@gmail.com""", encoding='utf-8')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        try:
            # Navigate
            await page.goto("http://127.0.0.1:8000/")
            
            # Wait for upload UI to be ready (explicit visibility wait)
            await page.wait_for_selector('div.drop-zone', timeout=5000)
            
            # Upload file
            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(csv_file))
            
            # Wait for completion signal (specific outcome)
            await page.wait_for_selector('text=/processed|records/', timeout=5000)
            
            # Allow async processing to complete
            await asyncio.sleep(1)
            
            # Verify result (check page content, not visible text)
            content = await page.content()
            assert 'José' in content, "Unicode name not preserved"
            assert '李明' in content, "Unicode name not preserved"
            
        finally:
            await browser.close()
            # Always cleanup
            csv_file.unlink(missing_ok=True)
```

---

## Reference: Timeline of Test Failure

```
Scenario: 43 tests, first 8 have hidden selector issues

Time 0:00    - Suite starts
Time 0:30    - Test 1 times out (hidden selector)
Time 1:00    - Test 2 times out (hidden selector)
...
Time 4:00    - Test 8 times out (hidden selector)
Time 4:05    - Test 9 finally starts (but Test 1-8 already wasted 4 minutes)
Time 6:30    - Test 9 completes
...
Time 21:00   - Suite finally finishes (or CI timeout kills it)

With fixes:
Time 0:00    - Suite starts
Time 0:10    - All 43 tests complete successfully
         ↑ 110x faster due to prevented timeouts
```

---

## Further Reading

- **Playwright best practices:** https://playwright.dev/python/docs/best-practices
- **Flaky test debugging:** https://github.com/microsoft/playwright/issues (search "flaky")
- **Test isolation patterns:** https://testautomationu.applitools.com/
- **Timeout strategy:** https://www.browserstack.com/guide/timeout-in-automation-testing

---

**Skill version:** 1.0  
**Last updated:** 2026-06-01  
**Tested on:** Playwright with Pytest, Python 3.14, macOS 23.6
