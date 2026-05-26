# Frequently Asked Questions (FAQ)

**Can't find your question? Check [INDEX.md](INDEX.md) for links to specific docs, or ask your tech lead.**

---

## 🎯 Quick Search by Category

- [Getting Started](#getting-started)
- [Uploading Files](#uploading-files)
- [Processing & Flagging](#processing--flagging)
- [Reviewing Flagged Records](#reviewing-flagged-records)
- [Approving & Rejecting](#approving--rejecting)
- [Rules & Patterns](#rules--patterns)
- [Folders & File Operations](#folders--file-operations)
- [Technical Issues & Troubleshooting](#technical-issues--troubleshooting)
- [Developer Questions](#developer-questions)

---

## Getting Started

### Q: I'm new. Where do I start?

**A:** Read in this order:
1. **[README.md](../README.md)** (5 min) — Understand what the system does
2. **[OPERATOR_MANUAL.md](../OPERATOR_MANUAL.md#quick-start-first-time-setup)** (5 min) — Do your first upload
3. **[QUICK_START.md](QUICK_START.md)** (2 min) — Print this and keep it at your desk
4. **[OPERATOR_MANUAL.md](../OPERATOR_MANUAL.md#the-5-step-workflow)** (10 min) — Learn the full workflow

**Total: 22 minutes to get going!**

---

### Q: Do I need any special software or training?

**A:** Nope! You just need:
- A web browser (Chrome, Safari, Firefox, Edge)
- A CSV file from Givebutter
- 2 minutes to learn how to upload

Everything else is built in. If you can use email, you can use this.

---

### Q: Who should I contact if I have questions?

**A:** It depends:
- **How to use the system** → Ask your tech lead
- **If something broke** → Ask your tech lead immediately
- **Questions about approval** → Ask your manager
- **General questions** → Check this FAQ first, then ask your tech lead

---

## Uploading Files

### Q: Where do I upload my CSV file?

**A:** Go to `http://localhost:5000` in your web browser. You should see a simple form that says "Upload Givebutter Donation CSV".

**Tip:** Ask your tech lead to confirm the uploader is running before you try to upload.

---

### Q: What file format does it accept?

**A:** CSV files from Givebutter. That's it.

**Note:** The file should have columns like donor name, email, amount, date. If your export is missing these, it might not work.

---

### Q: What happens right after I click "Upload"?

**A:** 
1. The system saves your file with a timestamp
2. A message appears: "File received"
3. Processing starts automatically (takes 5-30 seconds for most files)
4. Flagged records appear in the `review/flagged/` folder

**You don't need to do anything else.** The system handles it from here.

---

### Q: Can I upload the same file twice?

**A:** Yes, it's fine. The system will process it again with the current rules. This is useful if:
- New rules were added since the last upload
- You want to reprocess an old file
- You're testing something

---

### Q: What's the maximum file size I can upload?

**A:** 16 MB. That's about 500,000+ donations in one file. If your file is bigger, split it into multiple uploads.

---

## Processing & Flagging

### Q: Why isn't my file appearing in the flagged folder?

**A:** Three possibilities:

1. **Your data is clean!** No problems found = no flagged file created. Check the `intake/archive/` folder instead. This is good news!

2. **Still processing** — Wait 10-30 seconds and check again. Processing can take a moment for large files.

3. **File had errors** — Check `intake/failed/` for your file. There's probably a format issue. Ask your tech lead for help.

**What to do:**
- Wait 30 seconds and refresh
- Check `intake/new/`, `intake/failed/`, and `intake/archive/` manually
- Still stuck? Tell your tech lead the filename and when you uploaded it

---

### Q: What gets flagged?

**A:** Currently, the system flags:
- **Email typos** — gmai.com, gmal.com, yaho.com, hotmial.com, etc.
- **Missing emails** — Rows with no email address at all
- **Incomplete data** — Missing donation amounts or dates
- **Other rule violations** — Whatever rules your tech lead has set up

Check the "Understanding Rules" section in [OPERATOR_MANUAL.md](../OPERATOR_MANUAL.md#understanding-rules-plain-english-edition) for the complete list.

---

### Q: Can I tell the system what NOT to flag?

**A:** Not directly. But if the system is flagging something that's actually correct, tell your tech lead: "We shouldn't flag [thing]." They can refine the rules.

Example: "The system is flagging all names with accents (José, García). These are correct. Don't flag them."

---

## Reviewing Flagged Records

### Q: I see flagged records. What should I look for?

**A:** Ask yourself these questions:

- ✅ **Is the problem real?** (Not a false alarm)
- ✅ **Is it consistent?** (Same type of problem in multiple records)
- ✅ **Is it worth fixing?** (Will it impact donor communication or accounting?)
- ✅ **Am I confident?** (Not guessing)

See the [Approval Checklist](OPERATOR_MANUAL.md#approval-checklist) in OPERATOR_MANUAL.md for details.

---

### Q: What if I'm not sure about a flagged record?

**A:** Leave it in the `review/flagged/` folder! You can:
- Review it tomorrow
- Ask a colleague
- Ask your manager

Flagged files don't disappear. You can review them whenever you're ready.

---

### Q: I see the same problem in multiple records. What do I do?

**A:** 
1. **Count how many** (e.g., "43 instances of gmal.com → gmail.com")
2. **Tell your tech lead** — "I found 43 of the same typo in the May batch"
3. **Your tech lead will propose a rule** to catch it automatically next time
4. **You'll review and approve the rule**
5. **Future uploads will auto-catch it**

See Step 5 in [OPERATOR_MANUAL.md](../OPERATOR_MANUAL.md#step-5️⃣-request-rule-updates).

---

## Approving & Rejecting

### Q: What's the difference between "approved" and "rejected"?

**A:**
- **Approved** ("Yes, fix these") → Move to `review/approved/`  
  You've reviewed them and they need to be fixed
- **Rejected** ("No, these are fine") → Move to `review/rejected/`  
  You've reviewed them and they're actually okay as-is
- **Undecided** (leave in `review/flagged/`)  
  You haven't made up your mind yet

---

### Q: How do I move a file from one folder to another?

**A:** Easy:
1. Open your file browser
2. Find the file in `review/flagged/`
3. Cut it (Cmd+X on Mac, Ctrl+X on Windows)
4. Go to `review/approved/` or `review/rejected/`
5. Paste it (Cmd+V or Ctrl+V)

**Pro tip:** Don't use "Delete". Always "Move" so you keep an audit trail.

---

### Q: I moved a file to rejected by mistake. Can I undo it?

**A:** Yes! Just move it back:
1. Open `review/rejected/`
2. Find the file
3. Cut it (Cmd+X or Ctrl+X)
4. Go back to `review/flagged/`
5. Paste it (Cmd+V or Ctrl+V)

Nothing is deleted, so you can move files around freely.

---

### Q: How often should I review flagged files?

**A:** Depends on how often you upload:
- **Daily uploads** → Check `review/flagged/` each morning
- **Weekly uploads** → Check within 1-2 hours
- **As-needed uploads** → Check after uploading

**Pro tip:** Set a calendar reminder if you have a regular upload schedule.

---

## Rules & Patterns

### Q: What is a "rule" exactly?

**A:** A rule is a simple instruction the system follows. Think of it like a checklist item.

**Example rule:** "If an email ends in @gmai.com, it's probably a typo for @gmail.com"

**What happens:**
- System checks every email in a file
- Finds ones ending in @gmai.com
- Flags those records
- You review and approve them
- Rule becomes permanent
- Next file: @gmai.com records are auto-flagged

See [Understanding Rules](OPERATOR_MANUAL.md#understanding-rules-plain-english-edition) in OPERATOR_MANUAL.md.

---

### Q: Can I create my own rules?

**A:** No. But you can:
1. **Spot a pattern** — "I keep seeing the same typo"
2. **Tell your tech lead** — "Here's what I found"
3. **Tech lead proposes it** — Sends it to Claude AI
4. **You review** — "Yes, that's a real problem"
5. **Tech lead adds it** — Updates the rules file
6. **It's active** — For your next upload

You're the one who identifies patterns. Your tech lead makes them into rules.

---

### Q: When will a pattern I report become a rule?

**A:** Usually 1-2 hours:
1. You tell your tech lead
2. Tech lead proposes to Claude (10 min)
3. You review Claude's suggestion (5 min)
4. Tech lead updates rules file (5 min)
5. Your next upload uses the new rule

**Why not automatic?** Because we want a human to approve every rule. Better safe than sorry.

---

### Q: What if a rule is wrong and breaks something?

**A:** Tell your tech lead immediately with details:
- "The new rule auto-corrected 'john.doe+work@gmail.com' to 'john.doe@gmail.com' by mistake"
- Your tech lead will refine or remove the rule
- A new, better rule will be proposed
- Rules can always be changed

You're the safety check. If something looks wrong, report it.

---

## Folders & File Operations

### Q: Where do files go when I upload them?

**A:** Here's the journey:

```
intake/new/  (you upload here via web form)
    ↓
    ↓ (system processes)
    ├─ review/flagged/  (if problems found)
    │   ↓
    │   ├─ review/approved/  (you move good ones here)
    │   └─ review/rejected/  (you move bad ones here)
    │
    └─ intake/archive/  (original file, for audit trail)
```

---

### Q: What's in each folder?

**intake/new/**
- Where uploads land before processing
- **You don't need to do anything here.** Processor moves files automatically.

**review/flagged/**
- Records the system thinks are problems
- **You work here.** Review each file and move to approved/rejected.

**review/approved/**
- Files you've approved (definitely problems that need fixing)
- **Used by tech lead** to spot patterns and create rules

**review/rejected/**
- Files you rejected (actually fine as-is)
- **Archive.** Can be deleted after a month or kept for audit trail.

**intake/archive/**
- Original uploads (for backup/audit trail)
- **Keep forever** for auditing who uploaded what and when

**intake/failed/**
- Files that couldn't be processed (format errors)
- **Ask your tech lead** if a file appears here

---

### Q: Can I delete files?

**A:** You *can*, but **don't**. Instead:
- Move approved files to `review/approved/` (audit trail)
- Move rejected files to `review/rejected/` (audit trail)
- Keep originals in `intake/archive/` (backup)

This way you have a record of everything. Always use "Move" not "Delete".

---

### Q: What if I accidentally deleted a file?

**A:** Check your Trash/Recycle Bin first. If it's gone:
1. Ask your tech lead if there are backups
2. Have the original file re-uploaded

For future: always use "Move" instead of "Delete".

---

## Technical Issues & Troubleshooting

### Q: The uploader says "File received" but nothing appears in review/flagged/

**A:** Check in this order:

1. **Is the processor running?**
   - Ask: "Is someone running the processor right now?"
   - If no: ask them to start it
   - If yes: ask them to check the console for errors

2. **Did your file actually upload?**
   - Check `intake/new/` for your file (with today's timestamp)
   - If there: upload worked, now wait for processing
   - If not: upload failed, try again

3. **Is your file valid?**
   - Check `intake/failed/` for your file
   - If there: file format is wrong (missing columns, weird characters)
   - Ask your tech lead to check the CSV format

4. **Did your data have no problems?**
   - Check `intake/archive/` for your file
   - If there: all records passed checks! Your data is clean. This is good!

**Still stuck?**
- Wait 30 seconds and try again
- Take a screenshot of what you see
- Tell your tech lead:
  - Filename
  - When you uploaded it
  - Which folder it's in (new/failed/archive)

---

### Q: I uploaded a file but the processor crashed or showed an error

**A:** Your role:
1. **Stop uploading** new files
2. **Take a screenshot** of the error
3. **Tell your tech lead:**
   - "The processor crashed at [time]"
   - Show screenshot
   - Show any files stuck in `intake/new/`

**Tech lead will:**
- Restart the processor
- Debug the crash
- Ask you to re-upload

You don't need to do anything else.

---

### Q: A flagged record looks correct, but the system says it's wrong

**A:** Example: You have a donor named "José García" (with accents). The system flags it, but you can see it's spelled correctly.

**What to do:**
1. Move the file to `review/rejected/` (you've reviewed it; it's fine)
2. Tell your tech lead: "The system is incorrectly flagging names with accents"
3. Tech lead will refine the rules

**Your judgment matters.** If you think something is correct, it IS correct. Flag it to your tech lead, and they'll fix the rules.

---

### Q: I see possible duplicate donations. What should I do?

**A:** Example: 
- John Smith, john@example.com, $50, May 10
- John Smith, john@example.com, $50, May 10
(Same person, same amount, same day—but two separate records)

**Don't delete records yourself.** Instead:
1. Tell your tech lead: "I found possible duplicates in the May batch"
2. Show them the details
3. Tech lead will investigate (is it a real duplicate, or did someone donate twice?)
4. Tech lead tells you which to keep, which to delete

Sometimes duplicates are legitimate (someone donated twice!), so let a human decide.

---

### Q: The processor is stuck. How do I know?

**A:** Signs:
- Files in `intake/new/` not moving after 5 minutes
- No new files in `review/flagged/` after uploading
- Console shows errors or hasn't updated in a while

**What to do:**
1. Check if processor is running: `ps aux | grep processor`
2. If running: ask a tech lead to check the console
3. If not running: ask tech lead to restart it
4. After restart: re-upload your file

---

## Developer Questions

### Q: How do I add a new rule?

**A:** Process:
1. Operator spots a pattern and tells you
2. You propose to Claude AI (using the skill in `skills/claude_skill_v2.6_cost_optimized.md`)
3. Claude returns a JSON proposal
4. You review and update `config/rules/rules_v2.X.json`
5. Bump version (v2.4 → v2.5)
6. System auto-discovers the new rules
7. Next upload uses them

See [Adding New Rules](DEVELOPER.md#adding-new-rules) in DEVELOPER.md.

---

### Q: How do I validate a rules file?

**A:** 
```bash
python3 -m scripts.processor_v2_3 --validate config/rules/rules_v2.5.json
```

Or just try loading it:
```python
import json
with open('config/rules/rules_v2.5.json') as f:
    rules = json.load(f)
print(f"Valid! Version: {rules.get('version')}")
```

---

### Q: How do I test a new rule?

**A:** 
1. Create a test CSV with known patterns
2. Update the rules file
3. Upload via the uploader
4. Check `review/flagged/` for correct flagging
5. Verify no false positives
6. Have an operator review and approve

---

### Q: What's the 11-test suite?

**A:** A set of tests that validate the processor:
- **Tests 1-5:** Core rule application (email typos, name case, etc.)
- **Tests 6-9:** Edge cases (Unicode, plus-addressing, empty CSVs)
- **Test 10:** Schema validation (rules file is well-formed)
- **Test 11:** Backward compatibility (old files work with new rules)

Details in [Testing & QA](DEVELOPER.md#testing--quality-assurance) in DEVELOPER.md.

---

### Q: How do I run the processor manually?

**A:**
```bash
source .venv/bin/activate
python3 -m scripts.processor_v2_3
```

It will start watching `intake/new/` continuously.

---

### Q: How do I understand the .env file?

**A:** Don't edit it manually. It auto-updates via `env_manager.py`.

When you:
- Add a new `rules_v2.5.json` file → `.env` updates automatically
- Import `env_manager` in any script → folders are auto-created

See [.env File (Auto-Managed)](DEVELOPER.md#env-file-auto-managed) in DEVELOPER.md.

---

### Q: How is versioning handled?

**A:**
- **Major version** (v1→v2, v2→v3): Breaking changes (structure changes, folder reorganization)
- **Minor version** (v2.3→v2.4): New rules or improvements (backward-compatible)

See [Versioning Strategy](DEVELOPER.md#versioning-strategy) in DEVELOPER.md.

---

### Q: How do I debug a rule that's not working?

**A:** 
1. Check syntax: `python3 -c "import json; json.load(open('config/rules/rules_v2.4.json'))"`
2. Check schema: `python3 -m scripts.processor_v2_3 --validate config/rules/rules_v2.4.json`
3. Test rule logic manually
4. Check the flagged CSV—what's actually being flagged?
5. Look for false positives or regex errors

See [Troubleshooting](DEVELOPER.md#troubleshooting) in DEVELOPER.md.

---

### Q: What does Claude AI do?

**A:** Claude is a rule advisor only:
1. You tell Claude about a pattern
2. Claude analyzes it and proposes JSON
3. Claude suggests confidence scores
4. **You and your team review and approve**
5. Claude never touches production data

See [Claude AI Integration](DEVELOPER.md#claude-ai-integration) in DEVELOPER.md.

---

### Q: What's the difference between v2.3 (processor) and v2.6 (skill)?

**A:**
- **v2.3** — Processor version (the engine that processes CSVs)
- **v2.6** — Skill version (the Claude AI instructions for suggesting rules)

They're related but independent. The skill can update without updating the processor.

---

### Q: How often should I update rules?

**A:** As needed:
- **New pattern spotted** → Propose immediately
- **Rule breaks something** → Fix immediately
- **Rule is too broad** → Refine immediately

There's no schedule. Rules improve as patterns emerge.

---

### Q: What happens when I deploy a new rules file?

**A:** 
1. You update `config/rules/rules_v2.5.json`
2. `env_manager` auto-detects it (highest version)
3. `.env` updates automatically
4. Next upload uses new rules
5. **No code changes, no restarts needed**

It's a zero-code promotion. Drop the file, it works.

---

## Still Have Questions?

- **Check [INDEX.md](INDEX.md)** — Links to specific sections
- **Search this FAQ** — Use Ctrl+F / Cmd+F
- **Ask your tech lead** — They're here to help
- **Open an issue** — If something is broken or confusing

---

**Last updated:** May 25, 2026  
**Document version:** 1.0
