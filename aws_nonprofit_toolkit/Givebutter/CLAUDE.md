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
```bash
# Unit + Integration tests (fast)
pytest tests/unit tests/integration -v

# E2E tests (requires Flask app running)
pytest tests/e2e/ -v

# Specific test file
pytest tests/e2e/test_e2e_upload_workflow.py -v

# Single test with debugging
pytest tests/e2e/test_e2e_upload_workflow.py::test_page_loads_successfully -vv -s
```

### After Committing

1. **Pre-commit hook** automatically validates E2E tests
2. **CI/CD** (when configured) runs full suite with timeout=120s
3. **Monitor results** - flag any test taking > 15 seconds consistently

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
   pkill -f "python.*app.py"  # Flask app
   ```

2. **Check for hidden selectors**
   ```bash
   grep -r "input\[type=\"file\"\]" tests/e2e/
   ```

3. **Verify Flask app is not already running**
   ```bash
   lsof -i :8000
   ```

4. **Refer to**
   - SKILL_RESILIENT_TEST_DESIGN.md (general patterns)
   - E2E_TEST_RELIABILITY.md (project-specific)
   - givebutter_e2e_test_incident.md (incident details)

### If test fails intermittently

- Add more specific waits: `await page.wait_for_selector(specific_element)`
- Increase sleep before assertions: `await asyncio.sleep(2)`
- Check fixture scope (are tests sharing state?)

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

**Last updated:** 2026-06-01  
**Status:** Active (Post-incident improvements in place)
