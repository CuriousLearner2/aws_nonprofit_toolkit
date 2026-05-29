# Changelog
## Givebutter Donation Processor Version History

**Current Version:** 2.0 | **Last Updated:** May 26, 2026

All notable changes to this project will be documented in this file.

---

## [2.0] — Dual-Validation Architecture (May 26, 2026)

**Status:** Released | **Type:** Major Release

### What's New (V2 Overview)

V2.0 introduces a **dual-validation architecture** that combines upstream prevention with downstream correction:

- **Upstream Prevention** — Pre-form validation wrapper on nonprofit's website catches ~70% of validation errors before they enter Givebutter
- **Downstream Correction** — Processor catches remaining ~30% of errors that escape upstream
- **Learning Loop** — System automatically learns from operator decisions and improves rules

### Added

#### Documentation
- **[PRD.md](../PRD.md)** (NEW) — Product Requirements Document
  - V2 vision and strategy
  - Dual-validation architecture explanation
  - Validation rules architecture (two-file system)
  - User journeys (donors, operators, organization)
  - Success metrics and critical questions for discussion
  - Version: 2.0

#### Technical Specifications
- **Validation Rules Architecture (ARCHITECTURE.md)**
  - New section: "Validation Rules Architecture (V2)"
  - `validation_rules.json` specification (upstream, pre-form)
  - `rules.json` enhanced metadata (downstream, post-Givebutter)
  - Three detailed scenarios (prevent, correct, learn)
  - File structure and integration points
  
- **Validation Rules Integration (DEVELOPER.md)**
  - New section: "Validation Rules Integration (V2)"
  - How processor loads and uses validation_rules.json
  - Tracking rule sources via validation_rule_id
  - Logging bypass events (errors that escaped upstream)
  - Updating both files when patterns emerge
  - Python code examples and best practices
  - Unit testing for validation rules

#### Documentation Updates
- **INDEX.md** — Added PRD to navigation, updated developer learning path
- **QUICK_START.md** — Added "Understanding V2" section explaining dual validation
- **README.md** — Updated with V2 version badge and dual-validation description
- **SETUP_GUIDE.md** — Added links to PRD for setup context (v1.0 content still valid)
- **OPERATOR_MANUAL.md** — Version remains 1.0 (workflow unchanged)

### Changed

#### Architectural Decisions
- **Problem:** V1 was purely corrective (catching errors AFTER they entered Givebutter)
- **Solution:** V2 adds prevention layer (catching errors BEFORE Givebutter)
- **Approach:** Pre-form validation wrapper on nonprofit's own website domain (works around Givebutter iframe constraint)
- **Benefit:** Prevents ~70% of errors upstream, reduces operator workload, improves data quality at entry

#### System Design
- `validation_rules.json` (NEW upstream file)
  - Controls pre-form validation on nonprofit's website
  - Defines validation rules, typo corrections, required fields
  - Real-time feedback strategy (warnings, suggestions, blocking)
  
- `rules.json` (ENHANCED downstream file)
  - Now includes `validation_rule_id` linking back to upstream rules
  - Tracks which errors escaped upstream vs. were caught downstream
  - Enables learning loop: patterns → rules → prevention

#### Documentation Structure
- Core docs remain at root level (README, OPERATOR_MANUAL, SETUP_GUIDE)
- Reference docs remain in docs/ folder (ARCHITECTURE, DEVELOPER, FAQ, etc.)
- Added PRD at root level for product strategy

### Integration Points

The V2 system defines three integration points:

