# Product Requirements Document (PRD)
## Givebutter Donation Processor v2.0 (Planned Future Release)

**Version:** 2.0  
**Date:** May 26, 2026  
**Status:** Planned (Future Release)  
**Current Implementation:** v3.0 (Web-Based Operator Review System)

---

## ⚠️ Important Note

**This document describes v2.0 planned features that are NOT YET IMPLEMENTED.**

The current released version is **v3.0** (June 1, 2026), which focuses on the **downstream correction system** (web-based operator review workflow) without upstream prevention.

**What's in v3.0 (Current)**:
- ✅ Web-based operator review UI
- ✅ Per-record decision workflow (approved/followup/rejected)
- ✅ 7 validation types (email, phone, amount, name, address, headers, tier)
- ✅ 330+ comprehensive tests
- ✅ Decision persistence and multi-session support

**What's in v2.0 (Planned Future)**:
- ⏳ Upstream pre-form validation wrapper (this PRD)
- ⏳ Auto-watching of donation entry
- ⏳ Real-time donor feedback
- ⏳ Integrated learning loop

See [CHANGELOG.md](docs/CHANGELOG.md) and [README.md](README.md) for current v3.0 details. This document remains valuable for future upstream prevention implementation.

---

---

## Executive Summary

The Givebutter Donation Processor v2.0 introduces a **dual-validation architecture**: preventing errors upstream (before data enters Givebutter) while maintaining downstream correction (catching what escapes). This shift from purely **corrective** to **preventive + corrective** reduces operator workload, improves data quality at entry, and creates a learning system that gets smarter over time.

**Key Innovation:** Pre-form validation wrapper on your website gates access to Givebutter widget, catching ~70% of validation errors before they propagate to the database.

---

## Problem Statement (V1 Limitations)

### Current System (v1.x)
```
Data Entry → Givebutter Database → Processor Catches Errors
             (no validation)      (post-hoc correction)
```

**Issues:**
- ❌ Errors already in Givebutter database (propagated before detection)
- ❌ Operator must review every error (high workload)
- ❌ Learning is slow (rules improve only after errors occur)
- ❌ No feedback to donor (form accepted bad data silently)

**Givebutter Constraint:** Cannot inject custom JS into hosted widget (PCI compliance). Form runs in iframe on Givebutter's domain.

---

## Proposed Solution: V2.0 Architecture

### Dual-Validation System
```
PREVENTION (Your Website)           CORRECTION (This System)
┌─────────────────────────────┐   ┌──────────────────────────┐
│ Pre-Form Validation Wrapper │   │ Downstream Processor     │
│ (Your domain, your JS)      │   │ (Post-Givebutter)       │
│                             │   │                          │
│ ✅ Email validation         │   │ Catches what escaped:   │
│ ✅ Domain whitelist         │───→ ⚠️ Unknown formats      │
│ ✅ Required fields          │   │ ⚠️ Edge cases           │
│ ✅ Format validation        │   │ ⚠️ Corrupted data       │
│ ✅ Real-time feedback       │   │                          │
│                             │   │ Learns patterns:        │
│ "Did you mean gmail.com?"   │   │ • Operator approves fix │
│ [Suggest] or [Edit]         │   │ • Rule added for next   │
│                             │   │                          │
│ If validation passes → Open │   │ System improves ✨      │
│ Givebutter widget           │   │                          │
│                             │   │                          │
│ PREVENTS ~70% of errors     │   │ CORRECTS ~30% escapes   │
└─────────────────────────────┘   └──────────────────────────┘
```

**Benefit:** Cleaner data flows through entire pipeline.

---

## Validation Rules Architecture (High-Level)

### Two-File System

#### File 1: `validation_rules.json` (UPSTREAM)
**Purpose:** Prevent errors before Givebutter entry  
**Audience:** Pre-form wrapper on your website  
**Example:**

```json
{
  "email_validation": {
    "format": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
    "domain_whitelist": ["gmail.com", "yahoo.com", "outlook.com"],
    "common_typos": {
      "gmai.com": "gmail.com",
      "yaho.com": "yahoo.com"
    },
    "action_on_unknown_domain": "warn_with_suggestion"
  },
  "required_fields": ["donor_name", "email", "donation_amount"],
  "formats": {
    "phone": "^\\d{3}-?\\d{3}-?\\d{4}$",
    "zip": "^\\d{5}(-\\d{4})?$"
  }
}
```

