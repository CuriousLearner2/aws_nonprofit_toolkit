# Normalization Review Screen — Design & Implementation

**Status:** ✅ Design finalized | ⏳ Implementation pending

---

## 📄 Authoritative Documents

### 1. **normalization_review-spec.md** ⭐ PRIMARY
The definitive specification for implementation.

Contents:
- Product intent and safety constraints
- Visual design direction
- Exact copy for all UI elements
- Component specifications
- Data model expectations
- Acceptance criteria
- Stitch artifact note

**Use this for:** Implementation guidance, QA verification, design review

---

### 2. **NORMALIZATION_REVIEW_IMPLEMENTATION.md**
Supplementary implementation requirements (legacy reference).

**Use this for:** Implementation checklist, cross-reference details

---

## 📦 Stitch Artifacts (Visual Reference Only)

Located in:
- `iteration-001/` — Baseline capture
- `iteration-002/` — Safety improvements (8 changes)
- `iteration-003/` — Final polish variant

**Important:** These folders contain Stitch exports and screenshots for visual direction only.

**Do NOT:**
- Manually patch `design.html`
- Treat Stitch API success reports as final
- Implement from Stitch artifacts directly

**Do:**
- Use these for color, typography, spacing reference
- Refer to `normalization_review-spec.md` for all behavioral requirements

See `iteration-003/STITCH_REFERENCE_ONLY.md` for details.

---

## 🛠️ Implementation Roadmap

### Phase 1: App Development
1. Create route: `/imports/<import_id>/normalizations`
2. Implement components per spec
3. Build data model integration
4. Wire up audit logging

### Phase 2: QA & Verification
1. Run Playwright tests against app (not Stitch)
2. Verify all acceptance criteria
3. Test audit events
4. Performance review

### Phase 3: Deployment
1. Code review
2. Stakeholder approval
3. Merge to main
4. Deploy to staging/production

---

## 📋 Quick Checklist

Before implementing, ensure:
- [ ] Read `normalization_review-spec.md` completely
- [ ] Understand v1 safety constraints
- [ ] Review section 15 (Acceptance Criteria)
- [ ] Know the exact copy for all UI elements
- [ ] Plan Playwright test strategy

---

## 🔗 Related Work

- **Import Dashboard:** `/path/to/import-dashboard/` — Similar DonorTrust pattern
- **Stitch Design Tool:** Session history archived (API reliability issues noted)
- **Givebutter Integration:** No direct CRM writeback (v1 constraint)

---

## 📞 Questions?

Refer to:
1. `normalization_review-spec.md` § [section number]
2. `NORMALIZATION_REVIEW_IMPLEMENTATION.md` for detailed checklist
3. `iteration-003/STITCH_REFERENCE_ONLY.md` for Stitch artifact notes

---

**Last Updated:** 2026-06-11  
**Status:** ✅ Specification Complete | Ready for Implementation