1. **Pre-Form Wrapper** (on nonprofit's website)
   - Loads `validation_rules.json`
   - Validates form input in real-time
   - Shows user-friendly suggestions
   - Gates access to Givebutter widget

2. **Processor** (this system, downstream)
   - Loads both `validation_rules.json` and `rules.json`
   - Flags records that escaped upstream validation
   - Logs bypass events for analysis

3. **Learning Loop** (operator + AI)
   - Operator approves patterns in flagged records
   - System detects patterns (3+ instances, 98%+ confidence)
   - Claude AI proposes rule updates
   - Technical lead reviews and approves
   - Both files updated, system improves for next batch

### Critical Questions (Open for Discussion)

Before implementation, stakeholders should answer:

1. **Pre-Form Integration Feasibility**
   - Can your site team integrate a pre-form validation wrapper?
   - Is donation page Givebutter-hosted iframe or custom?
   
2. **Validation Rules Editability**
   - Who should edit `validation_rules.json`? (Operators via UI or developers only?)
   
3. **Real-Time Feedback Style**
   - Blocking errors (stop submission) or helpful tooltips (suggestions only)?
   
4. **Validation Scope**
   - Email-only, full formats, business rules, or all of the above?

See [PRD.md](../PRD.md) for full context.

### Success Metrics

| Metric | V1 | V2 Goal |
|--------|----|----|
| Errors prevented | 0% | ~70% |
| Operator review load | High | Low (30%) |
| Donor experience | Silent failures | Real-time feedback |
| Learning cycle | Slow (days) | Fast (hours) |
| Data quality at entry | Poor | Good |

### Files Modified

- `README.md` — Added V2 version badge, dual-validation description
- `docs/INDEX.md` — Added PRD to navigation, updated learning paths
- `docs/QUICK_START.md` — Added V2 section, links to PRD
- `docs/ARCHITECTURE.md` — Added validation rules architecture section (15+ pages)
- `docs/DEVELOPER.md` — Added validation rules integration section
- Created `docs/CHANGELOG.md` (this file)
- Created `PRD.md` (new product strategy document)

### Next Steps (Phase 2 Implementation)

After stakeholder approval of the 4 critical questions:

- [ ] Finalize `validation_rules.json` specification
- [ ] Build pre-form validation wrapper (HTML/JS example)
- [ ] Update processor to load and use `validation_rules.json`
- [ ] Implement rule learning feedback loop
- [ ] Testing (unit + integration + real-world)
- [ ] Deploy pre-form wrapper to nonprofit website
- [ ] Train operators on V2 workflow
- [ ] Monitor prevention rate and operator feedback

---

## [1.3] — Final V1 Release (May 24, 2026)

**Status:** Stable | **Type:** Maintenance Release

### Added
- Comprehensive OPERATOR_MANUAL.md with 12 FAQ sections
- SETUP_GUIDE.md with 10-step first-time setup
- Visual workflow diagrams (OPERATOR_MANUAL)
- Emergency troubleshooting guide
- Approval checklist for operators

### Changed
- Documentation reorganized (root-level core docs + docs/ reference)
- All relative paths updated for docs/ folder location
- QUICK_START.md expanded with V2 forward reference

### Fixed
- Relative path issues in cross-document links
- FAQ search-ability improvements

---

## [1.2] — Rules Enhancement (May 20, 2026)

**Status:** Stable | **Type:** Feature Release

### Added
- env_manager.py auto-discovery of rules files
- rules.json versioning system
- Rules validation against schema
- Confidence scoring for pattern detection

### Changed
- rules.json structure includes metadata
- Rules are now auto-discovered from config/rules/ folder
- Version management simplified

---

## [1.1] — Initial Release (May 15, 2026)

**Status:** Stable | **Type:** Feature Release

### Added
- Flask web uploader (localhost:8000)
- CSV donation file processing
- Email validation and typo detection
- Flagging system for problematic records
- intake/new/, review/flagged/, review/approved/, review/rejected/ workflow
- Basic rules.json system
- operator decision learning

### Features
- Upload CSV files via web form
- Automatic data quality checking
- Operator review workflow
- Rule-based error detection
- Human-in-the-loop approval system

---

## [1.0] — Proof of Concept (May 1, 2026)

**Status:** Archived | **Type:** Initial Release

### Features
- Basic donation CSV processing
- Email validation
- Simple flagging (no learning)
- Command-line operation

### Notes
- Pre-web interface version
- Limited rule set
- Manual folder management

---

## Version Numbering Scheme

We use [Semantic Versioning](https://semver.org/):

- **MAJOR** (2.0, 3.0, ...) — Breaking changes, major architecture shifts
- **MINOR** (2.1, 2.2, ...) — New features, backwards compatible
- **PATCH** (2.0.1, 2.1.1, ...) — Bug fixes, maintenance

**Current:** 2.0 (Dual-validation architecture introduces major architectural change; previous 1.x versions remain stable for reference)

---

## Support

- **Questions about changes?** → See [PRD.md](../PRD.md) for V2 context
- **Technical details?** → See [ARCHITECTURE.md](ARCHITECTURE.md) and [DEVELOPER.md](DEVELOPER.md)
- **User guide?** → See [OPERATOR_MANUAL.md](../OPERATOR_MANUAL.md)

---

**Last Updated:** May 26, 2026  
**Maintained By:** Nonprofit Toolkit Team  
**License:** [See LICENSE file]
