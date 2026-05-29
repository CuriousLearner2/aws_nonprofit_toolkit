# Audit Spec: Ongoing BS4 vs Visual Extraction Audit

## Purpose

Run a lightweight visual check on every ingested email to detect listings that
BS4 missed. Store results in `extraction_audit` for automated resolution or
human review. Trigger full visual recovery only when a real miss is confirmed.

---

## When to run

After every email ingest run (immediately following `batch_ingest.run_batch_ingest`).

---

## Database schema

```sql
CREATE TABLE IF NOT EXISTS extraction_audit (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id          TEXT NOT NULL,
    subject           TEXT,
    source            TEXT,           -- Redfin | Zillow
    checked_at        TEXT,           -- ISO timestamp
    bs4_count         INTEGER,        -- listings BS4 extracted from this email
    visual_count      INTEGER,        -- card count from Phase 1
    bs4_addresses     TEXT,           -- JSON array of addresses BS4 stored
    visual_addresses  TEXT,           -- JSON array from Phase 2 (null until Phase 2 runs)
    missed_addresses  TEXT,           -- JSON array: in visual_addresses but not bs4_addresses
    status            TEXT DEFAULT 'pending',  -- pending | resolved | needs_review
    resolution_note   TEXT            -- why resolved or what needs review
);
```

---

## Phases

### Phase 1 — Card count (runs on every email)

Invoke the visual extractor skill in `count` mode on the rendered email.
Compare the returned count against `bs4_count` (number of listings BS4
stored for this email).

**Flag condition:**

```
visual_count > bs4_count
```

- Insert a row into `extraction_audit` for every email processed.
- Set `status = 'pending'` for flagged emails.
- Set `status = 'resolved'` and `resolution_note = 'counts match'` for clean emails.

No further action for clean emails.

---

### Phase 2 — Address list (runs on flagged emails only)

Invoke the visual extractor skill in `addresses` mode on the flagged email.
The skill returns only in-geo addresses (Berkeley/Oakland/Albany CA) — no
out-of-geo filtering is needed here.

Normalize both lists before comparing:
- Uppercase
- Strip punctuation
- Strip unit/apt suffixes for matching (e.g. "848 STANNAGE AVE APT 11" → "848 STANNAGE AVE")

Compute `missed_addresses`:
```
missed = [a for a in visual_addresses
          if not any(a.startswith(b[:12]) for b in bs4_addresses)
          and not already_in_db(a)]
```

Update the audit row:
- Set `visual_addresses` and `missed_addresses`.
- If `missed_addresses` is empty → set `status = 'resolved'`,
  `resolution_note = 'visual addresses already in DB or matched BS4'`.
- Otherwise → leave `status = 'pending'`, proceed to Phase 3.

---

### Phase 3 — Full field extraction (runs only for confirmed misses)

Invoke the visual extractor skill in `full` mode, but scoped to only the
missed addresses. For each missed address:
1. Crop the card region containing that address from the rendered email.
2. Extract all fields.
3. Ingest via the normal upsert pipeline (apply `is_rental_listing` and
   `is_allowed_city` filters before writing).

After ingestion:
- Set `status = 'resolved'`, `resolution_note = 'ingested N missed listings'`.

---

## Automated resolution rules

| Condition | Action | Status |
|---|---|---|
| `visual_count == bs4_count` | No further action | `resolved` |
| `visual_count > bs4_count` AND Phase 2 finds no missed in-geo addresses | No further action | `resolved` |
| `visual_count > bs4_count` AND missed addresses already in DB (from another email) | No further action | `resolved` |
| `visual_count > bs4_count` AND confirmed missed in-geo address not in DB | Phase 3 → ingest | `resolved` |
| Phase 2 address is ambiguous (no city, OCR garbled) | Flag for human review | `needs_review` |

---

## Human review queue

Query for rows requiring attention:

```sql
SELECT email_id, subject, source, visual_count, bs4_count,
       missed_addresses, resolution_note
FROM extraction_audit
WHERE status = 'needs_review'
ORDER BY checked_at DESC;
```

Common reasons a row lands in `needs_review`:
- Visual returned an address with no recognizable city
- OCR error makes the address unresolvable (e.g. "FARLANE" vs "FAIRLANE")
- Address matches an existing DB entry but with a significantly different price
  (possible re-listing at new price — should not be auto-updated)

---

## Cost profile

| Phase | Runs on | Model | Calls | Est. cost/email |
|---|---|---|---|---|
| Phase 1 | Every email | Sonnet (batch) | 1 | ~$0.001 |
| Phase 2 | Flagged only (~15%) | Sonnet (batch) | 1 | ~$0.002 |
| Phase 3 | Missed cards only | Sonnet (batch) | 1 per missed card | ~$0.003/card |

Estimated total: ~$1.50/month at 30 emails/day.

---

## Hard rules

- Do not run Phase 2 or 3 unless Phase 1 flags a count mismatch.
- Do not ingest a listing in Phase 3 without applying `is_rental_listing` and `is_allowed_city` filters.
- Do not auto-resolve a row with `needs_review` status — human must clear it.
- Do not modify the BS4 extractor or its existing DB records during audit.
- Always normalize addresses before comparing across extractors.
