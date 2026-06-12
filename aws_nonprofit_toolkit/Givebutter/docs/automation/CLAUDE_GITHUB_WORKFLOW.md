# Claude Code GitHub Automation Workflow

This document describes the GitHub Actions workflows for integrating Claude Code into the development and QA processes.

**Status:** Automated Developer Workflow + Manual QA - Claude Code creates PRs automatically, humans review and merge.

---

## Overview

Two GitHub Actions workflows enable Claude Code automation:

1. **Developer Workflow** (`.github/workflows/claude-dev.yml`)
   - Triggered by `@claude` mention in issue/PR comments
   - Uses official **anthropics/claude-code-action**
   - Claude Code creates/updates branches and opens PRs
   - No automatic merges (human approval required)
   - Comprehensive scope guardrails enforced

2. **QA Workflow** (`.github/workflows/claude-qa.yml`)
   - Triggered by `needs-qa` label or manual trigger
   - Runs full test suite (unit + integration)
   - Posts test results as PR comment
   - Uploads test artifacts for review
   - Checks for forbidden patterns/vocabulary

---

## Developer Workflow

### Official GitHub Action

**Name:** `anthropics/claude-code-action`
**Source:** https://github.com/anthropics/claude-code-action

### How to Trigger

**Method 1: Issue Comment (Recommended)**

```
@claude Update the PHASE1A_CLOSEOUT doc to include link to Phase 1B schema proposal
```

**Method 2: PR Review Comment**

```
@claude Add test for new export card field validation
```

**Method 3: Manual Trigger**

Go to GitHub Actions → "Claude Code Developer Agent" → "Run workflow"
- Enter issue/PR number
- Enter task description (up to 2000 characters)

### What Happens (Full Automated Flow)

1. **Developer creates issue** or PR with task description
2. **Developer comments:** `@claude [task description]`
3. **Workflow detects @claude mention** and extracts task
4. **Claude Code Action starts** with:
   - Repository context
   - Task description
   - Comprehensive guardrails
   - Timeout protection (25 minutes)
5. **Claude Code:**
   - Reviews issue/PR context
   - Creates a new branch (e.g., `docs/add-phase1b-section`)
   - Makes changes on the branch
   - Creates a PR with summary
   - Posts summary comment to issue
6. **Workflow completes** with result summary
7. **Developer/QA:**
   - Reviews PR created by Claude Code
   - Adds `needs-qa` label if QA needed
   - Triggers QA workflow automatically
   - Reviews test results
   - Approves and merges PR

### Scope Guardrails (Enforced)

Claude Code is instructed NOT to:

- ❌ Modify application code unless explicitly requested
- ❌ Modify tests unless explicitly requested
- ❌ Add database or persistence layer
- ❌ Add frontend runtime (React, Node, Vite, etc.)
- ❌ Add deployment automation
- ❌ Push directly to main branch
- ❌ Auto-merge PRs

Claude Code MUST:

- ✅ Create a new branch for all changes
- ✅ Create a PR (do not auto-merge)
- ✅ Preserve Phase 0 UI/UX for migrations
- ✅ Preserve DonorTrust guardrails
- ✅ Add `needs-qa` label if QA is needed

### Example: Documentation Update

```
1. Issue created: "Add Phase 1B readiness guide"
2. Comment: @claude Create comprehensive Phase 1B readiness document
3. Workflow triggered: Claude Code starts
4. Claude Code:
   - Creates branch: docs/phase1b-readiness
   - Creates file: docs/Phase_1B_READINESS.md
   - Writes comprehensive content
   - Creates PR: "docs: Add Phase 1B readiness guide"
   - Comments: "PR #42 created with Phase 1B readiness documentation"
5. Workflow completes: Success summary posted
6. Developer:
   - Reviews PR #42
   - Adds label: needs-qa
   - QA workflow runs tests
   - QA posts result comment
   - Developer approves and merges
7. Done: Documentation is updated on main branch
```

