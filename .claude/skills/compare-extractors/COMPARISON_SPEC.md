# Comparison Spec: Visual Extractor vs HTML/BeautifulSoup Extractor

## Purpose
Run both extractors against the same set of recent real estate emails (last 4 hours)
and produce a side-by-side comparison report plus discrepancy log printed to console.

---

## Extractors

### Extractor A: HTML/BeautifulSoup (existing)
- You already know how to run this.
- Reads inbox emails, parses HTML using BeautifulSoup.
- Writes results to SQLite.

### Extractor B: Visual (new)
- Follows the skill file: `Claude_SKILL_real_estate_final.md`
- Connects to Gmail via Gmail MCP connector.
- Searches: `from:(redfin.com OR zillow.com)`
- Time window: last 4 hours
- Processes each email body as a rendered visual image.
- Applies geographic filter: Berkeley CA, Oakland CA, Albany CA only.
- Returns JSON output — print to console only (do not write to SQLite).

---

## Time window
Both extractors must use the same window: **last 4 hours** from time of execution.

---

## Field mapping

The two extractors use different field names and formats. Use this mapping for comparison:

| Comparison Field | BS4/SQLite column      | Visual extractor field | Notes                                      |
|------------------|------------------------|------------------------|--------------------------------------------|
| address          | Address                | address                | Normalize to uppercase for matching        |
| zip_code         | *(parse from Address)* | zip_code               | Extract trailing ZIP from BS4 address      |
| price            | Price                  | price                  | Strip "$", commas, and annotations like "(unchanged)" from BS4; visual is already integer |
| beds             | Beds/Baths             | beds                   | Parse left side of "N bed / N bath"        |
| baths            | Beds/Baths             | baths                  | Parse right side of "N bed / N bath"       |
| sqft             | House sqft             | sqft                   | Strip commas                               |
| lot_sqft         | Lot sqft               | lot_sqft               | Strip commas                               |
| garage_spots     | Garage                 | garage_spots           | Parse leading integer from "N spots"       |

### Fields present in only one extractor (note but do not penalize)
- BS4 only: `first_seen`, `latest`
- Visual only: `walkability`

---

## Matching listings across extractors

Match listings from Extractor A and Extractor B using **address** as the primary key:
- Normalize both to uppercase, strip punctuation before comparing.
- If address is null in either → attempt match on price + beds + baths.
- If no match found → flag as unmatched (see Recall section below).

---

## Metrics to compute

### 1. Coverage (field extraction rate)
For each extractor independently, for each shared comparison field:
- Count listings where field is non-null.
- Report as percentage of total listings extracted.

Example output:
```
COVERAGE
                  | Extractor A (BS4) | Extractor B (Visual)
------------------+-------------------+---------------------
address           | 100%              | 100%
price             | 95%               | 90%
beds              | 90%               | 85%
...
```

### 2. Accuracy (field value agreement)
For matched listings only, for each shared comparison field:
- Compare normalized values between the two extractors.
- Report % of matched listings where values agree.
- Flag any disagreements in the discrepancy log.

Example output:
```
ACCURACY (matched listings only)
Field         | Agreement
--------------+----------
price         | 100%
beds          | 95%
sqft          | 80%
...
```

### 3. Recall (listings found)
- Total listings found by A only
- Total listings found by B only
- Total found by both
- Total unique listings across both

Example output:
```
RECALL
Found by both:           8
Found by A (BS4) only:   2
Found by B (Visual) only: 1
Total unique:            11
```

---

## Discrepancy log
For every matched listing where any field value disagrees, print:

```
DISCREPANCY: 3214 California St, Berkeley CA 94703
  Field     | BS4 value   | Visual value
  ----------+-------------+-------------
  price     | 1198000     | 1195000
  sqft      | 1858        | null
```

---

## Console output order
1. Run summary (time window, emails processed by each extractor)
2. RECALL table
3. COVERAGE table
4. ACCURACY table
5. DISCREPANCY LOG (full detail, one block per listing)

---

## Hard rules
- Do not write visual extractor output to SQLite.
- Do not modify the BS4 extractor or its database.
- Normalize all values before comparison — never compare raw strings.
- If a field is null in both extractors, exclude it from accuracy calculation for that listing.
