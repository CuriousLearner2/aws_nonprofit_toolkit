# System Architecture
## How the Givebutter Donation Processor is Built

This document explains how the system works internally. If you're an operator, start with [OPERATOR_MANUAL.md](../OPERATOR_MANUAL.md) instead.

---

## High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    GIVEBUTTER DONATION PROCESSOR                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐                                              │
│  │  YOU (Operator)  │                                              │
│  └────────┬─────────┘                                              │
│           │ (upload CSV)                                           │
│           ↓                                                        │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │        FLASK UPLOADER (http://localhost:8000)          │     │
│  │     (scripts/uploader/app.py)                          │     │
│  │  Simple web form for CSV uploads                       │     │
│  └──────────────────────┬────────────────────────────────┘     │
│                         │ (save with timestamp)                 │
│                         ↓                                       │
│                    intake/new/                                 │
│                   (upload folder)                              │
│                         │                                       │
│  ┌──────────────────────┴─────────────────────────────────┐    │
│  │     MAIN PROCESSOR v2.3 (auto-watches intake/new/)    │    │
│  │   (scripts/processor_v2_3.py)                         │    │
│  │  1. Load CSV file                                     │    │
│  │  2. Load rules from config/rules/rules_v*.json        │    │
│  │  3. Check every row against rules                     │    │
│  │  4. Flag rows that don't match                        │    │
│  │  5. Output flagged rows to review/flagged/            │    │
│  │  6. Archive original to intake/archive/               │    │
│  │  7. Move bad files to intake/failed/                  │    │
│  └──────────────────────┬─────────────────────────────────┘    │
│                         │                                       │
│       ┌─────────────────┼─────────────────┐                    │
│       ↓                 ↓                 ↓                    │
│  review/flagged/  intake/archive/   intake/failed/            │
│  (issues found)  (backup)            (format errors)          │
│       │                                   │                    │
│       │ (YOU review)                      │                    │
│       ↓                                   └─ (ask tech lead)   │
│  ┌─────────────────┐                                          │
│  │  YOU DECIDE:    │                                          │
│  │ approve/reject  │                                          │
│  └────┬────────┬──┘                                           │
│       │        │                                              │
│       ↓        ↓                                              │
│ review/    review/                                           │
│ approved/  rejected/                                         │
│       │        │                                              │
│       │ (tech lead escalates patterns)                        │
│       ↓                                                       │
│  ┌────────────────────────────────┐                         │
│  │  CLAUDE AI (v2.6 skill)        │                         │
│  │  Suggests new rules            │                         │
│  │  Never touches data            │                         │
│  └────────┬───────────────────────┘                         │
│           │ (you review + approve)                           │
│           ↓                                                   │
│  config/rules/rules_v*.json                                  │
│  (rules file updated, version bumped)                        │
│           │                                                   │
│           ↓ (auto-discovered by env_manager.py)             │
│  .env (updated automatically)                               │
│           │                                                   │
│           └─→ NEXT UPLOAD USES NEW RULES                   │
│                                                              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram (Step by Step)

```
┌─────────────┐
│ Givebutter  │
│  (export    │
│   CSV)      │
└──────┬──────┘
       │
       ↓ (user downloads)
  ┌─────────────┐
  │  Your       │
  │  Computer   │
  └──────┬──────┘
         │
         ↓ (upload via localhost:8000)
  ┌──────────────────────────────────┐
  │ UPLOAD HANDLER                   │
  │ • Receive file                   │
  │ • Save with timestamp            │
  │ • Store in intake/new/           │
  │ • Show "File received"           │
  └──────┬───────────────────────────┘
         │
         ↓ (processor auto-watches)
  ┌──────────────────────────────────┐
  │ PROCESSOR LOOP                   │
  │ • Detect new files               │
  │ • Read CSV with pandas           │
  │ • Check for parse errors         │
  └──────┬───────────────────────────┘
         │
         ├─ Parse error?
         │  ↓ (yes) → intake/failed/
         │  ↓ (no) → continue
         │
  ┌──────┴───────────────────────────┐
  │ LOAD RULES                       │
  │ • Get path from .env             │
  │ • Load config/rules/rules_v*.json│
  │ • Validate against schema        │
  └──────┬───────────────────────────┘
         │
  ┌──────┴───────────────────────────┐
  │ CHECK EACH ROW                   │
  │ For each donation record:        │
  │ • Check email typos              │
  │ • Check name case                │
  │ • Check campaign aliases         │
  │ • Check other fields             │
  │ → Flag if any mismatch           │
  └──────┬───────────────────────────┘
         │
         ├─ Any flagged rows?
         │  ├─ Yes → create flagged CSV
         │  │       store in review/flagged/
         │  │
         │  └─ No → file is clean
         │         store in intake/archive/
         │         (silent success)
         │
  ┌──────┴───────────────────────────┐
  │ YOU (OPERATOR)                   │
  │ • Open review/flagged/           │
  │ • Read flagged records           │
  │ • Decide approve/reject          │
  │ • Move file to appropriate folder│
  └──────┬───────────────────────────┘
         │
         └─→ PATTERN SPOTTED?
             └─→ TELL TECH LEAD
                 └─→ CLAUDE PROPOSES RULE
                     └─→ YOU APPROVE
                         └─→ TECH LEAD UPDATES RULES FILE
                             └─→ NEXT UPLOAD USES NEW RULE
```

---

## Folder Structure & Purpose

```
Givebutter/  (root directory)
│
├── intake/                 ← CSV files being processed
│   ├── new/               (WHERE UPLOADS LAND)
│   │   ├── upload_20260525_143022_donations.csv
│   │   └── upload_20260525_150033_donations.csv
│   │
│   ├── archive/           (BACKUP OF ORIGINALS)
│   │   ├── donations.csv_archived_20260525_143045
│   │   └── donations.csv_archived_20260525_150100
│   │
│   └── failed/            (PARSE ERRORS)
│       └── bad_format.csv
│
├── review/                ← You work here
│   ├── flagged/          (ISSUES TO REVIEW - YOUR INBOX)
│   │   ├── flagged_20260525_143045_upload_20260525_143022_donations.csv
│   │   └── flagged_20260525_150115_upload_20260525_150033_donations.csv
│   │
│   ├── approved/         (GOOD - ESCALATE TO CLAUDE)
│   │   └── flagged_20260525_143045_upload_20260525_143022_donations.csv
│   │
│   └── rejected/         (NOT ISSUES - ARCHIVE)
│       └── flagged_20260525_150115_upload_20260525_150033_donations.csv
│
├── config/                ← System configuration
│   ├── rules/            (Where rules live)
│   │   ├── rules_v2.3.json
│   │   ├── rules_v2.4.json  ← Current (auto-discovered)
│   │   └── rules_v2.5.json
│   │
│   └── schemas/          (Validation schemas)
│       ├── rules_schema_v2.3.json
│       ├── rules_schema_v2.4.json  ← Current
│       └── rules_schema_v2.5.json
│
├── scripts/               ← The actual code
│   ├── __init__.py
│   ├── env_manager.py     (auto-discovery, folder creation)
│   ├── processor_v2_3.py  (main processing engine)
│   └── uploader/
│       ├── __init__.py
│       └── app.py         (Flask web form)
│
├── skills/                ← Claude AI instructions
│   └── claude_skill_v2.6_cost_optimized.md
│
├── .env                   ← Environment variables (AUTO-MANAGED)
├── .venv/                 ← Python virtual environment
├── requirements.txt       ← Dependencies (Flask, pandas, etc.)
│
└── docs/                  ← Documentation (you are here!)
    ├── README.md
    ├── OPERATOR_MANUAL.md
    ├── DEVELOPER.md
    ├── ARCHITECTURE.md (this file)
    ├── SETUP_GUIDE.md
    ├── INDEX.md
    ├── FAQ.md
    ├── QUICK_START.md
    └── CHANGELOG.md
```

---

## Component Details

### 1. Flask Uploader (`scripts/uploader/app.py`)

```
┌─────────────────────────────────────────┐
│   FLASK UPLOADER                        │
│   (http://localhost:8000)               │
├─────────────────────────────────────────┤
│                                         │
│  Display HTML form:                     │
│  ┌────────────────────────────────┐   │
│  │ Upload Givebutter Donation CSV │   │
│  │                                │   │
│  │ [Choose File] [Upload]         │   │
│  └────────────────────────────────┘   │
│                                         │
│  On submit:                             │
│  1. Receive file                        │
│  2. Check size (max 16 MB)              │
│  3. Generate timestamp                  │
│  4. Save to intake/new/ as:             │
│     upload_YYYYMMDD_HHMMSS_filename    │
│  5. Return "File received" message      │
│  6. Exit                                │
│                                         │
│  (Does NOT process - processor does)    │
│                                         │
└─────────────────────────────────────────┘
```

**Key detail:** The uploader is STATELESS. It just saves files. The processor handles everything else.

---

### 2. Main Processor (`scripts/processor_v2_3.py`)

```
┌─────────────────────────────────────────────────────────┐
│   MAIN PROCESSOR (runs continuously)                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  LOOP:                                                  │
│  ┌──────────────────────────────────────────────┐     │
│  │ 1. Watch intake/new/ for files              │     │
│  │                                              │     │
│  │ 2. For each file found:                     │     │
│  │    a. Load file with pandas                 │     │
│  │    b. Check for parse errors                │     │
│  │       → Bad? → Move to intake/failed/       │     │
│  │       → Good? → Continue                    │     │
│  │    c. Load rules from RULES_FILE (.env)     │     │
│  │    d. Check each row against rules:         │     │
│  │       • email_typos check                   │     │
│  │       • name_case check                     │     │
│  │       • campaign_aliases check              │     │
│  │       • other field checks                  │     │
│  │    e. Collect flagged rows                  │     │
│  │       → None? → Move original to archive    │     │
│  │       → Some? → Create flagged CSV          │     │
│  │    f. Save flagged CSV to review/flagged/   │     │
│  │    g. Archive original to intake/archive/   │     │
│  │                                              │     │
│  │ 3. Repeat (look for new files)              │     │
│  │                                              │     │
│  └──────────────────────────────────────────────┘     │
│                                                         │
│  Expected flow: 5-30 seconds per file                 │
│  Errors logged to console                             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Key detail:** The processor is REACTIVE. It watches a folder and processes files as they appear.

---

### 3. Environment Manager (`scripts/env_manager.py`)

```
┌─────────────────────────────────────────────────────────┐
│   ENV_MANAGER (runs on import)                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  When any script imports this:                          │
│                                                         │
│  1. Scan config/rules/ for rules_v*.json               │
│     → Find all versioned files                          │
│     → Pick the highest version                          │
│     → Store in RULES_FILE                              │
│                                                         │
│  2. Scan config/schemas/ for rules_schema_v*.json      │
│     → Find all versioned files                          │
│     → Pick the highest version                          │
│     → Store in RULES_SCHEMA_FILE                        │
│                                                         │
│  3. Create required folders (if missing):              │
│     • intake/new/                                       │
│     • intake/failed/                                    │
│     • intake/archive/                                   │
│     • review/flagged/                                   │
│     • review/approved/                                  │
│     • review/rejected/                                  │
│                                                         │
│  4. Update .env with all paths                         │
│                                                         │
│  Result: Zero-code deployment!                         │
│  Drop rules_v2.5.json → auto-discovered               │
│  Drop rules_schema_v2.5.json → auto-discovered        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Key detail:** This is the magic that makes zero-code deployment work. No manual path updates needed.

---

## Decision Points (Where Humans Decide)

```
┌──────────────────────────────────────────┐
│  OPERATOR DECISION TREE                  │
├──────────────────────────────────────────┤
│                                          │
│  See flagged file in review/flagged/    │
│                │                         │
│                ↓                         │
│     "Is this a real problem?"           │
│                │                         │
│    ┌───────────┼───────────┐            │
│    │           │           │            │
│   YES         NO        MAYBE           │
│    │           │           │            │
│    ↓           ↓           ↓            │
│ Move to    Move to    Leave in          │
│ review/    review/    review/           │
│ approved/  rejected/  flagged/          │
│    │           │      (undecided)       │
│    │           │                        │
│    └─ ESCALATE ─┴─ ARCHIVE             │
│        TO                               │
│      CLAUDE                             │
│                                          │
└──────────────────────────────────────────┘
```

**Key detail:** The operator is the SAFETY GATE. Nothing changes without human approval.

---

## Rule Escalation Flow

```
┌──────────────┐
│ OPERATOR     │
│ spots        │
│ pattern      │
└──────┬───────┘
       │ "I found 43 gmal.com → gmail.com"
       ↓
┌──────────────────────────────────┐
│ TECH LEAD                        │
│ analyzes pattern                 │
│ contacts Claude                  │
└──────┬───────────────────────────┘
       │
       ↓ "What rule should we add?"
┌──────────────────────────────────┐
│ CLAUDE AI (v2.6 skill)           │
│ analyzes the pattern             │
│ suggests JSON rule               │
│ includes confidence score        │
│ includes impact estimate         │
└──────┬───────────────────────────┘
       │ Returns:
       │ {
       │   "field": "email_typos",
       │   "from": "gmal.com",
       │   "to": "gmail.com",
       │   "confidence": 0.98,
       │   "occurrences": 43
       │ }
       ↓
┌──────────────────────────────────┐
│ OPERATOR + TECH LEAD             │
│ review Claude's suggestion       │
│ "Yes, gmal.com is always         │
│  gmail.com"                      │
└──────┬───────────────────────────┘
       │
       ↓ "Approved"
┌──────────────────────────────────┐
│ TECH LEAD                        │
│ updates config/rules/            │
│ rules_v2.4.json → rules_v2.5.json│
│ adds new rule to email_typos     │
│ bumps version                    │
│ saves file                       │
└──────┬───────────────────────────┘
       │
       ↓ (env_manager auto-detects)
┌──────────────────────────────────┐
│ .env updated                     │
│ RULES_FILE = rules_v2.5.json    │
└──────┬───────────────────────────┘
       │
       ↓ (next upload)
┌──────────────────────────────────┐
│ PROCESSOR                        │
│ loads new rules                  │
│ gmal.com now auto-flagged        │
│ (no more manual review needed)   │
└──────────────────────────────────┘
```

**Key detail:** Rules are versioned. Drop a new file, system auto-discovers it. Zero-code deployment.

---

## Rules File Structure

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
    }
  ],
  "name_case": [],
  "campaign_aliases": [],
  "pull_frequency": {
    "givebutter_hours": 24
  }
}
```

**Key detail:** Simple JSON. Versioned. Validated against schema. Auto-discovered.

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Web Interface** | Flask (Python web framework) | HTTP server + form handling |
| **Data Processing** | Pandas (Python library) | CSV reading/manipulation |
| **File I/O** | Python pathlib | Cross-platform file operations |
| **Configuration** | python-dotenv | Environment variable management |
| **Validation** | JSON Schema | Rules file validation |
| **AI Advisory** | Claude API (external) | Rule suggestions |
| **Automation** | Continuous loop | File watching + processing |

**No database.** Everything is files. No external services (except optional Claude AI).

---

## Scaling Considerations

**Current capacity:** Optimized for nonprofits with 0-100k donations/month

**Bottlenecks:**
- **Large files (>100 MB):** Split into batches
- **Many rules:** Simple linear checks (fast)
- **Manual review:** Operator workload grows with flagged records

**Future optimizations:**
- Bulk file processing
- Parallel rule checking
- Web UI for approvals (v2.4 planned)
- Database instead of files (v3.0 planned)

---

## Security Considerations

✅ **What's secure:**
- Operator can't modify rules (only approve/reject)
- Claude never touches production data
- All changes are logged (audit trail)
- Processors are read-only from operator's perspective

⚠️ **What requires care:**
- .env file contains paths (don't commit with credentials)
- Rules file is JSON (don't hand-edit, use Claude)
- Processor has file system access (run on trusted server)
- Uploader is local-only (don't expose to internet without auth)

---

## How Data Flows End-to-End

```
STEP 1: OPERATOR          STEP 2: UPLOADER      STEP 3: PROCESSOR
┌──────────────┐          ┌──────────────┐     ┌──────────────┐
│ Downloads    │ upload   │ Save file    │ new │ Load & check │
│ CSV from     │ ──────→  │ with time    │ ──→ │ against      │
│ Givebutter   │          │ stamp        │     │ rules        │
└──────────────┘          └──────────────┘     └──────┬───────┘
                                                      │
                          ┌───────────────────────────┴────────┐
                          │                                     │
                     STEP 4a: No issues          STEP 4b: Issues found
                          │                                     │
                          ↓                                     ↓
                    ┌──────────────┐                ┌──────────────────┐
                    │ Archive file │                │ Create flagged    │
                    │ (backup)     │                │ CSV file          │
                    └──────────────┘                └────────┬─────────┘
                                                            │
                                                    STEP 5: OPERATOR
                                                            │
                                                    ┌───────┴────────┐
                                                    │                │
                                        "Fix these" │         "These are OK"
                                                    │                │
                                            STEP 6a │        STEP 6b │
                                                    │                │
                                            ┌───────┴────┐    ┌──────┴───┐
                                            │ Move to    │    │ Move to  │
                                            │ approved/  │    │ rejected/│
                                            └────┬───────┘    └──────────┘
                                                 │
                                        STEP 7: ESCALATE
                                                 │
                                        ┌────────┴────────┐
                                        │                 │
                                   Report pattern      
                                   to Claude
                                        │
                                   Claude proposes
                                   new rule
                                        │
                                   You approve
                                        │
                                   Tech lead updates
                                   rules file
                                        │
                                   STEP 8: NEXT UPLOAD
                                        │
                                   Uses new rules
                                   Auto-flags similar
                                   issues (no manual
                                   review needed)
