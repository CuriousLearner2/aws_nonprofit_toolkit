# Developer Reference
## Technical Architecture & Implementation Guide

---

## Overview

This document covers the technical architecture, rule systems, Claude AI integration, and maintenance procedures for developers and technical maintainers.

**See [OPERATOR_MANUAL.md](../OPERATOR_MANUAL.md) for user-facing documentation.**

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                        Flask Uploader                        │
│                  (scripts/uploader/app.py)                   │
│              Simple web form on :5000/upload                 │
└──────────────────────────────┬──────────────────────────────┘
                               │ (CSV files)
                               ↓
                    intake/new/ (upload folder)
                               │
                               ↓ (auto-watched)
┌──────────────────────────────────────────────────────────────┐
│                   Main Processor v2.3                        │
│            (scripts/processor_v2_3.py)                       │
│  1. Load rules from config/rules/rules_v2.x.json            │
│  2. Process each CSV in intake/new/                         │
│  3. Flag rows that don't match rules                        │
│  4. Output flagged rows to review/flagged/                  │
│  5. Move original to intake/archive/                        │
└──────────────────────────────────────────────────────────────┘
                               │
                ┌──────────────┼──────────────┐
                ↓              ↓              ↓
        review/flagged/  intake/archive/  intake/failed/
        (needs review)    (audit trail)    (bad CSVs)
                │
                ↓ (operator approves)
        review/approved/
                │
                ↓ (escalated to Claude)
        Claude AI suggests rules
                │
                ↓ (human approves)
        config/rules/rules_v2.(x+1).json
