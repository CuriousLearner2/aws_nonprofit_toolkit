# Givebutter Processor - Product Roadmap

**Current Version:** 3.4  
**Last Updated:** 2026-06-07

---

## ✅ Completed (Current Release)

### Core Features
- ✅ CSV upload with validation
- ✅ Three-tier validation system (PASS/WARNING/FAIL)
- ✅ Review interface with editable records
- ✅ Inline cell editing (click-to-edit pattern)
- ✅ Color-coded tier dropdowns (green/yellow/red)
- ✅ Auto-save architecture (changes persist immediately)
- ✅ Fuzzy email domain matching (70% threshold, aggressive)
- ✅ Editable tier dropdown (operator overrides)
- ✅ Bulk decision buttons (All: Approved/Rejected/Follow-up)
- ✅ Override confirmation dialogs
- ✅ Duplicate detection (exact match: email/phone/address, fuzzy match: names at 70%)

### Validation Rules
- ✅ Email format validation + fuzzy domain typo detection
- ✅ Phone: 10-11 digits (USA format), test pattern detection
- ✅ Phone: >11 digits flagged as WARNING with confirmation dialog
- ✅ Amount: numeric, > 0
- ✅ Name: 2-100 characters
- ✅ Date: YYYY-MM-DD or common formats

### Real-Time Features (Already Implemented)
- ✅ Real-time field validation feedback (inline error messages as user types)
- ✅ Save button enabled/disabled based on field validity
- ✅ Tier auto-updates when issues are fixed via inline edit
- ✅ Issues column updates in real-time after edits
- ✅ Suggestions shown for fixable issues (email typos, phone formatting)
- ✅ Color changes immediately when tier changes (no page refresh)

### Testing
- ✅ 6 critical P0 test cases (upload, inline edit, partial edit, long phone, tier override, bulk actions)
- ✅ Comprehensive E2E test suite with Playwright
- ✅ Agent testing kit (prompts, feature overview, test plans, sample data)
- ✅ Pre-commit hook for E2E test validation
- ✅ Test documentation for agents and developers

---

## 🔄 In Progress / Recently Fixed

### Phone Validation (v3.5)
- ✅ >11 digits: now WARNING (not FAIL) with confirmation dialog
- ✅ Confirmation appears when saving: "Phone has X digits (expected ≤11). Are you sure?"
- ✅ maxlength="15" on phone input field
- ✅ Test case P0_2c for long phone scenarios

### Tier Auto-Update on Partial Edits (v3.5)
- ✅ Fixed: Tier only becomes PASS when ALL issues resolved (not just some)
- ✅ Added test case P0_2b: Edit one of multiple issues → stays WARNING
- ✅ Verification: tier value, CSS class, and color all update together

### Fuzzy Email Matching (v3.5)
- ✅ Fixed: Exact domain name matches now preferred (e.g., `gmail.con` → `gmail.com`, not `hotmail.com`)
- ✅ Bug fix: Removed condition that was ignoring exact matches with unusual TLDs

### Override Confirmation Data Sync (v3.5)
- ✅ Fixed: Decision dropdown now syncs `data-issues` attribute when tier changes
- ✅ Prevents: Stale validation issues in override confirmation dialog
- ✅ Works when: Tier auto-updates after inline edit, or manually changed via dropdown

---

## 🚀 Future Enhancements (v3.6+)

### Operator Experience
- Keyboard shortcuts: Tab = next field, Shift+Tab = prev field, Esc = cancel edit
- Undo/redo for inline edits before submission
- Batch re-run: re-upload same CSV to recalculate tiers with new rules
- Column sorting: click header to sort by tier, decision, issues
- Quick filters: "Show only WARNING", "Show only unapproved", etc.
- Edit history: show what was changed and by whom

### Data Management
- Audit log: timestamp, operator, field edited, old → new value
- Batch export: download original + processed CSVs together
- **Merge duplicate records** (v4.0+): Combine records that appear to be the same donor (flagging already works)
- Data reconciliation report: compare final output to import system

### Advanced Features
- Multi-file upload: process 10 CSVs at once
- Conditional validation rules: different rules per campaign or year
- Custom field mapping: UI to map user's CSV columns to expected fields
- Template library: save validation sets as templates for reuse
- Role-based access: operator vs admin vs auditor permissions

