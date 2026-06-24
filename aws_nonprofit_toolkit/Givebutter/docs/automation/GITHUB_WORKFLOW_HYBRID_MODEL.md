# GitHub Workflow: Hybrid Local + Automated Model

This document describes the GitHub Actions workflow approach for Givebutter Phase 1A and Phase 1B.

**Model:** Local Claude Code (developer) + GitHub Actions (automated QA/guardrails)

---

## Workflow Model

### Local Development (Primary)
- **Who:** Developer (human) or Claude Code (local CLI)
- **What:** Create branches, make code changes, write tests, commit
- **How:** `git checkout -b feature/...` → code → test locally → `git push`
- **Tools:** Claude Code (local), Git, IDE, test runner

### GitHub Actions (Automated Verification)
- **Who:** GitHub Actions (deterministic, no external AI)
- **What:** Run tests, check for forbidden patterns, verify scope compliance
- **When:** Automatically on PR creation/update, or when `needs-qa` label added
- **Result:** Test results + guardrail check posted as PR comment

---

## GitHub Actions Workflows

### 1. Test & Guardrails Workflow

**File:** `.github/workflows/claude-qa.yml`

**Triggers:**
- PR created/updated (always runs)
- `needs-qa` label added (explicit QA request)
- Manual trigger via workflow_dispatch

**Jobs:**

#### qa-check
- Installs dependencies
- Runs unit tests (tests/unit/)
- Runs integration tests (tests/integration/)
- Posts test results as PR comment
- Uploads artifacts (30-day retention)

#### code-quality-check
- Scans for forbidden technology:
  - `from sqlalchemy` (ORM forbidden)
  - `import React` (frontend runtime forbidden)
- Scans for forbidden vocabulary:
  - merge, merged, auto-apply, approve-all, sync, synced, CRM-writeback, writeback, finalized
  - And others per DonorTrust Phase 1A guardrails
- Verifies scope: warns if app code modified in documentation-only PRs

#### e2e-smoke-test
- **Trigger:** Opt-in via `e2e-check` label only (does not run on normal PRs)
- **Test:** Single representative E2E test (test_invalid_email_updates_visible_row_status_and_issues)
- **Purpose:** Validates Flask startup and browser integration without slowing normal CI
- **Informational Only (Initial Rollout):** Does not block PR merge (continue-on-error: true). This is temporary while gathering CI stability data; after roughly 10 successful labeled PR runs or 1–2 weeks without flaky failures, we can switch the smoke job to blocking.
- **Setup:** Installs Playwright, launches Chromium browser, seeds test database
- **Artifact:** Uploads e2e-smoke-results.txt (30-day retention)
- **Timeout:** 15 minutes (allows for browser startup overhead)

**Example Output:**
```
## 🧪 QA Report

=== QA Test Summary ===

**Unit Tests:** 48 passed, 0 failed
**Integration Tests:** 26 passed, 0 failed

**Status:**
✅ All tests passed

### Next Steps:
- Review test failures in the Actions logs
- Upload QA report artifacts from workflow
- Mark as needs-qa or approved based on results
```

---

## Workflow: Local Developer (Recommended for Phase 1B)

### Example: Add New Feature

```bash
# 1. Create local branch
git checkout -b feature/new-householder-field

# 2. Make changes, write tests
# ... edit scripts/householder/X_service.py
# ... edit tests/unit/test_X_service.py

# 3. Run tests locally
pytest tests/unit/ tests/integration/ -v

# 4. Commit and push
git add scripts/ tests/ docs/
git commit -m "feat: add new householder field

- Added field to service contract
- Updated repository mapping
- Added unit tests for new field
- Added integration test for route

Co-Authored-By: Claude <claude@anthropic.com>"

git push origin feature/new-householder-field
```

### What GitHub Actions Does

1. **On PR Creation:**
   - Runs full test suite automatically
   - Checks for forbidden patterns
   - Posts test results as comment
   - No merge action taken

2. **On e2e-check Label (Optional):**
   - Runs single E2E smoke test (Flask + Playwright)
   - Does NOT slow down normal PRs (label gating)
   - Results posted as artifact for review

3. **Review Process (Human):**
   - Developer reviews test results in PR
   - If tests fail: developer fixes locally, pushes again
   - If tests pass: reviewer approves and merges manually

---

## CODEOWNERS (If Used)

Optional file for automatic reviewer assignment:

```
# Default reviewer for all changes
* @CuriousLearner2

# Phase 1B-specific reviewers (when added)
scripts/householder/ @CuriousLearner2
docs/implementation/ @CuriousLearner2
```

---

## Scope Guardrails (Enforced by Tests)

### Forbidden in Phase 1A-1B

❌ Database modifications (ORM, migrations, persistence)
❌ Frontend runtime additions (React, Node, Webpack, Vite, Next.js)
❌ Automatic approval workflows (auto-apply, auto-merge, sync)
❌ CRM writeback or Givebutter API calls
❌ Deployment automation or CI/CD modifications
❌ Concurrent request handling beyond Phase 0 UI

### Required in Phase 1A-1B

✅ Fixture-backed service layer for all routes
✅ Frozen dataclasses for view models
✅ to_dict() / to_template_dict() adapter methods
✅ Phase 0 UI exactly preserved
✅ All DonorTrust guardrails honored
✅ No mutation of raw import records