**Controls:**
- Real-time validation (as user types)
- Helpful suggestions ("Did you mean gmail.com?")
- Blocking errors (stop form submission)
- Friendly, actionable error messages

---

#### File 2: `rules.json` (DOWNSTREAM)
**Purpose:** Correct errors that escaped upstream  
**Audience:** Processor (this system)  
**Example:**

```json
{
  "email_typos": [
    {
      "from": "gmai.com",
      "to": "gmail.com",
      "confidence": 0.99,
      "validation_rule_id": "email.typos.gmai",
      "note": "Escaped upstream, caught downstream"
    }
  ]
}
```

**Enhancements over v1:**
- Linked to validation_rule_id (tracks origin)
- Tracks confidence and source
- Learning metadata for improvement

---

### How They Work Together

#### Scenario 1: User Types Typo
```
1. User on YOUR SITE types: john@gmai.com
2. validation_rules.json checks:
   - Format valid? ✓
   - Domain recognized? ✗ (not in whitelist)
   - Check typo list: Found "gmai.com"!
3. Real-time tooltip appears:
   "Did you mean gmail.com?"
4. User clicks [Yes] → Corrected to gmail.com
5. Form submits → Givebutter receives: john@gmail.com ✅

RESULT: Error prevented, user informed, data clean
```

#### Scenario 2: User Somehow Bypasses Validation
```
1. User posts directly to Givebutter (bypasses wrapper)
2. Email "john@gmai.com" enters database
3. Processor loads rules.json, finds typo rule
4. Flags for operator review
5. Operator approves: "Yes, gmai.com is always gmail.com"
6. Error recorded with metadata (validation_rule_id)

RESULT: Error caught, operator approves, system learns
```

#### Scenario 3: New Pattern Emerges
```
1. Operator approves 43 instances of same typo
2. System detects pattern (threshold: 3+ instances, 98%+ confidence)
3. Claude AI analyzes and proposes rule
4. Technical lead reviews and approves
5. validation_rules.json UPDATED → Next form uses new rule
6. rules.json UPDATED → Downstream catching improves

RESULT: System learns, prevents same error in future batches
```

---

## User Journey

### For Your Donors
```
┌─────────────────────────────────────┐
│ Visit your nonprofit's website       │
├─────────────────────────────────────┤
│ See donation form (your form)        │
├─────────────────────────────────────┤
│ Type email: john@gmai.com            │
├─────────────────────────────────────┤
│ Real-time feedback appears:          │
│ "Did you mean gmail.com?"            │
├─────────────────────────────────────┤
│ Click [Yes] or manually fix          │
├─────────────────────────────────────┤
│ Form validates ✓ Open Givebutter     │
├─────────────────────────────────────┤
│ Complete donation in Givebutter      │
│ widget (clean data)                  │
└─────────────────────────────────────┘
```

**Benefit to donors:** Better UX (errors caught in real-time)

### For Your Operators
```
V1 Workflow: Upload CSV → Review many errors → Manual fixes
             (tedious, reactive)

V2 Workflow: Upload CSV → Review few errors → Learn patterns
             (efficient, proactive)
```

**Benefit to operators:** Less review work, system learns automatically

### For Your Organization
```
Cleaner data pipeline:
  Givebutter (cleaner) → CRM (cleaner) → Accounting (cleaner)
  
Better donor experience:
  Errors caught before submission (friendly feedback)
  
Faster learning:
  Patterns → Rules → Prevention (cycle shortens)
```

---

## Technical Architecture Overview

For detailed technical specification, see [ARCHITECTURE.md](docs/ARCHITECTURE.md).

### File Structure
```
config/
├── validation_rules.json      ← UPSTREAM validation (pre-form)
├── rules/
│   └── rules_v2.4.json        ← DOWNSTREAM correction (post-Givebutter)
└── schemas/
    └── validation_schema_v2.4.json  ← Validates validation_rules.json
```

### Integration Points
1. **Pre-form wrapper** → Loads validation_rules.json
2. **Website form** → Calls validate() function on submit
3. **Givebutter widget** → Opens only if validation passes
4. **Processor** → Loads rules.json (unchanged)
5. **Learning loop** → Both files update when patterns emerge

