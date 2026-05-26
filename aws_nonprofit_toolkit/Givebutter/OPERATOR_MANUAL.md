# Operator's Manual
## How to Use the Givebutter Donation Processor

---

## Introduction: Why This System Exists

Every nonprofit receives donations through platforms like Givebutter, Square, or Stripe. The data looks clean when you first download it, but it contains hidden problems:

- A donor typed "gmai.com" instead of "gmail.com" — you can't contact them
- The same person donated twice with slightly different names — your records show two donors instead of one
- A donation amount is missing — your accounting report is incomplete

These errors compound over time. A thousand small mistakes become a headache when you're reconciling accounts or sending donor receipts.

**This system catches those problems before they become headaches.**

---

## Your Role

You are the **data quality guardian**. Your job:

1. **Upload** donation CSV files
2. **Review** records the system flags as problematic
3. **Decide** whether each flagged record should be corrected
4. **Help the system learn** — when you spot patterns, the system remembers them for future files

You're not responsible for fixing the data yourself (the system does that), but you ARE responsible for saying "yes, that's wrong" or "no, that's actually correct."

### Your Responsibility Flow

```
         YOU (Operator)
              │
    ┌─────────┼─────────┐
    │         │         │
  Upload    Review    Decide
   CSV     Flagged    Approve/
  Files    Records    Reject
    │         │         │
    └─────────┼─────────┘
              │
         Report
        Patterns
              │
         Rules
        Improve
```

---

## Quick Start: First Time Setup

**Step 0: Get access**
Ask your technical lead to:
- Ensure the uploader is running on your computer
- Give you the uploader URL (usually `http://localhost:5000`)
- Show you where the `review/flagged/` folder is on your computer

**Step 1: Open the uploader**
- Go to `http://localhost:5000` in your web browser
- You should see a simple form: "Upload Givebutter Donation CSV"

**Step 2: Export from Givebutter**
- Log into Givebutter
- Go to Donations → Export
- Download the CSV file (usually named something like `donations_2026_05.csv`)

**Step 3: Upload**
- Click "Choose File" on the uploader form
- Select your downloaded CSV
- Click "Upload"
- **You should see:** "File received" (it works!)

**That's it!** The system now begins processing your file.

---

## The 5-Step Workflow

### Complete Workflow Diagram

```
STEP 1: UPLOAD                 STEP 2: AUTO-PROCESS         STEP 3: REVIEW
(You do this)                  (System does this)           (You do this)
        │                               │                           │
        │                               │                           │
   ┌────▼─────┐              ┌──────────▼──────────┐     ┌──────────▼──────────┐
   │  Upload   │              │ System checks every │     │ Open flagged file   │
   │  CSV file │─────────────▶│ row against rules   │────▶│ Look at each record │
   │ (go to    │              │ and flags problems  │     │ Ask: "Is this      │
   │ localhost │              │                     │     │  really a problem?" │
   │  :5000)   │              └──────────┬──────────┘     │                     │
   └──────────┘               │          │ (if no issues) │ Answer: YES or NO   │
                              │          │                └──────────┬──────────┘
                              │    ┌─────▼──────┐                    │
                              │    │ File is    │        ┌───────────┼───────────┐
                              │    │ clean (0   │        │           │           │
                              │    │ problems)  │        │      YES  │      NO   │
                              │    └────────────┘    STEP 4        │           │
                              │                     APPROVE/      │           │
                    ┌─────────▼──────────┐         REJECT         │           │
                    │ Flagged CSV file   │          │              │           │
                    │ appears in review/ │    ┌─────▼────┐    ┌───▼──────┐
                    │ flagged/           │    │  Move to │    │  Move to │
                    │ (with problematic  │    │ review/  │    │ review/  │
                    │  records)          │    │ approved │    │ rejected │
                    │                    │    │ folder   │    │ folder   │
                    └────────────────────┘    └────┬─────┘    └──────────┘
                                                   │
                                              STEP 5
                                            (Request
                                           Rule Update)
                                                   │
                                            ┌──────▼──────────┐
                                            │  Tell tech lead:│
                                            │ "I found a pattern"
                                            │  Tech lead      │
                                            │ proposes rule   │
                                            │ You approve     │
                                            │ Rule is added   │
                                            └─────────────────┘
```

