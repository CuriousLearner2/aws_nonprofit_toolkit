# Documentation Index
## Your Guide to All Givebutter Processor Docs

Welcome! This page helps you find exactly what you need. Pick your role or question below.

---

## 🎯 Quick Navigation by Role

### 👤 **I'm a Donation Processor**
*You upload files and review flagged records daily*

**Start here:**
1. **[README.md](../README.md)** — 4 min read  
   Understand what this system does and why

2. **[OPERATOR_MANUAL.md](../OPERATOR_MANUAL.md)** — 30 min (first time), 5 min (after that)  
   Step-by-step instructions for your daily work

3. **[QUICK_START.md](QUICK_START.md)** — 2 min  
   Print this! One-page reference with folder locations and key commands

**When you have questions:**
- **FAQ in OPERATOR_MANUAL** — Search for your question
- **QUICK_START.md** — Key terms and folder reference
- **Ask your tech lead** — For rule or system questions

---

### 👨‍💼 **I'm a Manager or Nonprofit Leader**
*You oversee the quality control process*

**Start here:**
1. **[README.md](../README.md)** — 4 min read  
   Understand the system, problem it solves, and basic workflow

2. **[OPERATOR_MANUAL.md](../OPERATOR_MANUAL.md#approval-checklist)** — Jump to "Approval Checklist"  
   Know what your team should be checking

3. **[FAQ.md](FAQ.md)** — Browse questions from your team  
   Common issues and how to help solve them

**Key sections:**
- [How it works (3 steps)](README.md#how-it-works-3-steps)
- [The 5-step workflow](OPERATOR_MANUAL.md#the-5-step-workflow)
- [Troubleshooting guide](OPERATOR_MANUAL.md#troubleshooting)

---

### 👨‍💻 **I'm a Developer or Technical Lead**
*You maintain the system, update rules, and manage deployment*

**Start here:**
1. **[README.md](../README.md)** — 4 min read  
   High-level overview

2. **[DEVELOPER.md](DEVELOPER.md)** — 20 min (full read), 5 min (reference)  
   Architecture, rules system, Claude integration, maintenance

3. **[CHANGELOG.md](CHANGELOG.md)** — Track what's changed  
   Version history and planned features

**Key sections:**
- [Architecture diagram](DEVELOPER.md#architecture)
- [Adding new rules](DEVELOPER.md#adding-new-rules)
- [Claude AI integration](DEVELOPER.md#claude-ai-integration)
- [Running the processor](DEVELOPER.md#running-the-processor)
- [Troubleshooting](DEVELOPER.md#troubleshooting)

---

## 📚 Documents at a Glance

### README.md — The Starting Point
- **Length:** 4 minutes
- **Audience:** Everyone (start here!)
- **What it covers:**
  - What the system does
  - Why we need it
  - Who should read what
  - Quick start instructions
- **Best for:** Getting oriented, understanding the big picture

### OPERATOR_MANUAL.md — The User Guide
- **Length:** 30 minutes (first read), 5 minutes (after that)
- **Audience:** Donation processors (primarily), anyone using the system
- **What it covers:**
  - Why this system exists
  - Your role and responsibilities
  - 5-step workflow with diagrams
  - Folder guide with real examples
  - 12 common questions (FAQ)
  - Complete troubleshooting section
- **Best for:** Daily work, understanding workflow, solving problems

### DEVELOPER.md — The Technical Reference
- **Length:** 20 minutes (full read), 5 minutes (looking up specific topics)
- **Audience:** Developers, technical leads, system maintainers
- **What it covers:**
  - System architecture and components
  - Environment setup and .env management
  - Rules system structure and validation
  - Claude AI integration (v2.6)
  - Processor details and error handling
  - Versioning strategy
  - Testing procedures (11-test suite)
  - Maintenance tasks (daily, weekly, monthly)
  - API reference
- **Best for:** Understanding internals, updating rules, debugging, deployment

### QUICK_START.md — The Cheat Sheet
- **Length:** 2 minutes
- **Audience:** Operators (primarily), anyone who needs quick answers
- **What it covers:**
  - Folder locations (what to put where)
  - Key keyboard shortcuts and file operations
  - Important terms defined in one sentence
  - Emergency contacts
- **Best for:** Quick reference, printing and posting at your desk

### FAQ.md — Questions & Answers
- **Length:** Browse as needed
- **Audience:** Everyone (questions are organized by category)
- **What it covers:**
  - Common questions from operators
  - Common technical questions
  - Troubleshooting scenarios
  - How-to answers for specific tasks
- **Best for:** Finding answers to specific questions

### CHANGELOG.md — What's New
- **Length:** Browse as needed
- **Audience:** Technical leads (primarily)
- **What it covers:**
  - Version history
  - What changed in each version
  - Planned features
- **Best for:** Tracking updates, understanding past changes

---

## 🔍 Find Your Answer

### By Question Type

**"How do I...?"** (How-to Questions)
- Upload a file? → [OPERATOR_MANUAL.md, Step 1](OPERATOR_MANUAL.md#step-1️⃣-upload-a-csv-file)
- Review flagged records? → [OPERATOR_MANUAL.md, Step 3](OPERATOR_MANUAL.md#step-3️⃣-review-flagged-records)
- Request a rule update? → [OPERATOR_MANUAL.md, Step 5](OPERATOR_MANUAL.md#step-5️⃣-request-rule-updates)
- Add a new rule? → [DEVELOPER.md, Adding Rules](DEVELOPER.md#adding-new-rules)
- Run the processor? → [DEVELOPER.md, Processor Details](DEVELOPER.md#processor-details)
- Validate a rules file? → [DEVELOPER.md, Rules Validation](DEVELOPER.md#rules-schema-validation)

**"Why...?"** (Understanding)
- does this system exist? → [OPERATOR_MANUAL.md, Introduction](OPERATOR_MANUAL.md#introduction-why-this-system-exists)
- do we need rules? → [DEVELOPER.md, Rules System](DEVELOPER.md#rules-system)
- did this error happen? → [OPERATOR_MANUAL.md, Troubleshooting](OPERATOR_MANUAL.md#troubleshooting) or [DEVELOPER.md, Troubleshooting](DEVELOPER.md#troubleshooting)

**"What is...?"** (Definitions & Explanations)
- A rule? → [OPERATOR_MANUAL.md, Understanding Rules](OPERATOR_MANUAL.md#understanding-rules-plain-english-edition)
- The processor? → [DEVELOPER.md, Processor Details](DEVELOPER.md#processor-details)
- The v2.6 skill? → [DEVELOPER.md, Claude AI Integration](DEVELOPER.md#claude-ai-integration)
- intake/new/? → [OPERATOR_MANUAL.md, Folder Guide](OPERATOR_MANUAL.md#the-folders-youll-use-every-day)

**"Help! Something broke"** (Troubleshooting)
- File didn't upload → [OPERATOR_MANUAL.md, Troubleshooting](OPERATOR_MANUAL.md#problem-uploader-says-file-received-but-nothing-appears-in-review-flagged)
- Processor crashed → [OPERATOR_MANUAL.md, Troubleshooting](OPERATOR_MANUAL.md#problem-processor-crashed-or-shows-an-error)
- Technical issue → [DEVELOPER.md, Troubleshooting](DEVELOPER.md#troubleshooting)

---

## 📖 Read Order Recommendations

### First Time (New Operator)
1. **README.md** (5 min) — Understand what you're doing
2. **QUICK_START.md** (2 min) — Know the key locations
3. **OPERATOR_MANUAL.md, Quick Start section** (5 min) — Do your first upload
4. **OPERATOR_MANUAL.md, The 5-Step Workflow** (10 min) — Understand the workflow
5. **OPERATOR_MANUAL.md, The Folders** (5 min) — Know where things go

**Total: ~30 minutes for your first day**

---

### First Time (New Developer)
1. **README.md** (5 min) — Understand the user perspective
2. **DEVELOPER.md, Architecture** (10 min) — See how it's built
3. **DEVELOPER.md, Rules System** (10 min) — Understand data structure
4. **DEVELOPER.md, Processor Details** (10 min) — How it works
5. **DEVELOPER.md, Testing** (5 min) — Know the 11-test suite

**Total: ~40 minutes to get oriented**

---

### When You Have a Specific Question
1. Check this index (you're here!)
2. Follow the link to the right section
3. If not found, search in FAQ.md
4. If still not found, ask your tech lead

---

## 🎓 Learning Paths

### Become an Operator Expert (1 hour)
1. **README.md** — Understand the system
2. **OPERATOR_MANUAL.md (all sections)** — Learn everything
3. **Bookmark QUICK_START.md** — Your daily reference
4. **Skim FAQ.md** — Know what questions exist

### Become a Technical Lead (2 hours)
1. **README.md** — User perspective
2. **OPERATOR_MANUAL.md** — User workflows
3. **DEVELOPER.md (all sections)** — Technical deep-dive
4. **CHANGELOG.md** — Version history
5. **Claude skill in skills/** — AI integration details

### Troubleshoot a Specific Issue (15 minutes)
1. Check the Troubleshooting section in OPERATOR_MANUAL or DEVELOPER
2. Follow the steps
3. If not solved, check FAQ.md
4. If still stuck, contact your tech lead with:
   - What you were doing
   - What happened
   - Any error messages (if technical)

---

## 📞 Support

**Stuck? Here's how to get help:**

| Question Type | Who to Ask | Where to Look First |
|---|---|---|
| "How do I upload a file?" | Your tech lead | OPERATOR_MANUAL.md, Step 1 |
| "Is this flagged record correct?" | Your manager | OPERATOR_MANUAL.md, Approval Checklist |
| "Why is my file in intake/failed?" | Your tech lead | OPERATOR_MANUAL.md, Troubleshooting |
| "How do I add a new rule?" | Your tech lead | DEVELOPER.md, Adding Rules |
| "The processor won't start" | Your tech lead | DEVELOPER.md, Troubleshooting |
| "Is there a rule for [pattern]?" | Your tech lead | DEVELOPER.md, Rules System |

---

## 🗺️ Document Map

```
README.md
├─ Everyone starts here
├─ Quick overview
└─ Routes to other docs
    │
    ├──→ OPERATOR_MANUAL.md
    │    ├─ For: Daily operators
    │    ├─ Length: 30 min first time
    │    ├─ Key: Step-by-step workflow
    │    └─ Contains: FAQ, troubleshooting
    │
    ├──→ DEVELOPER.md
    │    ├─ For: Technical leads
    │    ├─ Length: 20 min to read
    │    ├─ Key: Architecture, rules, Claude
    │    └─ Contains: Testing, maintenance
    │
    ├──→ QUICK_START.md
    │    ├─ For: Everyone (print it!)
    │    ├─ Length: 2 min to read
    │    ├─ Key: Folders, commands, contacts
    │    └─ Use: Daily reference
    │
    ├──→ FAQ.md
    │    ├─ For: Anyone with questions
    │    ├─ Length: Browse as needed
    │    ├─ Key: Organized by category
    │    └─ Use: Find answers fast
    │
    └──→ CHANGELOG.md
         ├─ For: Technical leads
         ├─ Length: Browse as needed
         ├─ Key: What's new, what changed
         └─ Use: Track versions
```

---

## ✨ Pro Tips

1. **Bookmark QUICK_START.md** — It's your daily reference
2. **Print QUICK_START.md** — Keep it at your desk
3. **When in doubt, check FAQ.md first** — Someone probably asked it
4. **Read the full OPERATOR_MANUAL once** — On your first day, takes 30 min, saves hours later
5. **Developer? Read DEVELOPER.md fully** — All the architecture is there
6. **Share this INDEX.md with your team** — So everyone knows where to look

---

**Last updated:** May 25, 2026  
**Current version:** 1.0
