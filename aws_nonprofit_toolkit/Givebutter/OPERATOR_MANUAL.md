# Operator's Manual
## How to Use the Givebutter Donation Processor v3.0

---

## Introduction: Why This System Exists

Every nonprofit receives donations through platforms like Givebutter, Square, or Stripe. The data looks clean when you first download it, but it contains hidden problems:

- A donor typed "gmai.com" instead of "gmail.com" — you can't contact them
- The same person donated twice with slightly different names — your records show two donors instead of one  
- A donation amount is missing — your accounting report is incomplete
- A phone number has an unusual format — is it real or a test entry?

These errors compound over time. A thousand small mistakes become a headache when you're reconciling accounts or sending donor receipts.

**This system catches those problems before they become headaches.**

---

## Your Role

You are the **data quality guardian**. Your job:

1. **Upload** Givebutter CSV files
2. **Review** validation results and operator suggestions
3. **Decide** for each record: approve, follow-up (with notes), or reject
4. **Generate** three clean output files ready for import

You're not responsible for fixing the data yourself (the system suggests fixes), but you ARE responsible for reviewing each record and making the final call.

---

## Quick Start: 60 Seconds

### For Technical Users

```bash
cd /Users/gautambiswas/Claude\ Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter

# One-time setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Every time you want to use it
source venv/bin/activate
python3 scripts/uploader/app.py
```

You'll see: `Running on http://127.0.0.1:8000`

### For All Users

1. Open **http://127.0.0.1:8000** in your browser
2. **Drag and drop** your Givebutter CSV export
3. **Wait** for validation (usually < 5 seconds)
4. **Review** the records with validation results
5. **Decide** for each record (approve/followup/reject)
6. **Click "Save Decisions"** to generate output files

Done! Three clean CSV files are created.

---

## The 4-Step Workflow

### Step 1: Upload

**Where:** http://127.0.0.1:8000

**What to upload:**
- Givebutter CSV exports
- Standard columns: Name, Email, Phone, Amount, Date, etc.

**What happens:**
- System runs validation on all records (< 5 seconds)
- System assigns validation tiers: PASS, WARNING, or FAIL
- System generates suggestions for fixes

**You see:** Summary of results
- Total records
- Pass count (✓)
- Warning count (⚠)
- Fail count (✗)

---

### Step 2: Review

**Where:** Web UI (same page)

**What you see:**

A table with all records showing:

| Column | What It Shows |
|--------|---------------|
| Name | Donor name |
| Email | Email address |
| Phone | Phone number |
| Amount | Donation amount |
| Campaign | Which fund/campaign |
| **Tier** | **✓ PASS / ⚠ WARNING / ✗ FAIL** |
| **Issues** | **What's wrong (if anything)** |
| **Suggestions** | **How to fix it** |
| Decision | (Empty—you fill this in) |
| Notes | (Optional—you fill this in) |

**Example record:**
```
Name:        taylor smith
Email:       taylor.smith11@gmai.com
Tier:        ⚠ WARNING
Issues:      (none)
Suggestions: Email typo detected. Consider: taylor.smith11@gmail.com
Decision:    [You choose: Approved / Follow-up / Rejected]
Notes:       [Optional: Add context]
```

---

### Step 3: Decide

For **each record**, choose one decision:

**✓ APPROVED**
- Record is good as-is, or the suggested fix looks right
- Will go to `_APPROVED.csv` (ready to import)

**⚠ FOLLOW-UP**  
- Needs attention but you want to note it for later
- Add notes: "Verify this high-dollar amount" or "Check phone format"
- Will go to `_FOLLOWUP.csv` with your notes

**✗ REJECTED**
- Invalid or shouldn't be imported
- Example: Clearly fake test entry, invalid email beyond repair
- Will go to `_REJECTED.csv` (exclude from import)

**Bulk Actions:**
- "All: Approved" — Mark all as approved at once
- "All: Follow-up" — Mark all for follow-up
- "All: Rejected" — Mark all as rejected
- Then click individual records to change as needed

---

### Step 4: Save & Generate

**Click "Save Decisions"**

System creates three files:

1. **`*_APPROVED.csv`**
   - Records you approved
   - Ready to import to your database
   - No further action needed

2. **`*_FOLLOWUP.csv`**
   - Records marked for follow-up
   - Includes your notes
   - Review these before importing

3. **`*_REJECTED.csv`**
   - Records you rejected
   - Don't import these
   - Keep for audit trail

---

## Understanding Validation Tiers

### ✓ PASS (Green)

**What it means:** Record matches reference patterns. Data looks clean.

