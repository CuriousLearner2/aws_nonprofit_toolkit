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

2. **[PRD.md](../PRD.md)** — 10 min read  
   Understand V2's dual-validation strategy (prevent errors upstream, catch downstream)

3. **[OPERATOR_MANUAL.md](../OPERATOR_MANUAL.md#approval-checklist)** — Jump to "Approval Checklist"  
   Know what your team should be checking

4. **[FAQ.md](FAQ.md)** — Browse questions from your team  
   Common issues and how to help solve them

**Key sections:**
- [How it works (3 steps)](../README.md#how-it-works-3-steps)
- [V2 Architecture](../PRD.md#proposed-solution-v20-architecture)
- [The 5-step workflow](../OPERATOR_MANUAL.md#the-5-step-workflow)
- [Troubleshooting guide](../OPERATOR_MANUAL.md#troubleshooting)

---

### 👨‍💻 **I'm a Developer or Technical Lead**
*You maintain the system, update rules, and manage deployment*

**Start here:**
1. **[README.md](../README.md)** — 4 min read  
   High-level overview

2. **[PRD.md](../PRD.md)** — 10 min read  
   Product strategy: V2 dual-validation architecture (upstream prevention + downstream correction)

3. **[ARCHITECTURE.md](ARCHITECTURE.md)** — 30 min read  
   Technical deep-dive with validation rules architecture specification

4. **[DEVELOPER.md](DEVELOPER.md)** — 20 min (full read), 5 min (reference)  
   Architecture, rules system, validation integration, Claude integration, maintenance

5. **[CHANGELOG.md](CHANGELOG.md)** — Track what's changed  
   Version history and planned features

**Key sections:**
- [PRD: Dual-validation architecture](../PRD.md#proposed-solution-v20-architecture)
- [ARCHITECTURE: Validation rules specification](ARCHITECTURE.md#validation-rules-architecture-v2)
- [DEVELOPER: Validation rules integration](DEVELOPER.md#validation-rules-integration-v2)
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
  - What the system does (V2: dual-validation)
  - Why we need it
  - Who should read what
  - Quick start instructions
  - Links to PRD for deeper context
- **Best for:** Getting oriented, understanding the big picture

### PRD.md — The Product Strategy (NEW in V2)
- **Length:** 10 minutes
- **Audience:** Everyone (especially managers and technical leads)
- **What it covers:**
  - V2 vision: dual-validation architecture
  - Problem statement (V1 limitations)
  - Proposed solution (upstream prevention + downstream correction)
  - Validation rules architecture (two-file system)
  - User journeys (donors, operators, organization)
  - Success metrics
  - Critical questions for discussion
- **Best for:** Understanding why V2 exists, product strategy, making design decisions

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

### ARCHITECTURE.md — The Technical Design (UPDATED for V2)
- **Length:** 30 minutes (full read)
- **Audience:** Developers, technical leads, system designers
- **What it covers:**
  - System architecture and components
  - Validation rules architecture specification (V2)
  - validation_rules.json (upstream prevention)
  - rules.json (downstream correction)
  - How the two systems work together
  - Three detailed scenarios (prevent, correct, learn)
  - File structure and integration points
- **Best for:** Deep technical understanding, implementing validation systems, designing integration

### DEVELOPER.md — The Technical Reference (UPDATED for V2)
- **Length:** 20 minutes (full read), 5 minutes (looking up specific topics)
- **Audience:** Developers, technical leads, system maintainers
- **What it covers:**
  - System architecture and components
  - Environment setup and .env management
  - Rules system structure and validation
  - Validation rules integration (V2)
  - Claude AI integration (v2.6)
  - Processor details and error handling
  - Versioning strategy
  - Testing procedures (11-test suite)
  - Maintenance tasks (daily, weekly, monthly)
  - API reference
- **Best for:** Understanding internals, updating rules, integrating validation systems, debugging, deployment

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
2. **PRD.md** (10 min) — Understand V2 product strategy
3. **ARCHITECTURE.md, Validation Rules** (15 min) — Technical specification
4. **DEVELOPER.md, Validation Integration** (10 min) — How to implement
5. **DEVELOPER.md, Rules System** (10 min) — Understand data structure
6. **DEVELOPER.md, Processor Details** (10 min) — How it works
7. **DEVELOPER.md, Testing** (5 min) — Know the 11-test suite

**Total: ~65 minutes to get oriented (includes V2 validation systems)**

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

### Become a Technical Lead (3 hours)
1. **README.md** — User perspective
2. **PRD.md** — Product strategy and V2 decisions
3. **OPERATOR_MANUAL.md** — User workflows
4. **ARCHITECTURE.md** — Technical design (including validation rules)
5. **DEVELOPER.md (all sections)** — Technical deep-dive
6. **CHANGELOG.md** — Version history
7. **Claude skill in skills/** — AI integration details

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
├─ Quick overview (now mentions V2!)
└─ Routes to other docs
    │
    ├──→ PRD.md (NEW)
    │    ├─ For: Everyone (especially leads)
    │    ├─ Length: 10 min to read
    │    ├─ Key: V2 strategy, dual validation
    │    └─ Use: Understand product direction
    │
    ├──→ OPERATOR_MANUAL.md
    │    ├─ For: Daily operators
    │    ├─ Length: 30 min first time
    │    ├─ Key: Step-by-step workflow
    │    └─ Contains: FAQ, troubleshooting
    │
    ├──→ ARCHITECTURE.md (UPDATED)
    │    ├─ For: Technical leads
    │    ├─ Length: 30 min to read
    │    ├─ Key: Validation rules architecture
    │    └─ Contains: Specifications, scenarios
    │
    ├──→ DEVELOPER.md (UPDATED)
    │    ├─ For: Technical leads
    │    ├─ Length: 20 min to read
    │    ├─ Key: Rules, validation integration, Claude
    │    └─ Contains: Testing, maintenance
    │
    ├──→ QUICK_START.md (UPDATED)
    │    ├─ For: Everyone (print it!)
    │    ├─ Length: 2 min to read
    │    ├─ Key: Folders, commands, validation rules
    │    └─ Use: Daily reference
    │
    ├──→ FAQ.md
    │    ├─ For: Anyone with questions
    │    ├─ Length: Browse as needed
    │    ├─ Key: Organized by category
    │    └─ Use: Find answers fast
    │
    └──→ CHANGELOG.md (UPDATED)
         ├─ For: Technical leads
         ├─ Length: Browse as needed
         ├─ Key: V2 dual-validation, what's new
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

**Last updated:** May 26, 2026  
**Current version:** 2.0 (Dual-Validation Architecture)
