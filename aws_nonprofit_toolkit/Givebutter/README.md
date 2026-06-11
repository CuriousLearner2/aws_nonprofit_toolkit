# Givebutter Project

Complete donation data management and operator review system for Givebutter exports.

**Status:** ✅ Production Ready | **Version:** 3.4 | **Last Updated:** 2026-06-05

---

## 📚 This Project Contains Two Systems

This repository has two major components:

1. **Givebutter Processor** (this page) — Donation validation, duplicate detection, operator review workflow
2. **DonorTrust v1 / Householder** — Import review system for identifying duplicates, normalizing donor data, grouping into households

**👉 [See the full Documentation Index](docs/INDEX.md) for both systems and all guides.**

---

## Givebutter Donation Processor

Complete donation data validation and operator review system for Givebutter exports.

---

## What It Does

Processes Givebutter CSV exports to:
1. **Validate** donation records (emails, phones, amounts, addresses, names)
2. **Detect** duplicates and household matches
3. **Suggest** corrections (typo fixes, format standardization)
4. **Guide** operators through per-record approval workflow
5. **Generate** three output files (approved, follow-up, rejected)

## Key Features

✅ **Smart Validation**
- Email typo detection (gmai.com → gmail.com, etc.)
- Fuzzy email domain matching (catches variants like gmaild.com → gmail.com)
- USA phone validation with unusual format detection
- Amount range checks and high-dollar flagging
- Address and name validation

✅ **Duplicate Detection**
- Exact match: email, phone, address
- Fuzzy match: donor names at 70% similarity
- Household grouping with suggestions

✅ **Three-Tier Scoring**
- **PASS** - Record matches reference patterns
- **WARNING** - Record has anomalies (review suggestions)
- **FAIL** - Record violates rules (likely reject)

✅ **Operator Workflow**
- Web-based review interface
- Per-record decisions: approve, follow-up, reject
- **Editable Tier field** - Change validation tier (Pass/Warning/Fail) to override validators
- **Inline editing** - Fix data errors directly in the review table
- Real-time validation on edits (email format, phone digits, amount ranges)
- **Automatic issue clearing** - Issues/suggestions update as you fix fields
- **Real-time tier recalculation** - Validation tier updates instantly when edits fix issues
- Notes field for operator context
- Bulk action buttons for efficiency (smart confirmation: individual dialogs ≤5 records, summary dialog >5)
- Override confirmation for FAIL and WARNING tier approvals

✅ **Configuration-Driven**
- Rules loaded from JSON (no hardcoding)
- Learns from operator-approved records
- Customizable thresholds and patterns

## Documentation

**👉 Start Here: [Documentation Index](docs/INDEX.md)**

The Documentation Index covers both systems:
- DonorTrust v1 / Householder (import review system)
- Givebutter Processor (donation validation)
- Testing & QA guidance
- Project-wide information

**For Processor Operators:**
- 🚀 [QUICK_START.md](QUICK_START.md) - 3-minute setup and usage

**For Processor Developers:**
- 📖 [PROCESSOR_GUIDE.md](docs/PROCESSOR_GUIDE.md) - Complete feature reference
- 🔌 [API.md](docs/API.md) - Full API documentation

**For DonorTrust / Householder:**
- 📖 [IMPLEMENTATION_GUIDE.md](docs/implementation/IMPLEMENTATION_GUIDE.md) - Phase overview and architecture
- 📋 [Phase 0 Acceptance Record](docs/completion-records/phase0/PHASE0_ACCEPTANCE_RECORD.md) - Design specification
- 🏗️ [Phase 1A Service Boundary Plan](docs/implementation/phase1a/PHASE1A_SERVICE_BOUNDARY_PLAN.md) - Architecture

## Quick Start

```bash
# Install
cd aws_nonprofit_toolkit
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run
cd Givebutter
python3 scripts/uploader/app.py

# Open browser
http://127.0.0.1:8000
```

Then:
1. **Upload** a Givebutter CSV
2. **Review** validation results
3. **Decide** for each record (approved/followup/rejected)
4. **Submit** to generate output files

## Output Files

After operator review:

```
review/
├── approved/
│   └── *_APPROVED.csv      (✓ Ready to import)
├── followup/
│   └── *_FOLLOWUP.csv      (⚠ Needs attention)
└── rejected/
    └── *_REJECTED.csv      (✗ Don't import)
```

All files include original data + validation metadata + operator notes.

## Architecture

**Components:**

- `processor.py` (634 lines) - Validation engine with 7 validation types
- `app.py` (293 lines) - Flask web application with 6 endpoints
- `review.html` (468 lines) - Web UI for operator review workflow
- `rules_v2.4.json` - Configuration (email typos, phone patterns, thresholds)
- `reference_list.json` - Learned patterns (domains, TLDs, amounts, names)

**Data Flow:**

```
Givebutter CSV → Processor → Processing CSV
                                ↓
                          [Web UI Review]
                                ↓
                    Approved / Followup / Rejected CSVs
```

## Validation Examples

