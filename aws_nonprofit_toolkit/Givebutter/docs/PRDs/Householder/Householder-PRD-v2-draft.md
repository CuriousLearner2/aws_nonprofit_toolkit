# Householder v2 PRD — Cross-Import Identity, Duplicate, and Household Linking

**Last updated:** 2026-06-08  
**Owner:** Gautam Biswas  
**Status:** v2 starter PRD / enhancement draft  
**Depends on:** Householder v1 PRD v2.5 and successful v1 implementation

---

## 1. Mission

Householder v2 extends Householder from an import-batch review tool into a safer long-term donor identity and householding system.

Where v1 asks:

> “Within this uploaded CSV, who looks like a duplicate and who appears to belong in the same household?”

v2 asks:

> “Across all prior imports and approved reviewer decisions, does this new contact match an existing person or household?”

The goal is to help nonprofits build a durable, human-reviewed donor/contact intelligence layer across multiple Givebutter exports while preserving all v1 safety guarantees.

---

## 2. Core Principle

v2 may use historical data as evidence, but it still must not silently merge people, overwrite contact fields, or assign households without review.

Every cross-import link must be represented as a suggestion first, then approved, rejected, or deferred by a human reviewer.

---

## 3. v1 vs. v2 Scope

### v1 Scope

Householder v1 is current-import only.

It compares contacts inside one uploaded CSV/import batch. It does not automatically compare against historical imports, existing households, prior duplicate decisions, or a global registry.

### v2 Scope

Householder v2 adds cross-import intelligence:

- Compare new contacts against contacts from prior imports.
- Suggest that a new contact belongs to an existing household.
- Suggest that a new contact is the same person as a previously imported contact.
- Maintain a global household registry.
- Maintain a master person/contact registry.
- Use prior reviewer decisions as evidence for future suggestions.
- Support review queues specifically for cross-import matches.

---

## 4. Non-Negotiables

v2 inherits all v1 guardrails:

1. Preserve raw imported data forever.
2. Never mutate `raw_import_rows`.
3. Never directly mutate baseline contact fields.
4. Never auto-merge contacts.
5. Never auto-create or auto-link households without explicit approval.
6. Never write back to Givebutter in v2 unless a separate API-writeback PRD is approved.
7. All cross-import matches are suggestions first.
8. Human approval is required before creating persistent master-person or household links.
9. All actions must be audit logged with reviewer, timestamp, decision, IP address, user agent, and optional notes.

---

## 5. New v2 Concepts

### 5.1 Master Person

A **master person** represents a real-world individual across multiple imports.

Examples:

- Jane Smith from Import 1
- Jane A. Smith from Import 3
- jane@example.com from Import 7

After review, these may all link to one `master_person_id`.

Important: v2 does not delete or merge the original contacts. It creates a reviewed link from each import-specific contact to a master person.

### 5.2 Global Household

A **global household** represents a durable household across imports.

Example:

- `123 Main Street | 94301`
- Jane Smith and John Smith from one import
- Mary Smith added in a later import
- A future donor at the same address suggested as a possible household member

v2 may suggest linking a new contact to an existing household, but only after human approval should the contact receive a global household link.

### 5.3 Cross-Import Suggestions

v2 introduces suggestions that compare current-import contacts to historical data:

- Current contact may match existing master person.
- Current contact may belong to existing global household.
- Current household suggestion may duplicate an existing global household.
- Current duplicate pair may match a previously reviewed duplicate decision.

---

## 6. User Stories

### 6.1 Link New Contact to Existing Household

As a nonprofit operator, when I upload a new Givebutter CSV, I want the system to tell me:

> “John Smith from this import appears to belong to the existing Smith household at 123 Main Street.”

So that I can approve the household link instead of manually rediscovering the household each time.

### 6.2 Detect Historical Duplicate

As a nonprofit operator, I want the system to tell me:

> “Jane A. Smith in this import appears to be the same person as Jane Smith from a prior import.”

So that duplicate donor records can be reviewed consistently over time.

### 6.3 Use Prior Decisions as Evidence

As a nonprofit operator, if I previously marked two contacts as “different people,” I want the system to avoid repeatedly suggesting the same incorrect match, or at least lower its confidence and show the prior decision.

### 6.4 Preserve Auditability

As an admin, I want to know when and why a contact was linked to a master person or household, who approved it, and what evidence was shown.

---

## 7. v2 Data Model Additions

The exact schema should adapt to the repository’s implementation pattern, but the logical entities are:

### `master_people`

Durable reviewed person records.

Suggested fields:

- id
- master_person_id
- primary_contact_id
- display_name
- primary_email
- primary_phone
- created_by
- created_at
- updated_at

### `contact_identity_links`

Links import-specific contacts to master people.

Suggested fields:

- id
- contact_id
- master_person_id
- link_status: pending / approved / rejected / deferred
- confidence_score
- match_reasons
- suggested_by
- suggested_at
- reviewed_by
- reviewed_at
- reviewer_notes
- ip_address
- user_agent

### `global_households`

Durable reviewed households across imports.