---

## Complete Workflow Examples

### Example 1: Bug Fix (Code + Tests)

```
1. Issue: "Export card title field not mapping correctly"
2. Developer comments: @claude Write tests for export card title mapping, then fix the issue
3. Claude Code:
   - Creates branch: fix/export-card-title
   - Adds test: test_export_card_title_mapping()
   - Implements fix in fixtures or service
   - Creates PR #43: "fix: Map export card name to title field"
4. Developer reviews PR, adds label: needs-qa
5. QA workflow:
   - Runs all tests: 335 passing
   - Posts: "✅ All tests passed (335 total)"
6. Developer approves PR #43
7. Merge: Changes are on main
```

### Example 2: Feature with Phase 1B Planning

```
1. Issue: "Plan Phase 1B database migration strategy"
2. Comment: @claude Create Phase 1B database migration guide with schema proposal
3. Claude Code:
   - Creates branch: docs/phase1b-database-guide
   - Creates: docs/PHASE1B_DATABASE_MIGRATION.md
   - Adds: Schema proposal, migration sequence, guardrails
   - Creates PR #44: "docs: Add Phase 1B database migration guide"
4. Developer reviews PR
5. Add label: needs-qa (for spell-check and link validation)
6. QA runs, posts results
7. Merge: Guide is available
```

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

### ANTHROPIC_API_KEY (Required for Developer Workflow)

**Purpose:** Authentication for Claude Code GitHub Action

**How to obtain:**
1. Go to https://console.anthropic.com
2. Sign in with your Anthropic account
3. Navigate to API keys section
4. Create new API key or copy existing key
5. Format: `sk-ant-...`

**How to set in GitHub:**

1. Go to your GitHub repository
2. Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. **Name:** `ANTHROPIC_API_KEY` (exact case)
5. **Value:** Paste your Anthropic API key
6. Click "Add secret"

**Scope:** This repository only (not organization-wide)

**Security:**
- ✅ Never commit API key to repo
- ✅ Never log API key in workflow output
- ✅ Rotate periodically (quarterly recommended)
- ✅ Use GitHub's secret masking (automatic)

**Verification:**

Once set, verify in workflow:
```yaml
- name: Validate ANTHROPIC_API_KEY Secret
  run: |
    if [ -z "${{ secrets.ANTHROPIC_API_KEY }}" ]; then
      echo "❌ ERROR: Secret not set"
      exit 1
    fi
    echo "✅ Secret is configured"
```

### QA Workflow Secrets

**None required** - QA workflow only runs tests, no API calls needed.

---

## Expected PR Workflow

### Automated Developer + QA Workflow

**Simplified Process:**

```
1. Developer creates GitHub issue with task
2. Developer comments: @claude [task description]
3. Claude Code creates PR automatically
4. Developer adds label: needs-qa
5. QA workflow runs automatically
6. QA posts test results
7. Developer/reviewer approves
8. Merge when ready
```

### Real Example: Phase 1B Documentation

```
1. Issue: "Create Phase 1B database migration guide"
2. Comment: @claude Create comprehensive guide for Phase 1B database migration including schema proposal and rollback procedures
3. Claude Code (automated):
   - Creates branch: docs/phase1b-database-guide
   - Creates file: docs/PHASE1B_DATABASE_MIGRATION.md
   - Writes guide with schema, procedures, checklist
   - Creates PR #45: "docs: Add Phase 1B database migration guide"
   - Posts comment: "PR #45 created with Phase 1B database migration guide"
4. Workflow completes: ✅ Success summary posted to issue
5. Developer/QA:
   - Reviews PR #45
   - Adds label: needs-qa
6. QA workflow (automatic):
   - Runs unit/integration tests: ✅ All 335 passing
   - Checks for forbidden patterns: ✅ None found
   - Posts: "✅ QA Report: All tests passing, no issues detected"
7. Reviewer:
   - Approves PR #45
   - Merges to main
8. Done: Documentation is live
```