```

### Key Files

| File | Purpose | Maintainer |
|------|---------|-----------|
| `scripts/uploader/app.py` | Flask web form for uploads | Dev |
| `scripts/processor_v2_3.py` | Main processing logic | Dev |
| `scripts/env_manager.py` | Auto-discover paths, create folders | Dev |
| `config/rules/rules_v2.x.json` | Active rule set (auto-discovered) | Dev + Operator |
| `config/schemas/rules_schema_v2.x.json` | JSON schema for validation | Dev |
| `skills/claude_skill_v2.6_cost_optimized.md` | Claude AI skill definition | Dev |
| `.env` | Environment variables (auto-updated) | Auto-generated |

---

## Environment Setup

### .env File (Auto-Managed)

The `env_manager.py` script auto-discovers and manages paths:

```bash
# Auto-populated by env_manager.discover_and_sync_paths()
RULES_FILE=config/rules/rules_v2.4.json
RULES_SCHEMA_FILE=config/schemas/rules_schema_v2.4.json
INTAKE_DIR=intake/new
INTAKE_FAILED_DIR=intake/failed
INTAKE_ARCHIVE_DIR=intake/archive
REVIEW_FLAGGED_DIR=review/flagged
REVIEW_APPROVED_DIR=review/approved
REVIEW_REJECTED_DIR=review/rejected
```

**Never edit .env manually.** It auto-updates when:
- A new versioned rules file is placed in `config/rules/`
- The `env_manager` is imported by any script

### Virtual Environment

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

**Key dependencies:**
- `Flask` — Web uploader
- `pandas` — CSV processing
- `python-dotenv` — Environment variable loading

---

## Rules System

### Rules File Structure (v2.4 Example)

```json
{
  "version": "2.4",
  "timestamp": "2026-05-25T10:30:00Z",
  "email_typos": [
    {
      "from": "gmai.com",
      "to": "gmail.com",
      "confidence": 0.99,
      "reason": "Common typo - missing 'i'"
    },
    {
      "from": "gmal.com",
      "to": "gmail.com",
      "confidence": 0.98,
      "reason": "Common transposition"
    },
    {
      "from": "yaho.com",
      "to": "yahoo.com",
      "confidence": 0.98,
      "reason": "Common typo - missing 'o'"
    },
    {
      "from": "hotmial.com",
      "to": "hotmail.com",
      "confidence": 0.99,
      "reason": "Common typo - transposition"
    }
  ],
  "name_case": [],
  "campaign_aliases": [],
  "pull_frequency": {
    "givebutter_hours": 24
  }
}
```

### Rules Schema Validation

**File:** `config/schemas/rules_schema_v2.4.json`

All rules files must pass schema validation before being applied. The processor checks:
- ✅ Required fields: `version`, `timestamp`, `email_typos`, `name_case`, `campaign_aliases`, `pull_frequency`
- ✅ Field types: arrays, strings, numbers
- ✅ Confidence scores: 0.0 to 1.0
- ✅ "from"/"to" pairs are valid email domains

**To validate a rules file:**
```bash
python3 -m scripts.processor_v2_3 --validate config/rules/rules_v2.5.json
```

### Adding New Rules

**Process:**

1. **Operator spots a pattern** → Reports to you: "43 instances of gmal.com → gmail.com"

2. **You propose to Claude** (in Claude Code):
   ```
   I found 43 records with the same typo: gmal.com → gmail.com
   All from the same upload, confidence 0.98.
   
   Based on claude_skill_v2.6_cost_optimized.md, propose a rule to add this.
   Include: plain_english, confidence_percent, evidence_lines, occurrences, impact_estimate.
   ```

3. **Claude returns JSON proposal:**
   ```json
   {
     "field": "email_typos",
     "plain_english": "Change '@gmal.com' to '@gmail.com'",
     "confidence_percent": 98,
     "evidence_lines": [2, 3, 4, ...],
     "occurrences": 43,
     "impact_estimate": "43 donations affected",
     "rationale": "Common transposition, all from same batch"
   }
   ```

4. **You review and manually update** `config/rules/rules_v2.4.json`:
   ```json
   {
     "version": "2.5",  // Bump version
     "timestamp": "2026-05-25T14:30:00Z",
     "email_typos": [
       // ... existing rules ...
       {
         "from": "gmal.com",
         "to": "gmail.com",
         "confidence": 0.98,
         "reason": "Common transposition (43 instances, May 2026)"
       }
     ]
     // ... rest of rules ...
   }
   ```

5. **Test the new rules:**
   ```bash
   python3 -m scripts.processor_v2_3 --validate config/rules/rules_v2.5.json
   ```

6. **The system auto-discovers** the new rules:
   - `env_manager.discover_and_sync_paths()` scans `config/rules/` 
   - Picks `rules_v2.5.json` (highest version)
   - Updates `.env` with `RULES_FILE=config/rules/rules_v2.5.json`
   - Next upload uses the new rules

**No code changes required.** Rules are purely data-driven.

---

## Claude AI Integration

### Claude Skill: v2.6 Cost-Optimized

**File:** `skills/claude_skill_v2.6_cost_optimized.md`

#### What Claude Does
- **Rule writer only** — Proposes JSON rules, never touches data
- **Detection** — Uses Haiku 3.5 ($0.25/M) to count patterns and find typos
- **Explanation** — Uses Sonnet 3.5 ($3/M) to write plain English and confidence scores

#### Output Requirements (Every Proposal)
```json
{
  "field": "email_typos",
  "plain_english": "Change '@gmal.com' to '@gmail.com'",
  "confidence_percent": 98,
  "evidence_lines": [2, 3, 4],
  "occurrences": 43,
  "impact_estimate": "43 donations (50.6%)",
  "rationale": "Common transposition"
}
```

#### Rules for Claude
1. **Allowed fields only:**
   - `email_typos`
   - `name_case`
   - `campaign_aliases`
   - `pull_frequency`

2. **Forbidden:**
   - Never propose changes to `notifications.email_to`
   - Never propose changes to payment fields or amounts
   - Never touch production data

3. **Confidence threshold:**
   - Patterns <60% confidence → rejected (escalate to human)
   - Patterns <3 occurrences → rejected (too rare)

4. **Guardrails:**
   - Plus-addressing (`user+tag@`) is NEVER a typo — ignore
   - Unicode names (José, O'Brien) preserve case — don't ASCII-fold
   - Test #7 validates against 500-record golden dataset

### Invoking Claude

```bash
# Start Claude Code in the Givebutter folder
cd /Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter

# Activate the skill
claude --skill skills/claude_skill_v2.6_cost_optimized.md

# Then ask:
# "I found 43 instances of gmal.com → gmail.com in the May batch.
#  Propose a rule to add this to email_typos."
```

---

## Processor Details

### Running the Processor

**Start:**
```bash
source .venv/bin/activate
python3 -m scripts.processor_v2_3
```

**Console output:**
```
[processor] Watching: /path/to/intake/new
[processor] Flagged -> /path/to/review/flagged
[processor] Rules: /path/to/config/rules/rules_v2.4.json
[processor] Loaded rules v2.4
```

**The processor continuously:**
1. Watches `intake/new/` for new CSV files
2. Loads the latest rules from `RULES_FILE`
3. Processes each CSV:
   - Reads with pandas
   - Checks each row against rules
   - Flags mismatches
4. Outputs flagged rows to `review/flagged/`
5. Archives original to `intake/archive/`
6. Moves parse errors to `intake/failed/`

### Processing Pipeline

**For each uploaded CSV:**

```
1. Load CSV with pandas
   → check for parse errors
   → if error: move to intake/failed/
   → if success: continue