**Examples:**
- Email is valid and from a known domain
- Phone is properly formatted
- Amount is within normal range
- All required fields present

**What to do:** Usually safe to approve

---

### ⚠ WARNING (Yellow)

**What it means:** Record has anomalies but isn't invalid. Worth reviewing.

**Examples:**
```
Email Typo:
  "Email typo detected. Consider: morgan.davis42@gmail.com"

High-Dollar:
  "High-dollar donation (>= $1000)"

Unusual Phone Format:
  "Unusual format. Consider: (555) 015-2931"

Duplicate Detected:
  "Phone match: tr_8b291c3d4e (same phone as another record)"

Fuzzy Name Match:
  "Name match (70%): tr_1b92c8d3ef (similar to another record)"
```

**What to do:**
1. Look at the suggested fix
2. Does it look right? → Approve
3. Unsure? → Mark for Follow-up with notes
4. Looks wrong? → Reject

---

### ✗ FAIL (Red)

**What it means:** Record violates validation rules. Likely needs fixing or rejection.

**Examples:**
```
Invalid Phone:
  "Invalid: Sequential test number (1234567890)"

Missing Email:
  "Missing email"

Invalid Format:
  "Invalid email format (missing @)"
```

**What to do:**
1. Review if it's a real problem
2. Can it be fixed? → Approve if fix looks good
3. Should not be imported? → Reject

---

## Tips for Quick Review

**1. Sort by Tier**
When all records appear at once, scan for color:
- ✓ Green = usually approve
- ⚠ Yellow = review suggestions
- ✗ Red = likely reject

**2. Use Bulk Actions**
- "All: Approved" for batches with mostly clean data
- Then fix exceptions individually

**3. Add Meaningful Notes**
Instead of:
```
"ok"
```

Write:
```
"Verified with donor—phone is correct even though format is unusual"
```

**4. High-Dollar = Follow-up**
If a donation is unusually large, mark for follow-up:
```
Decision: Follow-up
Notes: "High-dollar ($5,000)—verify before import"
```

**5. Duplicates = Investigate**
When you see a duplicate alert:
```
"Duplicate: Phone match: tr_8b291c3d4e"
```

Decide:
- **Same person, multiple gifts?** → Approve both (household giving)
- **Same transaction twice?** → Reject one (duplicate entry)
- **Not sure?** → Follow-up with notes for manual review

---

## Output Files Explained

### File Structure

All files go to: `review/`

```
review/
├── approved/
│   └── upload_20260530_212146_realistic_export_APPROVED.csv
├── followup/
│   └── upload_20260530_212146_realistic_export_FOLLOWUP.csv
└── rejected/
    └── upload_20260530_212146_realistic_export_REJECTED.csv
```

### What's in Each File

**All three files contain:**
- All original Givebutter fields (Name, Email, Phone, Amount, Date, etc.)
- Validation results (Tier, Issues, Suggestions)
- Your decisions

**FOLLOWUP file adds:**
- `Operator_Notes` column with your comments

---

## Validation Rules Reference

### Email Validation

**Typos detected (auto-corrected):**
- `gmai.com` → `gmail.com`
- `gmal.com` → `gmail.com`
- `yaho.com` → `yahoo.com`
- `hotmial.com` → `hotmail.com`
- (and 5+ more patterns)

**Domain check:**
- Validates against list of known valid domains
- Flags unusual/new domains for review

### Phone Validation

**Valid formats:**
- 10 digits: `5550123948` → formatted as `(555) 012-3948`
- 11 digits with leading 1: `15550123948`

**Flagged as invalid:**
- Sequential: `1234567890`
- All same digit: `5555555555`
- Reserved test: `555-0000` to `555-0199`
- Wrong length: < 10 or > 11 digits

**Flagged as unusual (warning):**
- Non-standard formatting: dots, weird spacing
- Area codes starting with 0 or 1

### Amount Validation

**Checks against:**
- Historical range (min/max from approved records)
- High-dollar threshold: ≥ $1,000 (configurable)

### Name & Address Validation

**Name:**
- Length check (typically 2-100 characters)
- Character validation (letters, numbers, hyphens, apostrophes)

**Address:**
- Completeness (Address, City, State present)

---

## Common Scenarios

### Scenario 1: Email Typo

```
Name:        Morgan Davis
Email:       morgan.davis42@gmai.com
Tier:        ⚠ WARNING
Suggestions: Email typo detected. Consider: morgan.davis42@gmail.com
```

**Decision:** APPROVED
- The suggestion looks right (common typo)
- Email will be corrected

---

### Scenario 2: High-Dollar Donation

