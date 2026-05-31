# Givebutter Donation Processor

Complete validation and workflow system for processing Givebutter CSV exports with operator review and approval.

## Overview

The processor validates donation records against configurable rules and reference patterns, detects duplicates, and guides operators through a web-based review interface to approve, flag for follow-up, or reject records.

**Three-Tier Validation System:**
- **PASS** - Record matches reference list patterns (clean data)
- **WARNING** - Record has anomalies (typos, high-dollar, unusual formats, duplicates)
- **FAIL** - Record violates explicit rules (invalid email, bad phone, missing required fields)

## Quick Start

### 1. Install Dependencies

```bash
cd aws_nonprofit_toolkit
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Start the Web Application

```bash
source venv/bin/activate
python3 aws_nonprofit_toolkit/Givebutter/scripts/uploader/app.py
```

Then open **http://127.0.0.1:8000** in your browser.

### 3. Upload and Review

1. **Upload** a Givebutter CSV export
2. **Review** records with validation results
3. **Decide** for each record: Approved, Follow-up (with notes), or Rejected
4. **Submit** to generate output files

### 4. Output Files

After submitting decisions, three files are generated:

- `review/approved/*_APPROVED.csv` - Ready to import
- `review/followup/*_FOLLOWUP.csv` - Needs operator attention
- `review/rejected/*_REJECTED.csv` - Excluded from import

## Validation Rules

### Email Validation

**Typo Detection** - Automatic correction suggestions:
- `gmai.com` → `gmail.com`
- `yaho.com` → `yahoo.com`
- `hotmial.com` → `hotmail.com`
- And 6+ more patterns

**Reference List** - Domain validation against operator-approved donors

### Phone Validation

**USA Phone Standards:**
- Valid: 10 digits or 11 digits (with leading 1)
- Standardized format: `(555) 012-3948`

**Flagged as Invalid:**
- Sequential digits: `1234567890`
- All same digits: `5555555555`
- Reserved test numbers: `555-0XXX`
- Wrong digit count: < 10 or > 11

**Flagged as Unusual:**
- Non-standard formatting (dots instead of dashes)
- Extra leading 1 (e.g., `15550123948`)
- Area codes starting with 0 or 1

### Amount Validation

- **Reference Range**: Historical min/max from approved records
- **High-Dollar**: ≥ $1,000 (configurable)
- Percentage flags relative to historical distribution

### Duplicate Detection

**Exact Match:**
- Email address
- Phone number (after digit extraction)
- Full address (Address 1 + City + State)

**Fuzzy Match:**
- Donor name at 70% similarity (configurable)

## Configuration

Edit `config/rules/rules_v2.4.json`:

```json
{
  "email_typos": [
    {"from": "gmai.com", "to": "gmail.com", "confidence": 0.99}
  ],
  "invalid_phone_patterns": [
    {"pattern": "^1234567890$", "reason": "Sequential test number"}
  ],
  "high_dollar_threshold": 1000,
  "fuzzy_match_threshold": 0.70
}
```

## Building Reference List

To learn patterns from approved records:

```bash
python3 scripts/build_reference_list.py
```

This updates `config/reference_list.json` with:
- Valid email domains and TLDs from approved records
- Amount statistics (min, max, median, percentiles)
- Name length and character constraints

Place approved CSV files in `review/approved/` first.

## Processing Pipeline

### 1. Upload (`POST /upload`)

Receives CSV, runs processor:

```
Input CSV
    ↓
[Processor validates each record]
    ↓
Output: CSV with validation results
```

### 2. Review (`GET /api/processing/<filename>`)

Retrieves records for operator review with:
- Validation Tier (PASS/WARNING/FAIL)
- Issues (what's wrong)
- Suggested Modifications (corrections)

### 3. Decide (`POST /api/processing/<filename>/submit`)

Operator specifies for each record:
- Decision: approved, followup, or rejected
- Notes: operator comments

### 4. Output (`/api/processing/<filename>/submit`)

Generates three files:

```
Approved       Followup        Rejected
(5 records)    (4 records)     (1 record)
    ↓              ↓               ↓
_APPROVED.csv  _FOLLOWUP.csv   _REJECTED.csv
```

## Field Coverage

**Validated Fields:**
- Donor Name (length, characters)
- Primary Email (format, typos, domain)
- Phone (format, digit count, obvious invalids)
- Amount (range, high-dollar flag)
- Address (completeness)

**Preserved Fields** (passed through unchanged):
- Transaction ID, Payout ID, Status, Date
- Campaign Title, Payment Method
- Processing Fee, Givebutter Fee, Fees Covered
- utm_source, utm_medium

**Added Columns** (in output):
- Validation_Tier (PASS/WARNING/FAIL)
- Issues (problems found)
- Suggested_Modifications (proposed fixes)
- Operator_Notes (operator input for follow-up)

## Suggested Modifications Examples

**Email Typo:**
```
Email typo detected. Consider: morgan.davis42@gmail.com
```

**Phone Format:**
```
Unusual format. Consider: (555) 015-2931
```

**Duplicate:**
```
Duplicate: Phone match: tr_8b291c3d4e; Name match (70%): tr_1b92c8d3ef
```

**High-Dollar:**
```
High-dollar donation (>= $1000)
```

## API Reference

### Upload File
```
POST /upload
Content-Type: multipart/form-data
Body: file=<csv_file>

Response:
{
  "filename": "upload_20260530_212146_realistic_export.csv",
  "record_count": 10,
  "warning_count": 9,
  "fail_count": 0,
  "status": "processed"
}
```

### List Processing Files
```
GET /api/processing

Response:
[
  {
    "filename": "upload_20260530_212146_realistic_export.csv",
    "rows": 10,
    "mtime": 1780199484.46
  }
]
```

### Get Records
```
GET /api/processing/<filename>

Response:
{
  "filename": "upload_20260530_212146_realistic_export.csv",
  "records": [
    {
      "idx": 0,
      "Name": "Morgan Davis",
      "Email": "morgan.davis42@gmail.com",
      "Phone": "555-019-2834",
      "Amount": "50.00",
      "Validation_Tier": "WARNING",
      "Issues": "Duplicate: Phone match: tr_8b291c3d4e",
      "Suggested_Modifications": ""
    }
  ]
}
```

### Submit Decisions
```
POST /api/processing/<filename>/submit
Content-Type: application/json

Body:
{
  "decisions": [
    {"idx": 0, "decision": "approved", "notes": ""},
    {"idx": 1, "decision": "followup", "notes": "Verify email"},
    {"idx": 2, "decision": "rejected", "notes": "Invalid"}
  ]
}

Response:
{
  "status": "success",
  "approved": 1,
  "followup": 1,
  "rejected": 1
}
```

### Cancel Review
```
POST /api/processing/<filename>/cancel
Response: {"status": "cancelled"}
```

## Directory Structure

```
Givebutter/
├── config/
│   ├── rules/
│   │   └── rules_v2.4.json          (validation rules)
│   └── reference_list.json          (patterns from approved records)
├── scripts/
│   ├── processor.py                 (validation engine)
│   ├── build_reference_list.py      (learns from approved)
│   └── uploader/
│       ├── app.py                   (Flask application)
│       └── templates/
│           └── review.html          (web UI)
├── intake/
│   └── new/                         (uploaded files)
├── archive/                         (processed files)
└── review/
    ├── processing/                  (currently being reviewed)
    ├── approved/                    (approved outputs)
    ├── followup/                    (follow-up outputs)
    └── rejected/                    (rejected outputs)
```

## Troubleshooting

### Phone validation too strict/lenient?

Edit `invalid_phone_patterns` in `rules_v2.4.json` to add/remove patterns.

### Email typo not detected?

Check `email_typos` list in `rules_v2.4.json`. Add new patterns as discovered.

### Duplicate detection missing matches?

Adjust `fuzzy_match_threshold` in `rules_v2.4.json` (0.0-1.0, default 0.70).

### Amount ranges off?

Run `build_reference_list.py` to recalibrate from approved records.

## Integration with Givebutter

The processor outputs three clean CSV files ready for:
1. **Approved** - Direct import to database
2. **Follow-up** - Manual review before import
3. **Rejected** - Not imported (delete or archive)

Each file includes original Givebutter fields plus validation metadata.

## Version History

**v3.0** (Current)
- Per-record validation and operator decisions
- Three-tier validation system (PASS/WARNING/FAIL)
- Duplicate/household detection
- Three output files based on operator decisions
- Configuration-driven rules
- Web-based review interface

**v2.4**
- Email typo detection
- High-dollar flagging
- File-level approval/rejection

**v1.0**
- Initial CSV processing
