# Claude Code GitHub Automation Workflow

This document describes the GitHub Actions workflows for integrating Claude Code into the development and QA processes.

**Status:** Pilot/MVP - Manual-only, non-blocking workflows. No automatic code changes.

---

## Overview

Two GitHub Actions workflows enable Claude Code automation:

1. **Developer Workflow** (`.github/workflows/claude-dev.yml`)
   - Triggered by `@claude` mention in issue/PR comments
   - Logs task description and waits for human action
   - Informs developers to use Claude Code locally

2. **QA Workflow** (`.github/workflows/claude-qa.yml`)
   - Triggered by `needs-qa` label or manual trigger
   - Runs full test suite (unit + integration)
   - Posts test results as PR comment
   - Uploads test artifacts for review
   - Checks for forbidden patterns/vocabulary

---

## Developer Workflow

### How to Trigger

**Method 1: Issue Comment (Recommended)**

```
@claude Update the PHASE1A_CLOSEOUT doc to include link to Phase 1B schema proposal
```

**Method 2: PR Comment**

```
@claude Add test for new export card field validation
```

**Method 3: Manual Trigger**

Go to GitHub Actions → "Claude Code Developer Agent" → "Run workflow"
- Enter issue/PR number
- Enter task description

### What Happens

1. Workflow detects `@claude` mention or manual trigger
2. Extracts task description
3. Posts a comment noting the workflow is **informational only**
4. Logs task details to workflow logs
5. **Does NOT automatically make changes** (current MVP limitation)

### Next Steps

1. Developer sees the workflow notification
2. Developer runs Claude Code locally:
   ```bash
   claude --code "Update the PHASE1A_CLOSEOUT doc..."
   ```
3. Developer reviews changes locally
4. Developer creates PR with changes
5. Developer requests review

### Limitations (Current MVP)

- ❌ No automatic code generation
- ❌ No automatic branch creation
- ❌ No automatic commits/pushes
- ⏳ Awaiting Anthropic Claude Code GitHub Action

**Rationale:** Safety-first. All code changes should be reviewed locally before pushing.

---

## QA Workflow

### How to Trigger

**Method 1: Label (Recommended)**

```bash
gh pr edit <PR_NUMBER> --add-label needs-qa
```

**Method 2: Manual Trigger**

Go to GitHub Actions → "Claude Code QA Workflow" → "Run workflow"
- Enter PR number

### What Happens

1. Workflow checks out PR code
2. Installs dependencies
3. Runs full test suite:
   - Unit tests: `tests/unit/`
   - Integration tests: `tests/integration/`
4. Generates test summary
5. Posts results as PR comment
6. Uploads test artifacts (results, logs)
7. Checks for forbidden patterns

### Example QA Report (Posted to PR)

```
## 🧪 QA Report

**Unit Tests:** 150 passed, 0 failed
**Integration Tests:** 183 passed, 0 failed

**Status:** ✅ All tests passed

### Next Steps:
- Review test results in Actions logs
- Verify no forbidden patterns detected
- Mark as approved or request changes
```

### Artifacts

Test results are uploaded and available for 30 days:
- `unit-test-results.txt` — Full unit test output
- `integration-test-results.txt` — Full integration test output
- `test-summary.txt` — Summary only

**To download:**
1. Go to GitHub Actions → "Claude Code QA Workflow" → latest run
2. Scroll to "Artifacts"
3. Download `qa-test-results`

### Forbidden Pattern Checks

Workflow automatically checks for:

**Forbidden Technologies:**
- SQLAlchemy ORM imports
- React imports

**Forbidden Vocabulary:**
- merge, merged
- auto-apply, approve-all
- sync, synced
- CRM-writeback, writeback
- finalized

**If violations found:** ❌ Test results are posted, violations are flagged

---

## Required GitHub Secrets

### For Claude Code Integration (Future)

When the Anthropic Claude Code GitHub Action becomes available:

**Secret: `ANTHROPIC_API_KEY`**
- Value: Your Anthropic API key
- Scope: This repository only (not organization)
- How to set: Settings → Secrets and variables → Actions → New repository secret
- Keep secure: Never commit, never log

