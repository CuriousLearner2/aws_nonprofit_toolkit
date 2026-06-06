# Agent Testing Kit - Givebutter Processor UI

Complete testing documentation package for Claude agents to validate the Givebutter Processor donation review UI using Playwright.

---

## 📁 Folder Structure

```
testing/agent/
├── README.md                          ← You are here
├── AGENT_TESTING_PROMPT.md           ← START HERE (copy this to agent)
├── FEATURE_OVERVIEW_FOR_AGENTS.md    ← Background & context
└── E2E_TEST_PLAN_P0.md               ← Test procedures & steps
```

---

## 🚀 How to Use This Kit

### Option 1: Direct Agent Handoff (Recommended)

1. Copy the entire content of **AGENT_TESTING_PROMPT.md**
2. Paste it into a new Claude conversation
3. Agent reads the prompt and executes tests
4. Agent reports findings

### Option 2: Agent Folder Access

If agent has file access, point it to this folder:
```
/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/testing/agent/
```

Agent will:
1. Read `AGENT_TESTING_PROMPT.md` (mission & overview)
2. Read `FEATURE_OVERVIEW_FOR_AGENTS.md` (learn what features do)
3. Follow `E2E_TEST_PLAN_P0.md` (execute test procedures)

---

## 📄 Files Explained

### 1. AGENT_TESTING_PROMPT.md
**What**: Self-contained prompt for testing agent  
**Size**: ~7.7 KB  
**Contains**:
- Mission statement
- Prerequisites (how to start Flask server)
- 5 test cases to execute
- Success criteria
- What to report back
- Troubleshooting guide

**When to use**: Copy this directly to an agent conversation

---

### 2. FEATURE_OVERVIEW_FOR_AGENTS.md
**What**: Background & context about the app  
**Size**: ~9.9 KB  
**Contains**:
- What the app does (why it matters)
- The 3-step operator workflow
- Key features & their purpose:
  - Inline editing with auto-tier update
  - Editable tier dropdown
  - Fuzzy email domain matching
  - Auto-save architecture
  - Bulk actions
- Data flow architecture
- How tests exercise features
- Technical behaviors to verify

**When to use**: Agent reads this first to understand context

---

### 3. E2E_TEST_PLAN_P0.md
**What**: Detailed test procedures  
**Size**: ~8.5 KB  
**Contains**:
- 5 P0 test cases with step-by-step procedures
- Success criteria for each test
- CSS selectors for all UI elements
- Sample test CSV (with expected tier distribution)
- Browser setup instructions
- Troubleshooting guide
- Pass/fail scoring

**When to use**: Agent executes test procedures from this file

---

## ✅ What Gets Tested

The **5 Critical (P0) Test Cases**:

1. **Upload CSV & Process** - File appears in review queue with correct tier counts
2. **Inline Editing + Auto-Update** - Edit phone → tier changes WARNING→PASS automatically
3. **Tier Override** - Manually change FAIL (red) → PASS (green) with color feedback
4. **Email Fuzzy Matching** - Catch typo `gmai.com`, show suggestion, apply fix
5. **Bulk Actions & Complete** - Approve all records → confirmation → Done → workflow ends

---

## 🎯 Success Criteria

**PASS**: All 5 tests pass
- ✅ No JavaScript errors
- ✅ Colors display correctly (green/yellow/red)
- ✅ Auto-save persists changes
- ✅ Tier auto-updates when issues fixed
- ✅ Bulk actions work with confirmation

**FAIL**: Any test fails or criteria not met
- Document which test failed
- Provide screenshots/console errors
- Steps to reproduce

---

## 🛠 Prerequisites

Before agent starts testing:

```bash
# 1. Start Flask server
cd /Users/gautambiswas/Claude\ Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter
source venv/bin/activate
python3 scripts/uploader/app.py

# 2. Verify server running
# Should see: "Running on http://127.0.0.1:8000"

# 3. In another terminal, agent can run Playwright tests
pytest tests/e2e/test_e2e_agent_validation.py -v
```

---

## 📊 Expected Output from Agent

Agent should report:

```
TEST RESULTS SUMMARY
====================
Total Tests: 5
Passed: 5 ✅
Failed: 0 ❌
Status: PASS

Test Details:
✅ Test 1: Upload CSV & Process
✅ Test 2: Inline Editing + Auto-Update
✅ Test 3: Tier Override (Colors correct)
✅ Test 4: Email Fuzzy Matching
✅ Test 5: Bulk Actions & Complete

Issues Found: None
Recommendations: None
```

---

## 🔍 Quick Reference: Key URLs & Paths

**Flask Server**: `http://127.0.0.1:8000`

**Flask App**: `/aws_nonprofit_toolkit/Givebutter/scripts/uploader/app.py`

**UI Templates**: `/aws_nonprofit_toolkit/Givebutter/scripts/uploader/templates/review.html`

**Processing Dir**: `/aws_nonprofit_toolkit/Givebutter/review/processing/`

**Output Dir**: `/aws_nonprofit_toolkit/Givebutter/review/approved/` (and followup/, rejected/)

---

## 🐛 Troubleshooting Common Issues

| Problem | Solution |
|---------|----------|
| Flask server won't start | Port 8000 in use: `lsof -i :8000` and kill process |
| Tests timeout | Flask server not running, increase wait timeout |
| Colors not showing | Check browser console for JS errors, hard refresh (Ctrl+Shift+R) |
| Changes not persisting | Verify CSV file in `/review/processing/` updated (check timestamp) |
| Tier not auto-updating | Verify processor.py and recalculate-tier endpoint working |

---

## 📝 Notes

- **Don't modify code** while testing (observe & report)
- **Use fresh browser context** between tests
- **Monitor console** for JavaScript errors
- **Document everything** with screenshots if possible
- **Test in Chromium** (Firefox may have CSS differences)

---

## 🔗 Related Documentation

Outside this folder:

- `README.md` - Feature list & quick start
- `OPERATOR_MANUAL.md` - How users operate the app
- `PROCESSOR_GUIDE.md` - Validation rules & technical details

---

## 📞 Contact

Questions about tests? Check `AGENT_TESTING_PROMPT.md` troubleshooting section.

Issues with the app? Check `FEATURE_OVERVIEW_FOR_AGENTS.md` for architectural details.

---

**Last Updated**: 2026-06-05  
**Version**: 1.0  
**Status**: ✅ Ready for Agent Testing