**Email Typo:**
```
Input: taylor.smith11@gmai.com
Suggestion: taylor.smith11@gmail.com
```

**Duplicate:**
```
Issue: Phone match: tr_8b291c3d4e
Action: Review for household matching
```

**High-Dollar:**
```
Issue: Amount $2,000.00 (>= $1,000 threshold)
Action: Approve if legitimate, follow-up if needs verification
```

## Configuration

Edit `config/rules/rules_v2.4.json` to customize:
- Email typo patterns
- Invalid phone patterns
- High-dollar threshold
- Fuzzy match sensitivity

## Learning from Approved Records

```bash
# Move good records to review/approved/
cp my_approved_records.csv review/approved/

# Run learning script
python3 scripts/build_reference_list.py
```

## Performance

- Upload: 1-2 seconds per batch
- Validation: ~0.1 seconds per record
- Processing: 2-5 seconds typical

## Requirements

- Python 3.8+
- Flask 2.0+
- Pandas 1.3+

## Testing

✅ **Comprehensive test suite: 281 tests (all passing)**
- Unit tests (157 tests) — All validation functions and edge cases
  - Email, phone, amount, name, address, date, tier assignment, header mapping
- Integration tests (68 tests) — CSV processing, persistence, decision workflows
  - Full processor pipeline
  - Decision persistence with operator notes
  - Edit persistence and validation on submit
  - CSV format handling and edge cases
  - Override confirmation logic
  - Column structure validation (processor output format)
  - Inline field validation logic (NEW: phone test patterns, email format, amount ranges)
- End-to-end tests (59 tests) — Full UI workflows with Playwright
  - Upload and processing queue
  - Decision workflow and record review
  - Inline editing with real-time validation
  - Form inputs and validation feedback
  - Visual regression testing at multiple viewports (mobile, tablet, desktop)
  - Table DOM structure and column alignment (prevents rendering regressions)

✅ **Real-world validation verified**
- 10 records: 9 warnings detected, 0 failures
- Decisions submitted: 5 approved, 4 follow-up, 1 rejected
- Output files generated and verified

📖 **[Testing Guide](TESTING.md)** | 📋 **[Test Plan](TEST_PLAN.md)** | 📊 **[Test Summary](TEST_SUMMARY.md)**

## API Overview

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/upload` | POST | Upload and process CSV |
| `/api/processing` | GET | List files in review |
| `/api/processing/<file>` | GET | Get records with validation |
| `/api/processing/<file>/submit` | POST | Save operator decisions |
| `/api/processing/<file>/recalculate-tier` | POST | Recalculate validation tier for edited record |
| `/health` | GET | API health check |

See [API.md](API.md) for complete documentation.

## Known Limitations

1. USA phone format only (extensible)
2. Name fuzzy matching at 70% (configurable)
3. Requires operator-approved records for reference list

## Troubleshooting

**Phone validation too strict?**
Edit `invalid_phone_patterns` in `rules_v2.4.json`

**Email typo not detected?**
Add pattern to `email_typos` in `rules_v2.4.json`

**Duplicate detection missing?**
Adjust `fuzzy_match_threshold` (0.0-1.0)

See [PROCESSOR_GUIDE.md](docs/PROCESSOR_GUIDE.md) for full troubleshooting.

## Changelog

**v3.4** (Current)
- Add Done button to close review and return to queue (all edits preserved)
- Per-field Save/Cancel buttons with disabled state until valid
- Override confirmation for both FAIL and WARNING tier records (not just FAIL)
- Smart bulk approval logic: individual dialogs for ≤5 records, summary dialog for >5
- Auto-save for data field edits (click Save when valid) + Decision/Notes fields
- **Editable Tier dropdown** - Operators can override validation tier (Pass/Warning/Fail)
- Fuzzy email domain matching (catches typos like gmaild.com, icloud.co, etc.)
- All 281 tests passing

**v3.3**
- Implemented inline field validation with real-time feedback
- Frontend validates against invalid test phone patterns (sequential, all same digits, reserved 555 ranges)
- Real-time validation on input change shows error messages below fields
- Save button disabled when validation errors present
- Added 11 integration tests for inline validation logic
- All 282 tests passing

**v3.2**
- Added column structure regression tests (integration + E2E)
- Added pre-commit hook to auto-run tests before commits
- Fixed column alignment bug in review table (was rendering all columns, not just mapped ones)
- Restored Date field to display
- All 271 tests passing

**v3.1**
- Fixed column index bug preventing validation issues from displaying after field edits
- Refactored DOM updates to use CSS selectors instead of hardcoded indices
- Added data-field-type attributes for more robust selector targeting
- Improved console error messages for DOM update failures

**v3.0**
- Per-record validation and operator decisions
- Three-tier validation system
- Duplicate/household detection
- Web-based review interface
- Configuration-driven rules

**v2.4**
- Email typo detection
- High-dollar flagging

**v1.0**
- Initial CSV processing

---

📖 **[Read the Full Guide](docs/PROCESSOR_GUIDE.md)** | 🚀 **[Quick Start](QUICK_START.md)** | 🔌 **[API Docs](docs/API.md)**