**No secrets required for current MVP** (test-only workflows don't need API key)

### Setting Secrets

1. Go to GitHub repo → Settings
2. Click "Secrets and variables" → "Actions"
3. Click "New repository secret"
4. Name: `ANTHROPIC_API_KEY`
5. Value: `sk-ant-...` (from Anthropic console)
6. Click "Add secret"

---

## Expected PR Workflow

### Minimal Example: Documentation Update

```
1. Create issue: "Update Phase 1A docs"
2. Comment on issue: "@claude Add Phase 1B schema section"
3. Developer runs Claude Code locally
4. Developer commits changes to branch
5. Developer creates PR
6. Add label: "needs-qa"
7. QA workflow runs, posts test results
8. If tests pass: ✅ Ready for review
9. Team reviews and approves
10. Merge PR
```

### Test-Driven Example: New Feature

```
1. Create issue: "Add Phase 1B export format"
2. Comment: "@claude Write tests for new export format first"
3. Developer runs Claude Code locally
4. Developer tests changes locally: pytest tests/
5. Developer creates PR with tests
6. Add label: "needs-qa"
7. QA workflow runs full suite
8. If tests pass: ✅ Code review can proceed
9. Team reviews code
10. If approved: Merge and close issue
```

---

## Cost Control Practices

### GitHub Actions (Free Tier)

- ✅ 2000 free minutes/month per account
- ✅ Unlimited workflow runs for public repos
- Current workflows use ~5 minutes per run
- Estimate: 400+ runs/month possible (well under limit)

### Anthropic API (When Integrated)

- 🔑 Use repository secrets, never hardcoded keys
- ⏱️ Set timeout limits on API calls
- 📊 Monitor usage in Anthropic console
- 🚫 Implement circuit breakers for failed calls
- 💰 Document expected costs per workflow run

### Recommended Limits

```yaml
# Workflow timeout (safeguard against hung processes)
timeout-minutes: 30

# Per-job timeout
timeout-minutes: 15

# API call timeout (when integrated)
request-timeout: 60s
```

---

## Safety Guardrails

### No Automatic Merges

```yaml
# ❌ NOT ALLOWED
permissions:
  pull-requests: write
  contents: write  # Would allow auto-merge

# ✅ REQUIRED
permissions:
  contents: read
  pull-requests: read  # Read-only
```

### No Automatic Deployments

- Workflows are CI-only (test and report)
- No deployment triggers
- No automatic pushes to main
- All code changes require human review

### No Hardcoded Credentials

```yaml
# ❌ NOT ALLOWED
env:
  API_KEY: sk-ant-abc123

# ✅ REQUIRED
env:
  # Use GitHub secrets:
  # ANTHROPIC_API_KEY=sk-ant-...
```

### Least-Privilege Permissions

```yaml
permissions:
  contents: read          # ✅ Minimal (no write)
  pull-requests: read     # ✅ Read-only
  issues: read            # ✅ Read-only
  # Explicit: no secrets access, no deployment perms
```

### Manual Approval Points

1. **Developer Workflow:** Human must run Claude Code locally and create PR
2. **QA Workflow:** Results posted to PR, human reviews before merge
3. **Merge:** Human must manually merge PR (no auto-merge)
4. **Deploy:** Human must manually trigger deployment (separate workflow, not included)

---

## What Still Requires Human Approval

### Mandatory Human Decisions

| Decision | Who | When |
|----------|-----|------|
| Task clarification | Developer | Before running Claude Code |
| Code review | Code reviewer | Before merge |
| Merge | Repo maintainer | After approval |
| Deployment | DevOps/Maintainer | After merge |
| Cost approval | Tech lead | Before integrating expensive APIs |
| Secrets rotation | Admin | Quarterly |

### Not Automated

- ❌ Creating issues (humans do this)
- ❌ Writing code (Claude Code runs locally, humans decide to push)
- ❌ Approving PRs (code review is manual)
- ❌ Merging (human click required)
- ❌ Deploying (separate manual process)

---

## Usage Examples

### Example 1: Documentation-Only Update

**Issue:** "Add Phase 1B deployment guide"

```
1. Comment on issue: @claude Add deployment guide section to Phase 1B docs
2. Workflow logs: "Claude Code Agent: Processing request..."
3. Developer runs Claude Code: claude --code "Add deployment guide..."
4. Developer commits: git commit -m "docs: Add Phase 1B deployment guide"
5. Developer creates PR
6. Workflow: `needs-qa` label triggers QA
7. QA workflow: Runs tests, posts "✅ All tests passed" comment
8. Developer reviews QA report
9. Maintainer approves and merges
```

### Example 2: Bug Fix with Tests

**Issue:** "Fix export card title mapping"

```
1. Comment: @claude The export card title field is not mapping correctly from 'name' to 'title'
2. Developer runs Claude Code locally
3. Developer writes test first: `test_export_card_title_mapping()`
4. Developer runs tests: `pytest tests/unit/test_exports_service.py`
5. Developer implements fix
6. Developer commits: `git commit -m "fix: Map export card name field to title"`
7. Developer creates PR with test and fix
8. Add label: needs-qa
9. QA workflow runs full suite
10. QA posts: "✅ All 333 tests passed"
11. Code review approves
12. Maintainer merges
```

### Example 3: Test-Driven Development

**PR:** "Add Phase 1B database adapter pattern"

```
1. Comment: @claude Write comprehensive tests for DatabaseRepository pattern
2. Developer runs Claude Code
3. Developer creates test file: `tests/unit/test_database_repository.py`
4. Developer adds label: needs-qa
5. QA workflow detects needs-qa
6. QA runs: "✅ All 300+ tests still pass, 45 new tests added"
7. Developer implements DatabaseRepository
8. Developer verifies: `pytest tests/unit/test_database_repository.py -v`
9. Developer creates PR with tests and implementation
10. QA workflow runs again: "✅ All 345 tests pass"
11. Code review approves patterns and tests
12. Maintainer merges
```

---

## Troubleshooting

### Workflow Doesn't Trigger on @claude Comment

**Check:**
1. Are you a collaborator on the repo? (Contributors need write permission)
2. Is the workflow file in `.github/workflows/`?
3. Is the workflow enabled? (Settings → Actions → General → Workflows)
4. Correct syntax? `@claude [space] [task]`

**Fix:**
```bash
# Verify workflow is on main branch
git log -1 --oneline .github/workflows/claude-dev.yml

# Re-trigger manually via Actions UI
```

### QA Workflow Doesn't Run on needs-qa Label

**Check:**
1. Is the label name exactly `needs-qa` (case-sensitive)?
2. Is the workflow enabled?
3. Correct branch? (Only main branch by default)

**Fix:**
```bash
# Manually trigger via Actions UI
# Or re-label: remove needs-qa, then add again
```

### Test Results Don't Post to PR

**Check:**
1. Is workflow run on PR (not issue)?
2. Are tests completing (check timeout)?
3. Is GitHub app authorized? (Settings → Applications)

**Fix:**
```bash
# Check workflow logs
# Re-run workflow via Actions UI
# Check for errors in workflow output
```

---

## Future Enhancements

### Phase 2: Anthropic Claude Code GitHub Action

Once available, add:
- Direct Claude Code invocation from workflow
- Output analysis and pull request generation
- Cost tracking per run
- Rate limiting and quotas

### Phase 3: Automatic PR Generation

```yaml
# Future (NOT CURRENT):
# - Claude Code generates branch
# - Claude Code creates commit
# - Claude Code opens PR
# - Human reviews and merges

# Current (MVP):
# - Workflow logs task
# - Developer uses Claude Code locally
# - Developer creates PR manually
```

### Phase 4: Integration with Other Tools

- Slack notifications (workflow completed, tests failed)
- Email summaries (daily test results)
- Linear/GitHub issue linking (auto-close on merge)
- Slack/Discord PR notifications

---

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Anthropic Claude Documentation](https://docs.anthropic.com)
- [Repository Secrets Setup](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)

---

## FAQ

**Q: Do I need to set up ANTHROPIC_API_KEY for the current workflows?**
A: No. Current workflows (test-only) don't use the API key. You'll only need it when Claude Code GitHub Action integration is added.

**Q: Can the workflow automatically merge my PR?**
A: No, intentionally. All merges require human approval.

**Q: Will the workflow cost money?**
A: Current workflows are free (GitHub Actions free tier). API usage costs will come later if/when Claude Code GitHub Action is integrated.

**Q: What if tests fail? Can I fix them in the workflow?**
A: No. The workflow reports failures. You must fix them locally, commit, and push a new version.

**Q: How long do test results stay available?**
A: Artifacts are retained for 30 days. You can download them anytime from the Actions tab.

**Q: Can I trigger the QA workflow without the needs-qa label?**
A: Yes, manually via GitHub Actions UI → "Run workflow" button.

---

**Last Updated:** 2026-06-11
**Status:** Pilot/MVP - All workflows are manual-only, non-blocking, and require human approval for merges.