### Real Example: Feature with Code and Tests

```
1. Issue: "Export card title field mapping bug"
2. Comment: @claude Write test and fix for export card title field not mapping from 'name' to 'title'
3. Claude Code (automated):
   - Creates branch: fix/export-card-title-mapping
   - Adds test: test_export_card_title_mapping()
   - Implements fix in service_contracts.py
   - Creates PR #46: "fix: Map export card name field to title"
   - Posts comment: "PR #46 created with test and fix"
4. Workflow completes: ✅ Success summary posted to issue
5. Developer:
   - Reviews PR #46
   - Checks code changes look correct
   - Adds label: needs-qa
6. QA workflow (automatic):
   - Runs all tests: ✅ 336 passing (new test included)
   - Checks no forbidden patterns: ✅ None found
   - Posts: "✅ QA Report: All 336 tests passing, code quality check passed"
7. Reviewer:
   - Approves PR #46
   - Merges to main
8. Done: Fix is deployed
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
| Issue creation | Developer | Before @claude comment |
| Task clarity | Developer | In @claude comment |
| Scope guardrails | Automated | Claude Code enforces |
| Code review | Reviewer | Before merge |
| PR approval | Reviewer | Final gate |
| Merge | Repo maintainer | After all approvals |
| Deployment | DevOps | After merge (separate) |
| Cost approval | Tech lead | Quarterly review |
| Secrets rotation | Admin | Quarterly |

### Fully Automated (No Human Step)

- ✅ Branch creation (Claude Code)
- ✅ Commit creation (Claude Code)
- ✅ PR creation (Claude Code)
- ✅ PR summary (Claude Code)
- ✅ Test running (QA workflow)
- ✅ Test reporting (QA workflow)

### Never Automated (Always Human)

- ❌ Issue creation (developer decides what to build)
- ❌ Scope definition (developer specifies constraints)
- ❌ Code review (humans review code quality)
- ❌ PR approval (humans approve before merge)
- ❌ Merge decision (maintainers decide when to merge)
- ❌ Deployment (separate manual process)

---

## Usage Examples

### Example 1: Documentation Update (Simplest)

**Issue:** "Add Phase 1B database migration guide"

```
1. Developer creates issue
2. Developer comments: @claude Create comprehensive Phase 1B database migration guide
3. Claude Code Action:
   - Creates branch: docs/phase1b-migration
   - Creates file: docs/PHASE1B_DATABASE_MIGRATION.md
   - Writes complete guide with schema, procedures
   - Creates PR #50: "docs: Add Phase 1B database migration guide"
4. Workflow completes and posts summary
5. Developer reviews PR #50
6. Developer adds label: needs-qa (optional for docs)
7. QA workflow (if label added):
   - Runs tests: ✅ All passing
   - Posts: "✅ QA: All tests pass, no issues"
8. Developer approves and merges PR #50
9. Done: Guide is live on main
```

### Example 2: Bug Fix with Tests

**Issue:** "Export card title field not mapping correctly"

```
1. Developer creates issue with details
2. Developer comments: @claude Write test for export card title mapping issue, then implement fix
3. Claude Code Action:
   - Creates branch: fix/export-card-title
   - Creates test: test_export_card_title_mapping()
   - Implements fix in service code
   - Creates PR #51: "fix: Map export card name field to title"
4. Workflow completes
5. Developer reviews PR #51 (code + test visible)
6. Developer adds label: needs-qa (required for code changes)
7. QA workflow (automatic):
   - Runs all tests: ✅ 336 passing (includes new test)
   - Posts: "✅ QA Report: All 336 tests passing"