---

## Success Metrics: V1 vs V2

| Metric | V1 | V2 Goal | Benefit |
|--------|----|---------|---------| 
| **Errors prevented** | 0% | ~70% | Cleaner data entry |
| **Operator review load** | High | Low (30%) | Faster processing |
| **Donor experience** | Silent failures | Real-time feedback | Better UX |
| **Learning cycle** | Slow (days) | Fast (hours) | Quicker improvement |
| **False positives** | Medium | Low | Less manual review |
| **Data quality at entry** | Poor | Good | Downstream cleaner |

---

## High-Level Timeline

### Phase 1: Design & Approval (Current)
- [x] Document V2 architecture
- [ ] **Get stakeholder buy-in on key questions**
- [ ] Finalize validation_rules.json specification

### Phase 2: Implementation (Post-Approval)
- [ ] Create validation_rules.json template
- [ ] Build pre-form wrapper (HTML/JS example)
- [ ] Update processor to load validation_rules.json
- [ ] Testing (unit + integration)

### Phase 3: Rollout
- [ ] Deploy pre-form wrapper to website
- [ ] Train operators on new system
- [ ] Monitor error prevention rate
- [ ] Iterate based on real-world feedback

---

## Critical Questions for Discussion

Before implementation, we need your input on these architectural decisions:

### ❓ Question 1: Pre-Form Integration
**Can your site team integrate a pre-form validation wrapper?**

- [ ] Yes, we have developers who can integrate custom JS
- [ ] Maybe, it depends on how complex it is
- [ ] No, our donation page is fully Givebutter-hosted
- [ ] Other: _______________

**Why it matters:** If your form is entirely Givebutter iframe, we need a different approach (e.g., Givebutter API pre-validation).

---

### ❓ Question 2: validation_rules.json Editability
**Who should be able to edit validation_rules.json?**

- [ ] **Operators (via UI)** - Point-and-click rule editor (more work, more user-friendly)
- [ ] **Developers only (JSON editing)** - Manual JSON files (less work, less user-friendly)
- [ ] **Both** - Simple rules via UI, complex rules via JSON (hybrid)
- [ ] Other: _______________

**Why it matters:** Affects how quickly you can respond to new patterns (hours vs days).

---

### ❓ Question 3: Real-Time Feedback Style
**What user experience do you want for validation feedback?**

- [ ] **Blocking errors** - Stop form submission if validation fails (strictest)
- [ ] **Helpful tooltips only** - Show suggestions but allow submission (gentlest)
- [ ] **Warnings → Confirm** - Show warning, require user confirmation to continue (balanced)
- [ ] **Multiple approaches** - Different rules have different feedback styles

**Why it matters:** Affects user experience and strictness of data validation.

---

### ❓ Question 4: Validation Rules Scope
**What validation should validation_rules.json cover?**

- [ ] **Email only** - Focus on domain typos and format validation
- [ ] **Email + required fields** - Also ensure name, amount, email present
- [ ] **Email + formats** - Email, phone format, zip code format, etc.
- [ ] **Full business rules** - All of above + min/max amounts, relationships, etc.
- [ ] **All of the above** - Comprehensive validation

**Why it matters:** Affects prevention rate (70% estimate is for email; broader scope = higher prevention).

---

## Next Steps

1. **Review this PRD** (you're reading it now!)
2. **Answer the 4 critical questions above**
3. **Discuss any architectural concerns**
4. **Finalize scope & approach**
5. **Approve implementation plan**
6. **Build validation_rules.json template** (Phase 2)

---

## Related Documentation

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Detailed technical specification
- **[DEVELOPER.md](docs/DEVELOPER.md)** - Integration guide for developers
- **[OPERATOR_MANUAL.md](../OPERATOR_MANUAL.md)** - How operators use the system
- **[SETUP_GUIDE.md](../SETUP_GUIDE.md)** - How to set up the system

---

## Questions? Issues?

This is an **open design**. We're documenting the approach and gathering feedback before implementation.

**Your input on the 4 critical questions above is essential to move forward.** ⬆️

---

**Document Version:** PRD v2.0  
**Last Updated:** May 26, 2026  
**Status:** Open for Review & Discussion
