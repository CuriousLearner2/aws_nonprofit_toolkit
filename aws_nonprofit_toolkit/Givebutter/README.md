# Givebutter Donation Processor

**Version: 2.0** | **Status: Dual-Validation Architecture** | Last Updated: May 26, 2026

## What Is This?

A smart system that helps nonprofits clean up donor data. V2.0 now prevents ~70% of errors before they enter Givebutter, while maintaining downstream correction for what escapes. 

**V2 Highlights:**
- 🛡️ **Prevention** — Real-time validation on your website catches email typos, formats, and required fields
- 🎯 **Correction** — Processor catches what escapes upstream and learns patterns
- 📚 **Learning** — System automatically improves as new patterns are approved

When you upload a CSV file of donations, the system automatically checks for problems (like email typos or duplicate records), flags them for you to review, and learns from your decisions to catch similar issues in the future.

**The human is always in control.** The system suggests fixes, but nothing happens automatically—you decide what gets corrected.

**New in V2:** See [PRD.md](PRD.md) for product strategy and validation rules architecture.

---

## The Problem We Solve

Donation files from platforms like Givebutter often contain messy data:
- **Email typos** — "gmai.com" instead of "gmail.com" (actually happened to 43 donors!)
- **Inconsistent names** — "John Smith" vs "john smith" vs "J. Smith"
- **Duplicate entries** — The same donor appears multiple times with slight variations
- **Missing information** — Incomplete addresses or phone numbers

This data needs to be clean before it goes into your CRM or accounting system. This tool makes that fast and reliable.

---

## How It Works (3 Steps)

```
1. UPLOAD              2. AUTO-FLAG           3. YOU REVIEW & DECIDE
   CSV file     →      Problems found   →     Approve or Reject
                       (automatically)
```

**In detail:**
1. **Upload** → You submit a donation CSV using the web form
2. **System flags issues** → Automatically scans all rows against known rules
3. **You review** → Look at flagged records and decide if they're correct or need fixing
4. **Rules improve** → When you spot patterns, the system learns them for next time

---

## Who Is This For?

### 👤 **I'm a Donation Processor**
You upload files and review flagged records daily. Start here:

➜ **Read:** [OPERATOR_MANUAL.md](OPERATOR_MANUAL.md) – Step-by-step instructions for your daily work

### 👨‍💼 **I'm a Manager or Nonprofit Leader**
You need to understand what this system does and why it matters.

➜ **You're reading it!** This README explains the what and why.

➜ **More detail:** [OPERATOR_MANUAL.md](OPERATOR_MANUAL.md) – So you can help your team troubleshoot

### 👨‍💻 **I'm a Developer or Technical Lead**
You need to understand the architecture, configuration, and how to maintain it.

➜ **Start with:** [PRD.md](PRD.md) – Product strategy and V2 validation rules architecture

➜ **Then read:** [DEVELOPER.md](docs/DEVELOPER.md) – Technical integration, versioning, and maintenance

➜ **Deep dive:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) – System design and validation rules specification

---

## Quick Start (60 Seconds)

**1. Start the uploader (one-time setup):**
```bash
cd /Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter
source .venv/bin/activate
python3 -m scripts.uploader.app
```

**2. Open the upload form:**
```
http://localhost:8000
```

**3. Upload a CSV file:**
- Click the form, select your Givebutter export, and submit
- Files appear in `review/flagged/` within seconds

**4. Check the flagged records:**
```bash
ls review/flagged/
```

**That's it.** You can now review and approve/reject records. See [OPERATOR_MANUAL.md](OPERATOR_MANUAL.md) for the full workflow.

---

## Key Folders (Quick Reference)

| Folder | What goes here | Who reads | Who writes |
|--------|---|---|---|
| `intake/new/` | Uploaded CSV files | Processor | Uploader |
| `review/flagged/` | Records that need review | Processor | Auto-processor |
| `review/approved/` | Good flagged records | Manager | Processor |
| `review/rejected/` | Bad flagged records | Archive | Processor |
| `config/rules/` | Rules that define what "bad" means | Developer | Developer (after approval) |

---

## Support & Questions

**For operators:** Read [OPERATOR_MANUAL.md](OPERATOR_MANUAL.md) — it has a full FAQ section

**For technical issues:** See [DEVELOPER.md](docs/DEVELOPER.md) — troubleshooting and architecture

**Questions about:** 
- **How to upload** → OPERATOR_MANUAL, Step 1
- **What to do with flagged files** → OPERATOR_MANUAL, Step 3
- **How rules get added** → OPERATOR_MANUAL, Step 5
- **Why something failed** → OPERATOR_MANUAL, Troubleshooting

---

## Version History

See [CHANGELOG.md](docs/CHANGELOG.md) for what's new in each version.

Current version: **v2.3** (Human-in-the-loop, no auto-apply)

---

**Ready to start?** [Open OPERATOR_MANUAL.md](OPERATOR_MANUAL.md) →