```
Name:        Riley Wilson
Amount:      $2,000.00
Tier:        ⚠ WARNING
Suggestions: High-dollar donation (>= $1000)
```

**Decision:** FOLLOW-UP
- Add note: "Verify this is a real donation—follow up with donor"
- Someone should double-check before importing to database

---

### Scenario 3: Duplicate Detected

```
Name:        Taylor Smith
Email:       taylor.smith@gmail.com
Phone:       555-012-3948
Tier:        ⚠ WARNING
Issues:      Duplicate: Phone match: tr_8b291c3d4e
```

**Decision:** FOLLOW-UP
- Add note: "Phone matches record tr_8b291c3d4e—same person or duplicate?"
- Your team can investigate whether these are two gifts from same donor or a data entry error

---

### Scenario 4: Invalid Phone

```
Name:        Casey Brown
Phone:       1234567890
Tier:        ✗ FAIL
Issues:      Invalid: Sequential test number
```

**Decision:** REJECTED or FOLLOW-UP
- This is a test entry, not real
- Usually REJECT (don't import)
- Or FOLLOW-UP if you want to verify with source

---

## Folder Structure

```
Givebutter/

UPLOAD & PROCESS:
├── scripts/uploader/app.py          ← Web application (run this)
├── scripts/processor.py              ← Validation engine

CONFIGURATION:
├── config/rules/rules_v2.4.json      ← Validation rules (JSON)
└── config/reference_list.json        ← Learned patterns

INPUT TRACKING:
├── intake/new/                       ← Where uploads land temporarily
└── archive/                          ← Processed files (audit trail)

YOUR WORKFLOW (review/):
├── processing/                       ← Files currently being reviewed (in UI)
├── approved/                         ← Output: *_APPROVED.csv
├── followup/                         ← Output: *_FOLLOWUP.csv
└── rejected/                         ← Output: *_REJECTED.csv
```

---

## Troubleshooting

### Problem: Upload button doesn't work

**Check:**
1. Is Flask running? (You should see `Running on http://127.0.0.1:8000`)
2. Is browser showing the right URL? (http://127.0.0.1:8000)
3. Is the file a valid CSV? (Can you open it in Excel?)

**Fix:**
- Restart the Flask app: `python3 scripts/uploader/app.py`

---

### Problem: No records appear after upload

**Check:**
1. Did you see the summary message? (If yes, upload worked)
2. Does the page show "Processing..."? (If yes, wait—it's still validating)
3. Are all records PASS tier? (If yes, no warnings to show—all clean!)

**Likely:** Your file has no issues. All records are APPROVED tier (green). Check the summary message.

---

### Problem: A record looks correct but is flagged as FAIL

**Example:** Record has a valid email but is marked FAIL

**What to do:**
1. Double-check: Is it really valid?
2. If yes, → Click APPROVED anyway (your judgment overrides system)
3. Tell your tech lead: "This record should not have been flagged"
4. Tech lead will refine the validation rules

**Bottom line:** You're the safety check. If you think it's correct, approve it.

---

## How The System Learns

When you approve records, the system learns:

1. **You approve many records** with `example.com` email domain
2. **System learns:** `example.com` is a valid domain
3. **Next upload:** System doesn't flag `example.com` emails
4. **Result:** Fewer false alarms over time

Your approvals make the system smarter.

---

## FAQ

**Q: Can I edit records in the UI?**

A: Not yet. You can only approve/reject/follow-up. If a record needs editing, mark it FOLLOW-UP with a note explaining what needs to change.

---

**Q: Are my notes saved?**

A: Yes. Notes are saved in the `_FOLLOWUP.csv` file. Your tech lead can see them.

---

**Q: Can I undo my decisions?**

A: If you haven't clicked "Save Decisions" yet, you can change your mind freely. After saving, the files are generated. You can re-upload and review again.

---

**Q: What if I approve something by mistake?**

A: It goes to `_APPROVED.csv`. Before importing, your tech lead can review the file and catch any problems.

---

**Q: How do I know if the system is working?**

A: Click the health check: http://127.0.0.1:8000/health

You should see: `{"status": "ok", "version": "3.0"}`

---

## Next Steps

1. **Ask your tech lead** to show you the system once
2. **Upload a test file** from Givebutter
3. **Walk through the review** (approve a few, follow-up on some)
4. **Click "Save Decisions"** and check the output files
5. **Ask questions** if anything is unclear

You're now ready. Thank you for being the data quality guardian! 🎉

---

**Last updated:** May 30, 2026
**Version:** 3.0
**Status:** Production Ready