2. Load rules from RULES_FILE
   → validate against schema
   → if invalid: log error, skip file
   → if valid: continue

3. Check each row:
   ├─ Check email against email_typos
   ├─ Check name against name_case
   ├─ Check campaign against campaign_aliases
   └─ Check other fields (amount, date, etc.)

4. Collect flagged rows
   → if none: move original to intake/archive/ (silent)
   → if some: create flagged CSV with header row

5. Output flagged CSV
   → location: review/flagged/
   → filename: flagged_{timestamp}_{original_filename}

6. Archive original
   → location: intake/archive/
   → filename: {original_filename}_archived_{timestamp}
```

### Error Handling

**Parse errors** (malformed CSV):
- File moved to `intake/failed/`
- Error logged with filename and reason
- Operator checks console or failed folder

**Invalid rules:**
- Error logged
- Processor uses previous valid rules (fallback)
- Dev should fix schema immediately

**Data conflicts:**
- If a row matches multiple rules, all are flagged
- Operator decides which apply

---

## Versioning Strategy

### Version Numbers: vX.Y

- **X (major):** Structure changes (new rule fields, new folder layout, backward-incompatible)
- **Y (minor):** New rules, bug fixes, small improvements (backward-compatible)

**Current:** v2.3 (processor) and v2.4 (rules)

**Version history:**

```
v2.0 (Jan 2026)      — Initial human-in-the-loop system
v2.1 (Feb 2026)      — Added household matching logic
v2.2 (Mar 2026)      — Fixed escalation schema
v2.3 (May 24, 2026)  — Added full 11-test suite, removed auto-apply
v2.4 (May 25, 2026)  — Added email_typos rules (gmai, gmal, yaho, hotmial)
v2.5 (planned)       — Web UI for approvals (no JSON editing)
v2.6 (skill)         — Cost-optimized Claude integration
```

### When to Bump Version

| Change | Example | New Version |
|--------|---------|-------------|
| New email typo rule | gmal.com → gmail.com | v2.5 (minor) |
| New rule field | Add "typo_category" | v3.0 (major) |
| New folder structure | Rename review/ → approvals/ | v3.0 (major) |
| Bug fix | Fix duplicate detection | v2.5 (minor) |
| UI update | Add approval form | v3.0 (major) |

---

## Testing & Quality Assurance

### Test Suite (11 Tests)

**Claude Skill mentions an 11-test suite. Implement/run:**

1. **Test 1-5: Core rule application**
   - Email typo detection
   - Name case detection
   - Campaign alias matching
   - etc.

2. **Test 6-9: Edge cases**
   - Empty CSVs
   - Unicode names (José, O'Brien)
   - Plus-addressing (user+tag@gmail.com)
   - Case sensitivity

3. **Test 10: Schema validation**
   - Rules file passes schema
   - All required fields present
   - Type checking (arrays, strings, numbers)

4. **Test 11: Backward compatibility**
   - Process files from v2.3 with v2.4 rules
   - Old rule format still works
   - Golden dataset (500 records) matches expected output

**Run tests:**
```bash
python3 -m pytest tests/ -v
```

### Manual Testing

**After deploying new rules:**

1. Create a test CSV with known typos
2. Upload via the uploader
3. Check `review/flagged/` for correct flagging
4. Verify no false positives
5. Operator reviews and approves

---

## Maintenance Tasks

### Daily
- Monitor `intake/failed/` for errors
- Check processor console for warnings
- Check rule schema validity

### Weekly
- Review flagged file patterns
- Analyze operator approve/reject ratio
- Check for recurring issues (e.g., "operator keeps rejecting email_typos, maybe the rule is too broad?")

### Monthly
- Archive old files in `review/rejected/` and `intake/archive/`
- Review Claude's rule proposals for cost
- Test the 11-test suite
- Back up rules files

### When Adding New Rules
1. Get pattern data from operator
2. Propose to Claude (with skill)
3. Review Claude's proposal
4. Update rules file, bump version
5. Run schema validation
6. Test with sample data
7. Operator re-uploads and verifies

---

## Troubleshooting

### Processor Won't Start

**Error:** `ModuleNotFoundError: No module named 'flask'`

**Fix:**
```bash
source .venv/bin/activate
pip install -r requirements.txt
python3 -m scripts.processor_v2_3
```

---

### Files Stuck in `intake/new/`

**Cause:** Processor stopped or crashed

**Fix:**
```bash
# Check if running
ps aux | grep processor_v2_3

