# E2E Test Reliability Guidelines

## Preventing Issues 1-4 from Recurring

### Issue 1: Hidden File Input Selectors
**Prevention:** Pre-commit hook installed at `.git/hooks/pre-commit`
- Blocks commits with `wait_for_selector('input[type="file"]')`
- Enforces use of `wait_for_selector('div.drop-zone', timeout=5000)` instead
- Status: ✅ Automated prevention in place

### Issue 2: Race Condition Propagation
**Prevention:** Always add explicit visibility waits before interaction
```python
# ❌ BAD - Race condition
review_button = await page.query_selector('button:has-text("Review")')
await review_button.click()

# ✅ GOOD - Explicit wait
await page.wait_for_selector('button:has-text("Review")', timeout=5000)
review_button = await page.query_selector('button:has-text("Review")')
await review_button.click()
```

**Checklist for new E2E tests:**
- [ ] Every `query_selector()` call preceded by `wait_for_selector()`?
- [ ] Timeouts set to 5000ms for visibility waits?
- [ ] No `await button.click()` without prior visibility confirmation?

### Issue 3: Test Interdependencies
**Prevention:** Flask fixture scope consideration
- Current: `scope="session"` (shared across all tests)
- Trade-off: Performance vs isolation
- **Recommendation:** Keep session scope for speed, but ensure tests can fail independently

**Before adding new tests:**
- [ ] Test doesn't rely on files/state from previous tests?
- [ ] Test cleans up its uploaded files after completion?
- [ ] Test uses unique filenames to avoid conflicts?

### Issue 4: Cumulative Timeouts
**Prevention:** Individual test timeout limits
- Max wait per operation: 5 seconds (visibility)
- Max wait per page action: 8 seconds (completion message)
- Total per test: ~30 seconds (Playwright default)
- **Red flag:** If a test takes >15 seconds consistently, it indicates a race condition

**Monitoring:**
```bash
# Run tests with timing output
pytest tests/e2e/ -v --durations=10
```

## Quick Verification Checklist

Before committing E2E test changes:
```bash
# 1. Check for hidden selectors
grep -r "wait_for_selector('input\[type=\"file\"\]')" tests/e2e/

# 2. Run individual failing tests
pytest tests/e2e/test_e2e_decision_workflow.py::test_save_all_decisions_completes_review -v

# 3. Run full suite with timeout monitoring
pytest tests/e2e/ -v --tb=short --durations=10

# 4. Check test execution time (should be < 2 minutes total)
time pytest tests/e2e/ -q
```

## Known Issues & Workarounds

### Playwright Text Selectors
- Issue: `text=/regex/` selector requires text to be visible in DOM
- Workaround: Use `page.content()` assertion instead for async-rendered content
- Applied in: `test_success_message_visual`, `test_save_all_decisions_completes_review`

### Flask App Response Timing
- Issue: Async operations may take 1-2 seconds to complete
- Workaround: Add `await asyncio.sleep(2)` before checking results
- Applied in: Decision save operations

## Future Improvements

1. **Parallelize tests** - Run tests in parallel with `pytest-xdist` to detect interdependencies
2. **Reduce Flask startup overhead** - Use module-scope fixture instead of session-scope (trades performance)
3. **Add visual debugging** - Screenshot on timeout for easier debugging
4. **CI/CD integration** - Run full E2E suite on every commit with timeout kill after 120s

---

**Last Updated:** 2026-06-01  
**Status:** All 4 issues have prevention mechanisms in place
