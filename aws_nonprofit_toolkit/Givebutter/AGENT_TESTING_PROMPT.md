# Prompt for Testing Agent: Givebutter Processor UI Validation

## Your Mission

Execute the **top 5 critical E2E test cases** for the Givebutter Processor donation review UI using Playwright. Verify that operators can upload CSVs, review records, fix issues via inline editing, override validation tiers, and complete the workflow.

---

## Context & Documentation

**Read these first** (in order):
1. **FEATURE_OVERVIEW_FOR_AGENTS.md** - Understand what the app does and why each feature matters
2. **E2E_TEST_PLAN_P0.md** - The actual test procedures you'll execute

**Key Files**:
- Flask app: `/aws_nonprofit_toolkit/Givebutter/scripts/uploader/app.py`
- UI templates: `/aws_nonprofit_toolkit/Givebutter/scripts/uploader/templates/review.html`
- Test data location: Create sample CSV with 5 records (PASS/WARNING/FAIL mix)

---

## Your Task

Run the **5 P0 test cases** from E2E_TEST_PLAN_P0.md:

1. ✅ **Upload CSV & Process Records** - File appears in review queue with correct tier counts
2. ✅ **Inline Editing with Real-Time Tier Auto-Update** - Edit phone field → tier changes WARNING→PASS (green)
3. ✅ **Override Tier via Dropdown** - Manually change FAIL (red) → PASS (green) with color feedback
4. ✅ **Fix Email Typo & Verify Fuzzy Matching** - Catch `gmai.com` typo, show suggestion, apply fix
5. ✅ **Bulk Actions & Complete Review** - Approve all → confirmation dialog → Done button → workflow complete

---

## Prerequisites

**Before starting tests**:

```bash
# 1. Navigate to Givebutter directory
cd /Users/gautambiswas/Claude\ Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter

# 2. Start Flask server (in terminal 1)
source venv/bin/activate
python3 scripts/uploader/app.py

# 3. Verify server is running
# Should see: "Running on http://127.0.0.1:8000"

# 4. In terminal 2, run your Playwright tests
pytest tests/e2e/test_e2e_agent_validation.py -v --tb=short
```

---

## Test Execution

**For each test case**, follow the step-by-step procedure in E2E_TEST_PLAN_P0.md:
- Each test has numbered steps
- Each test has success criteria (all must pass)
- Use the CSS selectors provided in the doc
- Document any failures with screenshots/console logs

**Example test structure**:
```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_p0_1_upload_csv():
    """Test Case 1: Upload CSV & Process"""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Follow E2E_TEST_PLAN_P0.md steps 1-6
        # Verify success criteria
        
        await browser.close()
```

---

## Success Criteria

**PASS**: All 5 test cases pass with all success criteria met
- ✅ No JavaScript errors in console
- ✅ All tier colors display correctly (green/yellow/red)
- ✅ Auto-save persists changes (verify via reload)
- ✅ Tier auto-updates when issues are fixed
- ✅ Bulk actions work with confirmation dialogs

**FAIL**: Any test case fails or any success criterion is not met
- Document which test failed
- Screenshot of failure
- Browser console errors
- Network request failures

**PARTIAL**: 3-4 tests pass (investigate failures, may be environmental issue)

---

## What to Report

Create a test report with:

1. **Summary**: PASS/FAIL/PARTIAL + number of tests passed
2. **Per-test results**: 
   - Test name
   - Status (✅ PASS or ❌ FAIL)
   - If failed: what went wrong + steps to reproduce
3. **Issues found**:
   - UI bugs (missing elements, colors wrong, etc.)
   - Functional bugs (auto-update not working, tier not saving, etc.)
   - Performance issues (delays >1 second for auto-save, etc.)
4. **Console errors**: Any JavaScript exceptions
5. **Data persistence**: Verify changes saved to CSV file (check disk)
6. **Recommendations**: Anything to fix before production

---