# If not running, start it
python3 -m scripts.processor_v2_3

# If running but stuck, check for large files
ls -lah intake/new/

# If very large file (>100MB), process manually or split the CSV
```

---

### Rule File Won't Load

**Error:** `ValueError: Invalid JSON in RULES_FILE`

**Fix:**
1. Check syntax: `python3 -c "import json; json.load(open('config/rules/rules_v2.4.json'))"`
2. Validate against schema: `python3 -m scripts.processor_v2_3 --validate config/rules/rules_v2.4.json`
3. If invalid, restore previous version

---

### Flagged Records Look Wrong

**Problem:** System is flagging records that don't match the rule

**Debug:**
1. Check the rule in `config/rules/rules_v2.4.json`
2. Check the flagged CSV (what's actually being flagged?)
3. Look for false positives or regex errors
4. Test rule logic manually:
   ```python
   rule = {"from": "gmai.com", "to": "gmail.com"}
   email = "john@gmai.com"
   if email.endswith(rule["from"]):
       print(f"Would flag: {email}")
   ```
5. Refine rule or add guardrails (e.g., "don't flag plus-addressing")

---

## File Manifest

```
Givebutter/
├── README.md                          ← High-level overview
├── OPERATOR_MANUAL.md                 ← User guide (this doc)
├── DEVELOPER.md                       ← Technical reference (this doc)
├── CHANGELOG.md                       ← Version history
│
├── .env                               ← Auto-managed paths
├── .venv/                             ← Python virtual environment
├── requirements.txt                   ← Dependencies (Flask, pandas, etc.)
│
├── scripts/
│   ├── __init__.py
│   ├── env_manager.py                 ← Auto-discovery, path management
│   ├── processor_v2_3.py              ← Main processing engine
│   └── uploader/
│       ├── __init__.py
│       └── app.py                     ← Flask uploader web form
│
├── config/
│   ├── rules/
│   │   ├── rules_v2.3.json            ← Old rules (archived)
│   │   ├── rules_v2.4.json            ← Current rules (active)
│   │   └── rules_v2.5.json            ← Next version (in progress)
│   └── schemas/
│       ├── rules_schema_v2.3.json
│       ├── rules_schema_v2.4.json     ← Validates current rules
│       └── rules_schema_v2.5.json
│
├── skills/
│   ├── claude_skill_v2.3.md           ← Old skill (archived)
│   └── claude_skill_v2.6_cost_optimized.md ← Current skill (for Claude Code)
│
├── intake/
│   ├── new/                           ← Uploads land here
│   ├── archive/                       ← Processed uploads (audit trail)
│   └── failed/                        ← Malformed CSVs
│
└── review/
    ├── flagged/                       ← Issues found (operator reviews)
    ├── approved/                      ← Operator approved these (escalate)
    └── rejected/                      ← Operator rejected these (archive)
```

---

## Key APIs & Functions

### env_manager.py

```python
from scripts.env_manager import get_latest_versioned_file, discover_and_sync_paths

# Auto-discover latest rules
latest_rule = get_latest_versioned_file(
    Path("config/rules"), 
    prefix="rules"
)
# Returns: Path("config/rules/rules_v2.4.json")

# Sync all paths and create directories
discover_and_sync_paths()
# Updates .env, creates intake/new/, review/flagged/, etc.
```

### processor_v2_3.py

```python
def process_file(filepath: Path):
    """Process one CSV and flag rows per rules"""
    # Reads CSV
    # Applies rules
    # Outputs flagged CSV
    # Archives original
    pass

# Run continuously:
# python3 -m scripts.processor_v2_3
```

### uploader/app.py

```python
from flask import Flask, request

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def upload():
    """Web form for CSV uploads"""
    if request.method == 'POST':
        file = request.files.get('file')
        # Save to intake/new/ with timestamp
        # Return success message
```

---

## References

- **Claude Skill v2.6:** `skills/claude_skill_v2.6_cost_optimized.md`
- **Version History:** `CHANGELOG.md`
- **User Guide:** `OPERATOR_MANUAL.md`
- **Configuration:** `.env` (auto-managed by `env_manager.py`)

---

**Last updated:** May 25, 2026
**Document version:** 1.0
