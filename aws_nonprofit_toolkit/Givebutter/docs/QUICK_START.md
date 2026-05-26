# Quick Start Reference Card
## Givebutter Donation Processor — Print This!

**This is a one-page reference. Keep it at your desk or print it. For full details, see [OPERATOR_MANUAL.md](../OPERATOR_MANUAL.md).**

---

## Your Daily Workflow (3 Steps)

```
1. UPLOAD CSV          2. WAIT FOR FLAG       3. REVIEW & DECIDE
   (once per day/      (automatic)            (move approved/
    week/month)        (5-30 seconds)         rejected)
   
   Go to:              System does:           You do:
   localhost:5000      Checks all rows       Look at flagged
                       Flags problems        Say yes/no
```

---

## Folder Guide (Where Things Go)

| Folder | What's Here | What You Do |
|--------|-----------|-----------|
| **intake/new/** | Your uploads (before processing) | Nothing—processor handles it |
| **review/flagged/** | Records with problems | **Review them** each morning |
| **review/approved/** | Problems you approved | Move good flagged files here |
| **review/rejected/** | Problems you didn't approve | Move bad flagged files here |
| **intake/archive/** | Backup of original uploads | Leave alone (audit trail) |
| **intake/failed/** | Files that couldn't process | Ask tech lead if file appears here |

---

## Moving Files (Mac & Windows)

**Mac:**
- Cut: `Cmd + X`
- Paste: `Cmd + V`

**Windows:**
- Cut: `Ctrl + X`
- Paste: `Ctrl + V`

**Process:**
1. Open file browser
2. Find file in `review/flagged/`
3. Cut it
4. Open `review/approved/` or `review/rejected/`
5. Paste it

---

## Approval Checklist

Before moving a file to `review/approved/`, verify:

- [ ] Did I actually look at the records? (Not just moving blindly)
- [ ] Is the problem real? (Not a false alarm)
- [ ] Is it consistent across rows? (Multiple instances, same issue)
- [ ] Is fixing it important? (Affects donor communication or accounting?)
- [ ] Am I confident? (Not guessing)

**If any "no"** → Move to `review/rejected/` instead.

---

## Key Terms (One Sentence Each)

| Term | Definition |
|------|-----------|
| **CSV** | A file format (like Excel) that holds donor data |
| **Flagged** | The system found a problem and highlighted it for you to review |
| **Rule** | An instruction (like "gmai.com is probably gmail.com") that the system uses to check data |
| **Approved** | You reviewed a flagged record and said "yes, fix this" |
| **Rejected** | You reviewed a flagged record and said "no, it's actually fine" |
| **Escalation** | When you tell your tech lead about a pattern so they can make it into a rule |

---

## What Gets Flagged?

The system flags issues based on **validation rules** that your tech lead configures.

**Examples:**
- **Email typos:** gmai.com, gmal.com, yaho.com, hotmial.com
- **Missing emails:** No email address at all
- **Incomplete data:** Missing donation amounts or dates
- **Format errors:** Invalid phone numbers or zip codes
- **Custom rules:** Whatever patterns your tech lead adds

**V2 Update:** The system now has TWO layers of validation:
1. **Upstream** — Pre-form validation prevents errors BEFORE they enter Givebutter
2. **Downstream** — Processor catches what escapes upstream

See [PRD.md](../PRD.md) for how this works, or [DEVELOPER.md](DEVELOPER.md) for the complete rules list.

---

## Common Tasks (Quick How-To)

### "How do I upload a file?"
1. Go to `http://localhost:5000` in your web browser
2. Click "Choose File"
3. Select your Givebutter CSV
4. Click "Upload"
5. Wait 5-30 seconds for flagged records to appear in `review/flagged/`

### "How do I review flagged records?"
1. Open `review/flagged/` folder
2. Open the CSV file (with Excel or Google Sheets)
3. Look at each row and ask: "Is this actually a problem?"
4. When done, move file to `review/approved/` or `review/rejected/`

### "How do I move a flagged file?"
1. Open `review/flagged/`
2. Right-click the file
3. Click "Cut" (or press Cmd+X / Ctrl+X)
4. Open `review/approved/` or `review/rejected/`
5. Right-click empty space
6. Click "Paste" (or press Cmd+V / Ctrl+V)

### "How do I tell my tech lead about a pattern?"
1. Count the instances (e.g., "43 times")
2. Note the pattern (e.g., "gmal.com → gmail.com")
3. Tell your tech lead: "I found 43 instances of [pattern]"
4. Wait for them to propose a rule
5. Review and approve when ready

### "How do I undo a move?"
1. Open the folder you moved the file to
2. Right-click the file
3. Click "Cut"
4. Go back to `review/flagged/`
5. Click "Paste"

---

## Emergency Contacts

| Issue | Who to Contact | What to Say |
|-------|---|---|
| "How do I upload?" | Tech Lead | "Can you show me how to upload?" |
| "File upload failed" | Tech Lead | "I uploaded [filename] but got an error: [error]" |
| "File in intake/failed/" | Tech Lead | "My file [name] is in intake/failed/, what's wrong?" |
| "Processor won't start" | Tech Lead | "The processor crashed at [time]" |
| "Should I approve this?" | Your Manager | "Is [record] correct or should it be fixed?" |
| "File stuck in review/flagged/" | Tech Lead | "My file [name] won't process, it's stuck" |

---

## Red Flags (When to Ask for Help)

- ⚠️ Files stuck in `intake/new/` for >5 min
- ⚠️ No files appearing in `review/flagged/` (but processor is running)
- ⚠️ File in `intake/failed/` (format error)
- ⚠️ Same rule flagging records that look correct
- ⚠️ Processor console showing errors

**When in doubt, ask your tech lead.**

---

## Pro Tips

✨ **Bookmark this page** — You'll come back to it  
✨ **Print this page** — Keep it at your desk  
✨ **Set a calendar reminder** — For your upload schedule  
✨ **Review flagged files same day** — Don't let them pile up  
✨ **Report patterns early** — Rules improve over time  
✨ **Always move, never delete** — Keep the audit trail  

---

## Key Numbers to Remember

| Metric | Value |
|--------|-------|
| Processing time | 5-30 seconds per file |
| Max upload size | 16 MB (≈500k+ donations) |
| Time to add a rule | 1-2 hours after you report a pattern |
| Confidence threshold for rules | 60%+ (too low = rejected) |
| Min pattern size | 3+ instances (too few = rejected) |

---

## Understanding V2 (Dual-Validation System)

**New in V2:** The system prevents errors in TWO ways:

1. **Upstream** (on your website)
   - Real-time validation as donor fills form
   - "Did you mean gmail.com?" suggestions
   - Prevents ~70% of errors before Givebutter

2. **Downstream** (this system)
   - Catches what escaped upstream
   - You review and approve/reject
   - System learns from your decisions

**Result:** Cleaner data, less review work, smarter system.

See [PRD.md](../PRD.md) for details.

---

## If You Get Stuck

1. **Check this card** — You're probably here
2. **Check [OPERATOR_MANUAL.md](../OPERATOR_MANUAL.md)** — Search for your question
3. **Check [FAQ.md](FAQ.md)** — Browse questions by category
4. **Need to understand V2?** — Read [PRD.md](../PRD.md)
5. **Ask your tech lead** — That's what they're for!

---

## Your Role (In One Sentence)

**You are the data quality guardian. You upload files, review what the system flags, and say yes or no to each problem.**

---

**Givebutter Donation Processor | Quick Start Reference | V2 (May 26, 2026)**

---

### One-Page Cheat Sheet Format

```
┌─────────────────────────────────────────────────────────┐
│      GIVEBUTTER PROCESSOR — QUICK START CHEAT SHEET      │
├─────────────────────────────────────────────────────────┤
│ YOUR JOB: Upload → Review Flagged → Approve/Reject     │
│                                                         │
│ UPLOAD:              REVIEW:           MOVE:            │
│ localhost:5000      review/flagged/    Cmd/Ctrl + X    │
│ Click upload        Open CSV file      Paste to:        │
│ Choose file         Read each row      approved/        │
│ Wait 5-30 sec       Ask: Problem?      or rejected/    │
│                     YES → approved     V                │
│                     NO → rejected                       │
│                                                         │
│ QUICK QUESTIONS?                                        │
│ ├─ How to upload? → See step 1 above                  │
│ ├─ How to move? → Cmd/Ctrl+X, then paste              │
│ ├─ What to approve? → Use checklist on reverse side   │
│ └─ Still stuck? → Ask your tech lead                  │
│                                                         │
│ EMERGENCY: Processor broken? Tech lead NOW!            │
├─────────────────────────────────────────────────────────┤
│ KEY FOLDERS:                                            │
│ review/flagged/ = Your work area (open daily)         │
│ review/approved/ = Problems you approved              │
│ review/rejected/ = Problems you didn't approve        │
│ intake/archive/ = Backup (leave alone)               │
│ intake/failed/ = Bad files (ask tech lead)           │
└─────────────────────────────────────────────────────────┘
```

---

**For full details, open [OPERATOR_MANUAL.md](../OPERATOR_MANUAL.md) or check [INDEX.md](INDEX.md) for links to other docs.**