```

---

## Key Files & Their Relationships

```
.env
  ↓ (auto-updated by env_manager.py)
  ├─→ RULES_FILE = config/rules/rules_v2.4.json
  ├─→ RULES_SCHEMA_FILE = config/schemas/rules_schema_v2.4.json
  ├─→ INTAKE_DIR = intake/new
  ├─→ REVIEW_FLAGGED_DIR = review/flagged/
  └─→ ... (other paths)
       ↓
processor_v2_3.py
  ├─ Uses: rules_v2.4.json (from RULES_FILE)
  ├─ Watches: intake/new/ (from INTAKE_DIR)
  ├─ Outputs to: review/flagged/ (from REVIEW_FLAGGED_DIR)
  └─ Archives to: intake/archive/

uploader/app.py
  ├─ Saves to: intake/new/ (from INTAKE_DIR)
  └─ Max size: 16 MB (hardcoded)

config/rules/rules_v2.4.json
  ├─ Loaded by: processor_v2_3.py
  ├─ Validated by: rules_schema_v2.4.json
  ├─ Updated by: Human (with Claude's help)
  └─ Version: 2.4 (bumped when changed)

config/schemas/rules_schema_v2.4.json
  ├─ Validates: rules_v2.4.json
  ├─ Checked by: processor_v2_3.py (on startup)
  └─ Version: 2.4 (matches rules version)
```

---

## Summary: How It All Works Together

1. **Operator uploads CSV** via uploader (localhost:8000)
2. **Uploader saves file** to intake/new/ with timestamp
3. **Processor continuously watches** intake/new/
4. **Processor loads latest rules** from config/rules/ (auto-discovered by env_manager)
5. **Processor checks each row** against rules, flags mismatches
6. **Flagged rows saved** to review/flagged/
7. **Operator reviews** flagged records
8. **Operator decides:** Move to approved/ or rejected/
9. **Tech lead escalates patterns** to Claude AI
10. **Claude suggests new rules** (JSON format)
11. **Tech lead updates** config/rules/ and bumps version
12. **env_manager auto-discovers** new version
13. **.env updated automatically**
14. **Next upload** uses new rules
15. **Repeat** (system learns over time)

---

**Key principle:** Humans decide. System enforces. Rules improve. Data gets cleaner. 🎯

---

## Validation Rules Architecture (V2)

### Overview

V2 introduces a **dual-validation system**: preventing errors upstream (before Givebutter) while maintaining downstream correction (catching escapes). This addresses a key constraint: Givebutter's hosted widget doesn't allow custom JavaScript injection (PCI compliance), so validation must happen on your website before the form opens the widget.

### Two-File Architecture

```
VALIDATION_RULES.JSON                RULES.JSON
(UPSTREAM - PREVENTION)              (DOWNSTREAM - CORRECTION)

Your Website                         This Processor
┌──────────────────────────┐        ┌──────────────────────┐
│ Pre-Form Wrapper         │        │ Post-Givebutter      │
│                          │        │                      │
│ • Email format check ✓   │        │ Catches what         │
│ • Domain whitelist ✓     │──→ Open│ escaped upstream      │
│ • Required fields ✓      │        │                      │
│ • Format rules ✓         │ Widget │ • Applies corrections │
│ • Real-time feedback ✓   │        │ • Learns from errors │
│                          │        │                      │
│ "Did you mean            │        │ Operator approves    │
│  @gmail.com?"            │        │ fuzzy matches &      │
│                          │        │ edge cases           │
│ PREVENTS ~70%            │        │ CATCHES ~30%         │
└──────────────────────────┘        └──────────────────────┘
```

### validation_rules.json (Full Specification)

This file defines all upstream validation rules. Example structure:

```json
{
  "$schema": "../schemas/validation_schema_v2.4.json",
  "version": "2.4",
  "created": "2026-05-26T10:00:00Z",
  
  "email_validation": {
    "format": {
      "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
      "message": "Please enter a valid email address",
      "severity": "error"
    },
    "domain_whitelist": {
      "enabled": true,
      "domains": ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com"],
      "unknown_domain_action": "warn",
      "message": "Email domain not recognized. Did you mean..."
    },
    "common_typos": {
      "enabled": true,
      "typos": {
        "gmai.com": "gmail.com",
        "gmal.com": "gmail.com",
        "yaho.com": "yahoo.com",
        "hotmial.com": "hotmail.com"
      },
      "action": "warn_and_suggest"
    },
    "plus_addressing": {
      "enabled": true,
      "allowed": true,
      "note": "plus@gmail.com is valid, not a typo"
    }
  },
  
  "required_fields": {
    "donor_name": { "required": true, "min_length": 2 },
    "email": { "required": true },
    "donation_amount": { "required": true, "min": 0.01 }
  },
  
  "field_formats": {
    "phone_optional": {
      "pattern": "^(\\d{3}[-.]?\\d{3}[-.]?\\d{4})?$",
      "required": false
    },
    "zip_code": {
      "pattern": "^\\d{5}(-\\d{4})?$",
      "required": false
    }
  },
  
  "feedback_strategy": {
    "real_time": true,
    "on_blur": ["email", "phone"],
    "validation_timing": {
      "email": "immediate",
      "amount": "onchange"
    }
  }
}
```

### rules.json (Enhanced with Metadata)

Rules.json now includes metadata linking back to validation rules:

```json
{
  "email_typos": [
    {
      "from": "gmai.com",
      "to": "gmail.com",
      "confidence": 0.99,
      "validation_rule_id": "email.typos.gmai",
      "discovered": "2026-05-25",
      "instances_caught": 43,
      "source": "common_typo"
    }
  ]
}
```

**Enhancement:** `validation_rule_id` links to the upstream validation rule, enabling tracking of "where this rule came from" and "why we have it."

### Scenario Walkthroughs

#### Scenario 1: Prevention (User Types Typo)
```
User: john@gmai.com
                ↓
validation_rules.json checks:
  ✓ Format valid? YES
  ✗ Domain recognized? NO
  → Check typo list: "gmai.com" found!
                ↓
Real-time tooltip:
  "Did you mean gmail.com? [Yes] [Edit]"
                ↓
User clicks [Yes] → email corrected → form submitted
                ↓
Givebutter receives: john@gmail.com ✅
RESULT: Error prevented!
```

#### Scenario 2: Correction (User Bypasses Validation)
```
User posts directly to Givebutter (skips wrapper)
Email: john@gmai.com entered in DB
                ↓
Processor loads rules.json
Found: { from: "gmai.com", to: "gmail.com" }
                ↓
Row flagged for review:
  "Email typo detected (validation_rule_id: email.typos.gmai)"
                ↓
Operator reviews & approves
                ↓
RESULT: Error caught, learning metadata recorded
```

#### Scenario 3: Learning (Pattern Emerges)
```
1. Operator approves 23 instances of unfamiliar domain
   "example.co.uk" (not a typo, but flagged)
                ↓
2. System analyzes: 23 instances, high confidence = real pattern
                ↓
3. Learning system suggests: Add "example.co.uk" to whitelist
                ↓
4. Technical lead updates validation_rules.json:
   "domains": [..., "example.co.uk"]
                ↓
5. .env auto-updates (env_manager detects new version)
                ↓
6. Next upload: NO FALSE POSITIVES for example.co.uk
RESULT: System learns, prevents future false positives!
```

### File Structure

```
config/
├── validation_rules.json              ← UPSTREAM validation
├── rules/
│   ├── rules_v2.4.json               ← DOWNSTREAM correction (current)
│   └── rules_v2.5.json               ← Future version
└── schemas/
    ├── validation_schema_v2.4.json   ← Validates validation_rules.json
    └── rules_schema_v2.4.json        ← Validates rules.json
```

### Integration Points

**Pre-Form Wrapper (Your Website):**
```javascript
// Load validation rules
fetch('/config/validation_rules.json')
  .then(rules => {
    // Real-time validation as user types
    // Show suggestions before form submit
    // Only open Givebutter if validation passes
  })
```

**Processor (This System):**
```python
# Load both files for complete picture
validation_rules = load_json('config/validation_rules.json')
rules = load_json('config/rules/rules_v2.4.json')

# Check flagged records:
# 1. Which validation_rule_id did it escape from?
# 2. What does rules.json say?
# 3. Log both for learning feedback
```

### Benefits of V2

| Aspect | V1 | V2 | Impact |
|--------|----|----|--------|
| Error prevention | 0% | ~70% | Cleaner data entry |
| Operator review | High | Low (30%) | Faster processing |
| Donor feedback | Silent | Real-time | Better UX |
| Learning speed | Slow | Fast | Quicker improvement |
| Data quality | Post-DB | Pre-DB | Better throughout |
| Traceability | Low | High | Easier debugging |

### For More Details

See **[PRD.md](../PRD.md)** for product strategy and open questions about validation scope, implementation approach, and deployment.

---

**Key principle:** Humans decide. System enforces. Rules improve. Data gets cleaner. 🎯

---

**For more details:**
- **[PRD.md](../PRD.md)** — Product strategy and validation rules design
- **[DEVELOPER.md](DEVELOPER.md)** — Technical maintenance and integration
- **[OPERATOR_MANUAL.md](../OPERATOR_MANUAL.md)** — How to use the system daily
- **[SETUP_GUIDE.md](../SETUP_GUIDE.md)** — How to set it up initially

**Last updated:** May 26, 2026  
**Architecture version:** 2.0