---

## Local Testing Checklist (Before Pushing)

```bash
# 1. Run unit tests
pytest tests/unit/ -v

# 2. Run integration tests
pytest tests/integration/ -v

# 3. Verify no forbidden patterns
grep -r "from sqlalchemy" scripts/ tests/ || echo "✅ No SQLAlchemy"
grep -r "import React" scripts/ || echo "✅ No React"

# 4. Verify no forbidden vocabulary
grep -ri "auto-apply\|sync\|CRM-writeback" scripts/uploader/app.py || echo "✅ No forbidden words"

# 5. Check all targeted tests pass (Phase 1A verification)
pytest tests/unit/test_*.py tests/integration/test_*.py -v --tb=short

# 6. Check tests that currently pass still pass
pytest tests/ -v --tb=short

# 7. Optional: Run E2E smoke test locally (requires playwright install)
pytest tests/e2e/test_validation_review_dom.py::test_invalid_email_updates_visible_row_status_and_issues -v
```

---

## E2E Smoke Test (Label-Gated)

### How to Trigger E2E Smoke Test on Your PR

1. **Add the `e2e-check` label** to your PR
2. GitHub Actions automatically runs the e2e-smoke-test job (separate from unit/integration)
3. Results appear in artifacts > e2e-smoke-results
4. Test passes or fails independently (does not block merge)

### Why Not Run E2E on Every PR?

- **Browser startup overhead:** ~10 seconds per test
- **Normal PRs focus:** Unit + integration tests (12 seconds, no browser)
- **Selective coverage:** E2E smoke test verifies Flask + Playwright interaction only
- **Cost:** Chromium installation + headless browser launch adds ~30 seconds total

### When Should I Add e2e-check?

- Making changes to **validation review UI** or **form handling**
- Adding/modifying **E2E test coverage**
- Testing **Flask route changes** that affect browser rendering
- **Optional:** For documentation-only changes (not needed)

---

## Future: Automated Developer Workflow (Phase 1B+)

Once Phase 1B is stable and tested, GitHub Actions can be enhanced to include:

- **anthropics/claude-code-action** for `@claude` mentions
- Automated branch/PR creation for documentation updates
- Automated test fixes for minor test failures
- Automated guardrail verification

**Guardrail:** This requires explicit authorization in a new phase gate. Not recommended until Phase 1B testing is complete.

---

## FAQ

### Why not use Claude Code GitHub Action now?

1. **Phase 1A just completed** - need time for stability verification
2. **Phase 1B is untested** - database migrations add risk
3. **Hybrid model is simpler** - local developer tools + automated QA
4. **Easier debugging** - humans can reproduce test failures locally

### How do I request QA on my PR?

1. Add `needs-qa` label to PR
2. Or PR is automatically QA'd on creation
3. Or manually trigger: workflow_dispatch in Actions tab

### How do I request E2E smoke test on my PR?

1. Add `e2e-check` label to your PR
2. e2e-smoke-test job automatically runs (separate from unit/integration)
3. Check artifacts for e2e-smoke-results.txt

### What if a test fails?

1. GitHub Actions posts test results as PR comment
2. Download artifacts for detailed logs
3. Fix locally and push new commit
4. GitHub Actions automatically re-runs tests

### Can Claude Code modify the app code?

**Locally:** Yes, local Claude Code CLI is the primary developer tool.
**Via GitHub:** No, anthropics/claude-code-action not currently configured. Humans review/merge all GitHub PRs.

### What's the difference between needs-qa and automatic QA?

- **Automatic:** All PRs run tests when created/updated
- **needs-qa:** Explicit label for extended review (same tests, explicit flagging)

### What's the difference between needs-qa and e2e-check?

- **needs-qa:** Runs unit + integration tests (12 seconds, no browser)
- **e2e-check:** Runs single E2E smoke test (validates Flask + Playwright, ~30 seconds including browser startup)
- **Both independent:** Can use one, both, or neither depending on your change

---

## Implementation Status

| Component | Status | File |
|-----------|--------|------|
| Test & Guardrails Workflow | ✅ Active | `.github/workflows/claude-qa.yml` |
| E2E Smoke Test (Opt-In) | ✅ Active | `.github/workflows/claude-qa.yml` (e2e-smoke-test job) |
| Developer Automation (Claude Action) | ⏳ Not configured | (future: `.github/workflows/claude-dev.yml`) |
| CODEOWNERS | ✅ Optional | `.github/CODEOWNERS` |
| Hybrid Model Documentation | ✅ This document | `docs/automation/GITHUB_WORKFLOW_HYBRID_MODEL.md` |

---

## Next Steps

1. **Phase 1B:** Test the hybrid model with a few sample features
2. **Incident Monitoring:** Track test pass rate and feedback
3. **E2E Smoke Test Usage:** Gather feedback on opt-in label gating
4. **Phase 1B Completion:** Evaluate if automation can be expanded
5. **Phase 2:** Plan anthropics/claude-code-action integration (if beneficial)

---

**Last Updated:** 2026-06-23
**Model Status:** Hybrid (Local Developer + GitHub Automated QA + Opt-In E2E Smoke)
**Recommended for:** Phase 1B development and testing