## Key Things to Verify

✅ **Color Coding**
- Pass dropdown = Green (#d4edda)
- Warning dropdown = Yellow (#fff3cd)
- Fail dropdown = Red (#f8d7da)
- Colors update immediately on tier change

✅ **Auto-Save Persistence**
- Edit field → Save button → File updated to disk
- Close/reopen file → Changes still there
- Reload page → All data preserved

✅ **Tier Auto-Update**
- Fix issue (e.g., add phone) → Tier recalculates
- WARNING → PASS happens instantly (no page refresh)
- Issues column updates
- Color changes on dropdown

✅ **Fuzzy Email Matching**
- Typo `gmai.com` is flagged as WARNING
- Suggestion shows "Consider: user@gmail.com"
- Operator can click field, fix, save
- Tier updates after fix

✅ **Bulk Actions**
- "All: Approved" sets all decisions at once
- Confirmation dialog appears for FAIL/WARNING records
- ≤5 records: individual dialogs
- >5 records: summary dialog
- "Done" button closes review

---

## Troubleshooting

If you hit issues:

1. **Flask server not starting?**
   - Check port 8000 is free: `lsof -i :8000`
   - Check Python venv is activated

2. **Tests timeout waiting for elements?**
   - Verify Flask server is running
   - Check CSS selectors match E2E_TEST_PLAN_P0.md
   - Increase timeout if network is slow

3. **Tier dropdown color not showing?**
   - Open browser console, check for JavaScript errors
   - Verify `updateTierSelectColor()` function exists
   - Try hard refresh (Ctrl+Shift+R)

4. **Changes not persisting on reload?**
   - Check `/review/processing/` directory for CSV file
   - Verify file was actually modified (check timestamps)
   - Check Flask logs for save errors

5. **Email fuzzy matching not working?**
   - Verify fuzzy matching code is in processor.py
   - Try typos from E2E_TEST_PLAN_P0.md (gmai.com, gmial.com)
   - Check processor logs for validation output

---

## Important Notes for Agent

- **Don't modify code** while testing (just observe & report)
- **Use fresh browser context** (no cached data between tests)
- **Clear review/processing/ directory** between test runs if needed
- **Monitor browser console** for JavaScript errors during tests
- **Test in Chromium** (primary browser, CSS may differ in Firefox)
- **Document everything** - screenshots help when debugging failures

---

## Files You'll Reference

```
aws_nonprofit_toolkit/Givebutter/
├── FEATURE_OVERVIEW_FOR_AGENTS.md    ← Read first (context)
├── E2E_TEST_PLAN_P0.md               ← Follow these steps
├── scripts/uploader/
│   ├── app.py                        ← Flask server
│   └── templates/review.html         ← The UI you're testing
└── tests/e2e/
    └── test_e2e_agent_validation.py  ← Your test file (create this)
```

---

## Success Definition

🎯 **Agent completes testing when**:
- All 5 test cases executed
- Results documented (pass/fail for each)
- Issues identified (if any)
- Report generated

✅ **Perfect outcome**: All 5 tests PASS, no issues found, UI is production-ready

⚠️ **Acceptable outcome**: 4-5 tests PASS, minor issues identified, clear path to fix

❌ **Unacceptable outcome**: <3 tests PASS, blocking issues, needs investigation

---

## Questions for Agent

If you encounter issues, investigate and report:
1. **What's the exact error message?** (screenshot + console log)
2. **Which step fails?** (step number from E2E_TEST_PLAN_P0.md)
3. **Is it reproducible?** (happens every time or intermittent?)
4. **What's the expected vs actual behavior?** (what should happen vs what did happen)

This info helps the dev team fix bugs quickly.

---

## Good luck! 🚀

You're testing a critical workflow that operators use daily. Your thorough testing ensures a smooth experience for end users.

If you find bugs → document them clearly → dev team fixes them → operators happy.

**Report your findings back when complete.**