Suggested fields:

- id
- global_household_id
- canonical_form
- primary_contact_id
- primary_master_person_id
- member_count
- created_by
- created_at
- updated_at

### `household_identity_links`

Links import-specific or master-person records to global households.

Suggested fields:

- id
- contact_id
- master_person_id nullable
- global_household_id
- link_status: pending / approved / rejected / deferred
- confidence_score
- match_reasons
- suggested_by
- suggested_at
- reviewed_by
- reviewed_at
- reviewer_notes
- ip_address
- user_agent

### `cross_import_match_suggestions`

Optional unified table for all cross-import suggestions.

Suggested fields:

- id
- import_id
- current_contact_id
- historical_contact_id nullable
- master_person_id nullable
- global_household_id nullable
- suggestion_type: person_match / household_match / household_merge / prior_decision_conflict
- confidence_score
- match_reasons
- status: pending / approved / rejected / deferred
- reviewed_by
- reviewed_at
- reviewer_notes
- ip_address
- user_agent

---

## 8. Matching Logic

### 8.1 Cross-Import Person Matching

Compare new contacts against prior approved contacts and master people using evidence such as:

| Evidence | Meaning |
|---|---|
| Exact email | Strong same-person signal |
| Exact phone + similar name | Strong same-person signal |
| Same name + same address | Moderate same-person signal |
| Similar name + same phone | Moderate same-person signal |
| Prior approved same_person decision | Strong historical evidence |
| Prior rejected/different decision | Negative evidence |

No match should be approved automatically.

### 8.2 Cross-Import Household Matching

Compare new contacts against existing global households using evidence such as:

| Evidence | Meaning |
|---|---|
| Same normalized address + ZIP | Strong household signal |
| Same address + shared last name | Strong household signal |
| Same phone + last name + ZIP | Moderate household signal |
| Prior approved household membership | Strong historical evidence |
| Prior rejected household link | Negative evidence |

Exact email alone remains a duplicate/person signal, not a household signal.

### 8.3 Household Merge Suggestions

If two global households appear to represent the same real-world household, v2 may suggest a household merge.

Example:

- `HH_a1b2c3d4` = `123 Main St | 94301`
- `HH_f9e8d7c6` = `123 Main Street | 94301`

This must be a pending suggestion requiring explicit approval.

---

## 9. Review Queues

v2 adds review queues beyond the v1 queues:

### 9.1 Cross-Import Person Matches

Shows:

- current contact
- historical contact or master person
- match evidence
- prior reviewer decisions
- confidence score
- approve / reject / defer

### 9.2 Existing Household Matches

Shows:

- current contact or current household suggestion
- existing global household
- household members
- address evidence
- prior decisions
- approve / reject / defer

### 9.3 Household Merge Queue

Shows:

- two candidate global households
- overlapping members or address evidence
- risk warning
- approve / reject / defer

---

## 10. Exports

v2 should add exports that help nonprofits use cross-import intelligence.

### Export Master People

One row per approved master person.

### Export Global Households

One row per approved global household, with member count and members.

### Export Cross-Import Backlog

All pending/deferred cross-import match suggestions.

### Export Identity Audit

All approved/rejected/deferred identity and household link decisions.

---

## 11. API Writeback

Givebutter API writeback remains out of scope unless separately approved.

v2 may prepare data for manual upload or review, but it should not write changes back to Givebutter automatically.

---

## 12. Safety Requirements

v2 must include tests proving:

- Cross-import suggestions are pending by default.
- Historical contacts are not mutated.
- Master-person links require approval.
- Global-household links require approval.
- Prior decisions affect scoring but do not auto-approve future matches.
- Rejected historical matches suppress or lower repeat suggestions.
- Exact email is still a person/duplicate signal, not a household signal.
- Household merge suggestions never auto-merge.
- All cross-import decisions are audit logged.

---

## 13. Acceptance Criteria

v2 is complete when:

- A new import can be compared against prior approved contacts and households.
- The system creates pending cross-import person match suggestions.
- The system creates pending existing-household link suggestions.
- Reviewers can approve, reject, or defer these suggestions.
- Approved links create durable master-person or global-household relationships.
- Original contacts and raw rows remain unchanged.
- The app can export master people, global households, cross-import backlog, and identity audit logs.
- All safety and regression tests pass.

---

## 14. Deferred Beyond v2

These are intentionally not included unless separately approved:

- Automatic Givebutter API writeback
- Fully automated identity resolution
- Automated duplicate merges without human approval
- CRM-native sync jobs
- AI-generated salutations
- Retention/lifecycle alerts
- Meta CAPI or ad-platform integrations

---

## 15. Plain-English Summary

Householder v1 cleans and households one uploaded CSV at a time.

Householder v2 remembers what reviewers approved in the past.

When a new CSV is uploaded, v2 can say:

> “This new donor looks like a person we have seen before.”
> “This new donor may belong to an existing household.”
> “This household appears to be the same as a household we approved earlier.”

But v2 still follows the same safety rule:

> It can suggest. A human must approve. The original data is never overwritten.