### Performance & Scale
- Pagination: handle 10k+ records per file
- Lazy loading: load records on-demand as operator scrolls
- Bulk recalculation: async background job for tier recalculation
- Search: full-text search across records and notes

---

## 🐛 Known Issues & Limitations

### Current Limitations
- Phone validation: USA format only (no international)
- Email validation: English TLDs only (no .中国, .रु, etc.)
- Amount: no multi-currency support
- Date: no timezone handling
- Bulk operations: >5 records shows summary dialog (not individual)

### Potential Improvements
- Unicode homoglyph detection: currently catches Cyrillic 'а' but could be more comprehensive
- TLD whitelist: hardcoded common TLDs, could use IANA official list
- Phone patterns: reserved ranges are hardcoded, could be data-driven
- Fuzzy matching threshold: 70% is aggressive, could be configurable

---

## 📋 Decision Framework

### What Gets Priority?
1. **Data Quality** (prevents bad data from importing)
2. **Operator Efficiency** (reduces time-to-review per record)
3. **Auditability** (shows what changed, who changed it, when)
4. **Scale** (handles growth from 100 to 10,000+ records/file)

### What We Won't Do (for Now)
- Custom validation logic per nonprofit (could add later)
- ML-based matching (overkill for current use cases)
- Mobile app (web app is sufficient)
- Real-time sync with Givebutter API (batch import is sufficient)

---

## 📅 Release Schedule (Estimated)

| Version | Focus | Timeline |
|---------|-------|----------|
| **3.4** | ✅ Complete (inline editing, tier override, fuzzy matching) | 2026-05-30 to 2026-06-05 |
| **3.5** | Phone validation, tier auto-update fixes, data sync fixes | 2026-06-07 (in progress) |
| **3.6** | Enhanced validation, keyboard shortcuts, operator UX | 2026-06-30 |
| **4.0** | Audit log, search, filtering, role-based access | 2026-08-31 |
| **4.1+** | Advanced features (multi-file, custom rules, historical archive) | TBD |

---

## 🎯 Future Vision (v4.1+): Historical Review Archive

**Purpose**: Maintain a complete audit trail of donation processing decisions over time.

**What Gets Archived**:
- Complete review metadata: date completed, operator name, final counts (approved/rejected/followup)
- Original CSV + all processing outputs (approved, followup, rejected CSVs)
- Decision history: what was decided for each record + operator notes
- Validation snapshot: what validation rules were in place when reviewed
- Performance metrics: time-to-review, operator efficiency trends

**Why It Matters**:
- **Compliance**: "We approved this donor in March" (audit-ready proof)
- **Pattern Recognition**: "Are we rejecting more Q3 vs Q2?" (trend analysis)
- **Operational Context**: "How did we handle similar cases before?" (consistency)
- **Dispute Resolution**: "This was flagged as FAIL but operator approved it—here's why"
- **Capacity Planning**: "Avg 200 records/day, taking 4 hours—do we need more operators?"

**Future Queries**:
- Search: "Show all reviews from June involving emails with typos"
- Export: "Summary report of all decisions for campaign X, by month"
- Compare: "How validation rules changed between batch 1 and batch 2"
- Rollback: "Show what changed if we re-validate with old rules"

**Storage & Scale**:
- Archive stored separately from active processing (fast queries, scalable)
- Periodic cleanup: keep 2 years active, offer export-to-cold-storage for older data
- Index by date range, operator, campaign for fast lookup

---

## 🔗 Related Documents

- **[README.md](README.md)** - Feature list & quick start
- **[OPERATOR_MANUAL.md](OPERATOR_MANUAL.md)** - How to use the app
- **[PROCESSOR_GUIDE.md](PROCESSOR_GUIDE.md)** - Validation rules & technical details
- **[CLAUDE.md](CLAUDE.md)** - Development guidelines & testing requirements
- **[testing/agent/README.md](testing/agent/README.md)** - Agent testing kit

---

## 💬 Feedback

Issues, feature requests, or suggestions? Document them here and link to the relevant test case or incident analysis.

**Last Updated:** 2026-06-07  
**Maintainer:** Development Team