8. Developer approves PR #51
9. Merge: Fix is on main
10. Done: Bug is fixed
```

### Example 3: Feature with Code and Tests

**Issue:** "Implement Phase 1B repository interface protocol"

```
1. Developer creates issue with requirements
2. Developer comments: @claude Design and implement RepositoryProtocol base class with tests
3. Claude Code Action:
   - Creates branch: feature/phase1b-repository-protocol
   - Adds: service_contracts.py RepositoryProtocol class
   - Adds: tests/unit/test_repository_protocol.py with 20 tests
   - Creates PR #52: "feat: Add RepositoryProtocol for Phase 1B database abstraction"
4. Workflow completes
5. Developer reviews PR #52 (interface + tests)
6. Developer adds label: needs-qa
7. QA workflow:
   - Runs tests: ✅ 355 passing (20 new tests)
   - Posts: "✅ QA Report: All 355 tests passing"
8. Architecture reviewer approves design
9. Merge: Protocol is integrated
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

### Phase 2: Advanced Monitoring and Notifications

- Slack notifications (PR created by Claude Code, tests completed)
- Email summaries (weekly QA results)
- Cost tracking dashboard (API usage per workflow)
- GitHub issue auto-close on PR merge
- Slack/Discord PR mention notifications
- Custom guardrail violations reporting

### Phase 3: Workflow Optimization

- Parallel test execution (faster QA feedback)
- Caching for large test suites
- Incremental testing (only changed components)
- Performance regression detection
- Test coverage tracking per PR

### Phase 4: Multi-Repository Support

- Organize secrets across multiple repos
- Shared workflow templates
- Cross-repo PR linking
- Centralized cost and quota management

### Phase 5: Deployment Automation (Future - Separate Workflow)

- Promote to staging/production (manual gate)
- Automated rollback on failure (with safeguards)
- Blue-green deployments
- Canary releases with monitoring

---

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Anthropic Claude Documentation](https://docs.anthropic.com)
- [Repository Secrets Setup](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)

---

## FAQ

**Q: Do I need to set up ANTHROPIC_API_KEY?**
A: Yes! It's required for the developer workflow to run Claude Code. See "Required GitHub Secrets" section for setup instructions. Get your key from https://console.anthropic.com.

**Q: Can the workflow automatically merge my PR?**
A: No, intentionally. All merges require human approval. Claude Code creates the PR but cannot merge it.

**Q: Will the workflow cost money?**
A: GitHub Actions are free tier (2000 min/month). Anthropic API calls for Claude Code will incur costs - see your Anthropic billing dashboard. Estimate: ~$0.01-0.05 per task depending on complexity.

**Q: What if Claude Code makes a mistake?**
A: Review the PR, request changes via GitHub UI, then comment: `@claude Apply the suggested changes`. Claude Code will update the branch.

**Q: What if tests fail?**
A: QA workflow reports failures in the PR comment. Review failures and comment: `@claude Fix the failing tests`. Claude Code will implement fixes and push to the same branch/PR.

**Q: Can I ask Claude Code to make app code changes?**
A: Only if absolutely necessary and you explicitly state it. Default: no app code changes. Example: `@claude Update app.py to add the new export route (app code change requested)`

**Q: How long do test results stay available?**
A: Artifacts are retained for 30 days. Download from GitHub Actions tab → workflow run → Artifacts section.

**Q: Can I trigger the QA workflow without the needs-qa label?**
A: Yes, manually via GitHub Actions UI → "Claude Code QA Workflow" → "Run workflow" button.

**Q: What if the API key expires?**
A: Generate a new key at https://console.anthropic.com, update the GitHub secret, and workflows will use the new key immediately.

**Q: Why does the workflow have a 25-minute timeout?**
A: Safety guard against hung processes or runaway API calls. Most tasks complete in 2-5 minutes. Contact @anthropic if you need a longer timeout for complex tasks.

**Q: Can I use Claude Code for deployment?**
A: No, intentionally blocked. Deployment automation is not included in this workflow. Use a separate deployment tool.

---

**Last Updated:** 2026-06-11
**Status:** Automated Developer Workflow (with Claude Code GitHub Action) + Manual QA - Claude Code creates PRs automatically, humans review and merge.
