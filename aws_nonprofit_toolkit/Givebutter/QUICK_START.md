# Quick Start - Givebutter Processor

Get the processor running and processing donations in 3 minutes.

## Installation (one-time setup)

```bash
cd aws_nonprofit_toolkit

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Start the Web UI

```bash
cd aws_nonprofit_toolkit/Givebutter

# Activate venv
source ../../venv/bin/activate

# Run the app
python3 scripts/uploader/app.py
```

You'll see:
```
 * Running on http://127.0.0.1:8000
```

Open **http://127.0.0.1:8000** in your browser.

## Process a Donation File

### Step 1: Upload
1. Click the drop zone or drag-and-drop your Givebutter CSV export
2. Wait for the validation to complete
3. See the summary: `✓ Processed X records (Y warnings, Z failures)`

### Step 2: Review
1. Click **Review** next to the file
2. You'll see a table with all records and validation results:
   - **Tier**: Green (✓ PASS), Yellow (⚠ WARNING), Red (✗ FAIL)
   - **Issues**: What's wrong with the record
   - **Suggested Fixes**: How to correct it

### Step 3: Decide

For each record, choose:
- **Approved** - Import as-is
- **Follow-up** - Needs review, add notes
- **Rejected** - Don't import

**Bulk Actions:**
- "All: Approved" - Mark all as approved
- "All: Follow-up" - Mark all for follow-up
- "All: Rejected" - Mark all as rejected

### Step 4: Save
Click **Save Decisions** to generate output files.

Done! Three files are created:
- `_APPROVED.csv` - Ready to import
- `_FOLLOWUP.csv` - Needs attention
- `_REJECTED.csv` - Excluded

## Understanding Validation Tiers

### ✓ PASS (Green)
- Record matches reference patterns
- No issues detected
- Suggested modification: none

**Action:** Usually safe to approve

### ⚠ WARNING (Yellow)
- Record has anomalies but not invalid
- Examples: high-dollar donation, unusual phone format, fuzzy name match
- Suggested modification: how to fix it

**Action:** Review suggestions, decide if OK or needs follow-up

### ✗ FAIL (Red)
- Record violates explicit rules
- Examples: invalid email format, missing required field, obviously fake phone
- Suggested modification: required fixes

**Action:** Reject or fix and re-upload

## Common Issues & Solutions

### Email Typo Detected
**Issue:** `taylor.smith11@gmai.com`

**Suggested Fix:** `taylor.smith11@gmail.com`

**Action:** Approve if the fix looks correct. Add note if unsure.

### High-Dollar Donation
**Issue:** Amount $2,000.00 (above $1,000 threshold)

**Action:** Approve if legitimate large donor. Follow-up if needs verification.

### Duplicate Detected
**Issue:** `Duplicate: Phone match: tr_8b291c3d4e`

**Suggested Fix:** Same phone appears in another record

**Action:** Follow-up to investigate. Are they the same person (household)? Different transaction?

### Unusual Phone Format
**Issue:** `555.015.2931` (dots instead of dashes)

**Suggested Fix:** `(555) 015-2931`

**Action:** Approve if amount is correct. The system can standardize on import.

### Missing Phone Number
**Issue:** No phone provided

**Action:** Approve if email is valid. Follow-up if phone is required for your process.

## Output Files

All three files are created in the same batch:

```
review/
├── approved/
│   └── upload_20260530_212146_realistic_export_APPROVED.csv
├── followup/
│   └── upload_20260530_212146_realistic_export_FOLLOWUP.csv
└── rejected/
    └── upload_20260530_212146_realistic_export_REJECTED.csv
```

**Approved** - 5 records
- All validation passed or approved by you
- Ready for direct import to database

**Follow-up** - 4 records
- Need operator attention
- Includes your notes for context
- Review before importing

**Rejected** - 1 record
- Invalid or excluded
- Do not import

## Tips

**1. Review the Suggested Modifications**
The processor suggests the most likely fix. If it looks right, approve it.

**2. Use Notes for Follow-up**
Add brief notes on follow-up items: "Check with donor" or "Verify address before importing"

**3. Bulk Actions Save Time**
If most records are valid, use "All: Approved" then uncheck the questionable ones.

**4. Check the Tier Color**
- Green (PASS) = usually safe
- Yellow (WARNING) = review suggestions
- Red (FAIL) = likely reject unless fixable

**5. Duplicates Are Opportunities**
When a duplicate is detected, check if it's:
- Same person, multiple gifts (household) - approve both
- Same transaction twice - reject duplicate
- Different people (name match is fuzzy) - approve both

## Keyboard Shortcuts

None yet, but you can:
- **Tab** through dropdown selectors
- **Shift-Click** on notes field to expand

## Getting Help

Check the full documentation in [PROCESSOR_GUIDE.md](docs/PROCESSOR_GUIDE.md) for:
- Complete validation rule reference
- API documentation
- Configuration options
- Troubleshooting

## Advanced: Configure Rules

Edit `config/rules/rules_v2.4.json` to:
- Add more email typo patterns
- Change high-dollar threshold
- Adjust phone validation patterns
- Change duplicate detection sensitivity

Restart the app after editing rules.

## Advanced: Learn from Approved

To teach the system from previously approved records:

```bash
# Move good records to review/approved/
cp approved_records.csv review/approved/

# Run the learning script
python3 scripts/build_reference_list.py
```

This updates `reference_list.json` with patterns from your approved records.

---

**Questions?** Check [PROCESSOR_GUIDE.md](docs/PROCESSOR_GUIDE.md) for the full reference.