---

### Step 1️⃣: Upload a CSV File

**Where:** The web uploader (`http://localhost:5000`)

**What to upload:**
- Givebutter donation exports (CSV format)
- Should have columns: donor name, email, donation amount, date, etc.

**What happens next:**
- The uploader saves your file with a timestamp: `upload_20260525_143022_donations.csv`
- A folder is created: `intake/new/` (you don't need to look here)
- The processor starts analyzing your file automatically

**Time to process:** Usually 5-10 seconds for 100 donations. Larger files take longer.

---

### Step 2️⃣: Auto-Processing (System Does This)

You don't need to do anything here, but it helps to understand what's happening:

**The system:**
1. Reads your CSV file
2. Checks every row against known rules
3. **Flags** any records that don't match the rules
4. Creates a new file with only the flagged records

**Example:** 
- Your file has 100 donations
- System finds that 3 have invalid emails (missing the @ symbol)
- System finds 7 have "gmai.com" instead of "gmail.com"
- System flags those 10 records
- A new file appears: `flagged_20260525_143045_upload_20260525_143022_donations.csv`

**What counts as "flagged"?**
Currently, the system flags:
- Missing email addresses
- Typos in common email domains (gmai.com, gmal.com, yaho.com, hotmial.com)
- Donations with incomplete information

(This list grows as you approve new rules.)

---

### Step 3️⃣: Review Flagged Records

**Where:** The `review/flagged/` folder on your computer

**What you see:**
- CSV files with the problematic records
- One file per upload (so you can track which batch had the issue)
- Each file shows only the rows the system thinks are wrong

**What to look for:**
1. Is the problem real? ("Yes, that email is definitely a typo")
2. Is it consistent? ("I see the same typo in 5 records")
3. Will fixing it help? ("Yes, we need their correct email to send a thank you")

**Example: The "gmal.com" Incident**

You see a flagged file with 43 donations, all from May. All 43 have the email domain "gmal.com" (missing the 'i').

You check:
- ✅ Is it a typo? Yes (missing 'i')
- ✅ Are they all wrong? Yes, all 43
- ✅ Should we fix them? Yes, they're all mistakes

**Decision: This is good. Move to the next step.**

### Decision Tree for Review

```
┌──────────────────────────────────────┐
│   I see a flagged file. Now what?    │
└──────────────┬───────────────────────┘
               │
        ┌──────▼──────┐
        │ Look at the │
        │   records   │
        └──────┬──────┘
               │
    ┌──────────┴──────────┐
    │                     │
    │ Are these real      │ Can't tell yet?
    │ problems?           │ Leave it here.
    │                     │ Review tomorrow.
    ├──YES──┐        ┌────┴─────┐
    │       │        │           │
    │   YES:        NO:        MAYBE:
    │ Move to      Move to    Leave in
    │ review/     review/    review/
    │ approved/   rejected/  flagged/
    │ folder      folder
    │
    │ ✅ Good to fix  ❌ Actually   ⏳ Undecided
    │                  fine as-is
    │
    └─────────────────────────┘
```

---

### Step 4️⃣: Approve or Reject

Once you've reviewed a flagged file, you make a decision:

**Option A: Approve** ("Yes, these are all problems that need fixing")
- Move the flagged file to: `review/approved/`
- This signals: "I've reviewed these, they're real issues, please fix them"

**Option B: Reject** ("No, these are actually fine as they are")
- Move the flagged file to: `review/rejected/`
- This signals: "I've looked at these, but they don't need fixing"

**Option C: Defer** (leave it in `review/flagged/`)
- You're not sure yet
- That's fine—review it tomorrow
- No files are auto-deleted, so you can take your time

**How to move files:**
1. Open your file browser
2. Navigate to `review/flagged/`
3. Right-click the file
4. Choose "Cut" (Cmd+X on Mac, Ctrl+X on Windows)
5. Navigate to `review/approved/` or `review/rejected/`
6. Paste (Cmd+V or Ctrl+V)

---

### Step 5️⃣: Request Rule Updates

When you see a pattern emerging—"I've approved 5 flagged files with this same typo, and we should just catch it automatically next time"—the system is ready to learn.

**What happens:**
1. You move approved files to `review/approved/`
2. You contact your technical lead (or use a rule request form, if your team has one)
3. You say: "I found 43 instances of 'gmal.com' → 'gmail.com' in May's batch"
4. Your tech lead analyzes this and proposes a new rule to Claude AI
5. Claude suggests: "Add this to the automatic checklist"
6. Your tech lead reviews Claude's suggestion, updates the rules file, and re-runs the processor
7. **Next time** a file comes in with `gmal.com`, it's automatically caught and flagged

**You don't have to do anything here—just report the pattern to your tech lead.**

### Rule Escalation Flow (How Patterns Become Rules)

```
YOU NOTICE              TECH LEAD                  CLAUDE AI              NEXT BATCH
A PATTERN                PROPOSES                  ADVISES                OF FILES
    │                        │                          │                     │
    │                        │                          │                     │
"I see the same        "Let me ask Claude       "I found 43               Uses
typo in 5 files:      about this pattern"      instances of             new
gmal.com → gmail.com"        │                 gmal.com → gmail.com"    rule
    │                        │                          │               (auto
    └───────Tell────────────▶│                          │             detects)
              Tech Lead       │         "This looks               │
                              └────Proposes────────────▶│        Rules file
                                   to Claude                │    is updated
                                                           │
                                        ┌──────────────────▼─────────┐
                                        │  You review Claude's       │
                                        │  suggestion (in chat)      │
                                        │  "Yes, that looks right"   │
                                        └────────┬──────────────────┘
                                                 │
                                                 │ "Update the
                                                 │  rules file"
                                                 ↓
                                        Tech lead edits
                                        rules file &
                                        version bump
                                                 │
                                                 └─────────────────┐
                                                                   │
                                                                   ↓
                                                    File is processed
                                                    with new rule
                                                    (gmal.com auto-
                                                     caught!)
```

**Timeline:** Usually 1-2 hours from spotting the pattern to it becoming an active rule.

---

## The Folders You'll Use Every Day

### `intake/new/` — Upload Landing Zone
- **What:** Where files land after you upload them
- **Who can write:** Only the uploader
- **Who can read:** You (to check if the upload worked)
- **Action:** Don't delete files here; the processor moves them automatically

### `review/flagged/` — Issues Found
- **What:** Records the system thinks are problematic
- **Who can write:** Only the processor
- **Who can read:** YOU (this is where you work)
- **Action:** Review each file, then move to `approved/` or `rejected/`

**Check this folder first thing each day:**
```bash
ls review/flagged/
# You'll see files like: flagged_20260525_143045_upload_*.csv
```

### `review/approved/` — Fixes You Approved
- **What:** Flagged records you've reviewed and said "yes, fix these"
- **Who can write:** YOU
- **Who can read:** Manager, Tech Lead
- **Action:** Move files here when you approve them. Your tech lead may ask you for these when building rule updates.

### `review/rejected/` — Not Needed
- **What:** Flagged records you've reviewed and said "no, these are fine"
- **Who can write:** YOU
- **Who can read:** Archive / audit trail
- **Action:** You can delete these after a month or so (or keep for audit trail)

---

## Understanding Rules (Plain English Edition)

A **rule** is a simple instruction the system follows. Think of it like a checklist.

**Rule:** "If an email ends in 'gmai.com', it's probably a typo for 'gmail.com'"

**What the system does:**
- When processing a file, it checks every email
- If it finds `@gmai.com`, it **flags that row**
- You review it and say "yes, that's a typo" (approve)
- Tech lead adds the rule permanently: "Change gmai.com → gmail.com"
- Next file: `@gmai.com` is auto-corrected before you even see it

**Current Rules** (as of May 2026):

| Problem | Solution | Why |
|---------|----------|-----|
| `gmai.com` | → `gmail.com` | Common typo (missing 'i') |
| `gmal.com` | → `gmail.com` | Common typo (transposition) |
| `gamil.com` | → `gmail.com` | Common typo |
| `yaho.com` | → `yahoo.com` | Common typo (missing 'o') |
| `hotmial.com` | → `hotmail.com` | Common typo |

**How rules are added:**
1. You notice a pattern in flagged files
2. You tell your tech lead
3. Tech lead proposes it to Claude (the AI advisor)
4. You review Claude's proposal ("Does this look right?")
5. Tech lead updates the rules file
6. Rules are active for the **next batch of files you upload**

---

## Approval Checklist

Before you move a flagged file to `review/approved/`, ask yourself:

- [ ] **Have I actually looked at the flagged records?** (Not just moved them blindly)
- [ ] **Is the problem real?** (Not a false alarm)
- [ ] **Is it consistent across records?** (Not a one-off)
- [ ] **Is fixing it worth our time?** (Will it impact donor communication or accounting?)
- [ ] **Am I confident this is the right fix?** (Not guessing)

**If you answer "no" to any of these, move the file to `review/rejected/` instead.**

---

## Common Questions (FAQ)

### Q: I uploaded a file, but I don't see it in `review/flagged/`. Why?

**Possible reasons:**

1. **The file has no problems** — All records passed the checks, so there's nothing to flag. This is good! Your data is clean.

2. **The processor hasn't finished yet** — Processing can take 5-30 seconds depending on file size. Wait a minute and check again.

3. **The file failed to parse** — The CSV format is wrong (missing columns, weird characters, etc.). Check `intake/failed/` — your file is there. Ask your tech lead for help.

**What to do:**
- Wait 30 seconds and check `review/flagged/` again
- Check `intake/failed/` for error messages
- Ask your tech lead if the processor is running

---

### Q: I rejected a flagged file by mistake. Can I undo it?

**Yes.** Just move it back:
1. Open `review/rejected/`
2. Find the file you moved by mistake
3. Cut it (Cmd+X or Ctrl+X)
4. Navigate to `review/flagged/`
5. Paste it (Cmd+V or Ctrl+V)

No records are deleted, so you can move files around freely.

---

### Q: I see the same typo in multiple files. When will it be a rule?

**Soon, but not automatically.** Here's the timeline:

1. **You notice it** → "I've seen 'gmai.com' in 5 files"
2. **You report it** → Tell your tech lead
3. **Tech lead proposes it to Claude** → Claude says "this looks like a valid typo"
4. **You review Claude's proposal** → "Yes, that's right"
5. **Tech lead adds it** → Updates the rules file
6. **Your next upload uses it** → New files are checked against the new rule

**Total time:** Usually 1-2 hours (if your tech lead is responsive)

**Why not automatic?** Because a human should always review before changing rules. We don't want to accidentally "fix" something that's actually correct.

---

### Q: What if a rule is wrong and breaks something?

**Example:** The system auto-corrects 'john.doe+work@gmail.com' to 'john.doe@gmail.com' by accident.

**Here's what happens:**
1. You notice the error when you review flagged files from the next batch
2. You tell your tech lead: "The new rule broke these 10 records"
3. Tech lead removes or refines the rule
4. The rule is disabled for future files
5. A new rule is proposed (more specific, so it doesn't break legit records)

**Bottom line:** You're the safety check. If something looks wrong, report it. Rules can always be changed.

---

### Q: Can I edit the rules myself?

**No.** Rules are stored in JSON files that require technical knowledge to edit correctly. Editing them wrong can break the processor.

**What you CAN do:**
- Review and approve/reject flagged files
- Report patterns to your tech lead
- Review and accept Claude's rule proposals

**What your tech lead does:**
- Edit the rules JSON file
- Test the new rules before deployment
- Re-run the processor

This division of labor keeps the system safe and audit-able.

---

### Q: How often should I check for flagged files?

**Depends on your upload frequency:**
- **Daily uploads** → Check `review/flagged/` each morning
- **Weekly uploads** → Check 1-2 hours after upload
- **As-needed uploads** → Check after each upload

**Pro tip:** Set a calendar reminder if you do weekly uploads. Flagged files don't go away, but reviewing them promptly helps your tech lead spot patterns faster.

---

### Q: What's the difference between "rejected" and just leaving it in "flagged"?

- **`review/flagged/`** — "I haven't decided yet" (temporary holding)
- **`review/rejected/`** — "I've looked at this and decided it's fine" (archived decision)

You can leave things in `flagged/` for days while you make up your mind. Move to `rejected/` only when you've made a final decision.

---

### Q: I accidentally deleted a flagged file. Can I get it back?

**You shouldn't be able to delete it** if you're using "move" rather than "delete." But if you did:

1. Check your Trash/Recycle Bin (it might still be there)
2. Ask your tech lead if they have backups
3. Have the original file re-uploaded

**Pro tip:** Always "move" files rather than delete them. Use Cut + Paste, not Delete.

---

## Troubleshooting

### Problem: Uploader says "File received" but nothing appears in `review/flagged/`

**Check these things:**

1. **Is the processor running?**
   - Ask: "Is someone running `python3 -m scripts.processor_v2_3`?"
   - If not, ask them to start it
   - If yes, ask them to check the console for errors

2. **Did your file actually upload?**
   - Check `intake/new/` for your uploaded file
   - Is it there with today's timestamp? If yes, the upload worked.
   - If no, the upload failed. Try again or ask your tech lead.

3. **Is your file valid?**
   - Check `intake/failed/` for error messages
   - If your file is there, there's a format problem (usually missing columns)
   - Ask your tech lead to check the CSV format

4. **Does your data have no problems?**
   - Maybe your file passed all checks! No flagged records = all clean data. This is good.
   - Processor moves clean files to `intake/archive/` silently

**What to do:**
- Wait 30 seconds and try refreshing
- Check `intake/new/`, `intake/failed/`, and `intake/archive/` manually
- If still stuck, ask your tech lead with these details:
  - File name
  - When you uploaded it
  - Whether it's in `intake/new/`, `intake/failed/`, or `intake/archive/`

---

### Problem: Processor crashed or shows an error

**Your role:**
1. Stop uploading new files
2. **Screenshot the error** (take a picture of what's on the screen)
3. Tell your tech lead:
   - "The processor crashed at [time]"
   - Show them the screenshot
   - Show them any files stuck in `intake/new/`

**Your tech lead will:**
- Restart the processor
- Debug the crash
- Have you re-upload your file

**You don't need to do anything else.** This is a technical problem, not a data problem.

---

### Problem: A flagged record looks correct, but the system says it's wrong

**Example:** You have a donor named "José García" (with accents). The system flags it, but you can see it's spelled correctly.

**What to do:**
1. Move the file to `review/rejected/` (you've reviewed it; it's fine)
2. Tell your tech lead: "The system is incorrectly flagging names with accents"
3. Tech lead will refine the rules to be smarter about Unicode names

**Bottom line:** Your judgment matters. If you think something is correct, it's correct. Flag it to your tech lead, and they'll fix the rules.

---

### Problem: Two donations look identical but aren't (possible duplicate)

**Example:** 
- John Smith, john@example.com, $50, May 10
- John Smith, john@example.com, $50, May 10
(Same person, same amount, same day—but two separate records)

**This is a duplicate.** What to do:

1. **Don't move either file to approved yet.**
2. **Tell your tech lead:** "I found possible duplicates in the May batch" and show them the details
3. **Tech lead will:**
   - Investigate if it's a real duplicate (or just a coincidence)
   - Propose a rule if duplicates are common
   - Tell you which record to keep, which to delete

**You shouldn't delete records yourself.** Duplicates are tricky (sometimes they're the same person donating twice, which is good!) so let your tech lead decide.

---

## Getting Help

### Is It a Question About...

**My workflow?** → Read this manual again (it probably answers it) or check the FAQ section above.

**How to use the uploader?** → See "Quick Start" section, or ask your tech lead to walk you through it once.

**Why a specific record was flagged?** → Ask your tech lead to explain the rule that caught it.

**A technical error or crash?** → Tell your tech lead with:
  - What happened
  - When it happened
  - What file you were uploading
  - Any error messages you saw

**Ideas for new rules** → Tell your tech lead: "I noticed a pattern in the May batch..."

### Contact Info

Your support team:
- **Tech Lead:** [Name/Email] — for technical problems and rule updates
- **Manager:** [Name/Email] — for process questions or escalations

---

## Next Steps

1. **Get access** to the uploader and folders
2. **Ask your tech lead** to walk you through uploading one test file
3. **Review the flagged records** in that test file
4. **Ask questions** — it's better to ask than to guess

You're now ready to be the data quality guardian for your nonprofit. Thank you! 🎉

---

**Last updated:** May 25, 2026
**Document version:** 1.0
