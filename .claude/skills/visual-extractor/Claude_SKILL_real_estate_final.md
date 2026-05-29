# Skill: extract-real-estate-listings-independently

## Description
Extract structured real-estate listings from Redfin and Zillow emails. Accesses the inbox via the Gmail MCP connector and processes each qualifying email as a rendered visual — extracting listing data directly from what is visible on screen rather than parsing raw HTML or plain text.
This skill is an independent extractor designed for comparison against another parsing method.

---

## What this skill does

- Connects to Gmail via the Gmail MCP connector
- Searches inbox for emails from supported senders
- Processes each email body as a rendered visual image
- Identifies all listing cards visible in the email
- Extracts structured property data
- Applies strict geographic filtering
- Returns normalized JSON output

---

## When to use this skill

Use this skill when:
- Processing Redfin or Zillow emails
- Building an independent extraction pipeline
- Comparing extraction accuracy vs another system

---

## Inputs

This skill operates on:
- Email metadata (sender, subject, id) — retrieved via Gmail MCP
- Email body rendered as a visual image — all listing data is extracted visually from what is visible on screen

Note: This skill does NOT parse raw HTML or plain text. All extraction is performed visually on the rendered email.

Optional:
{
  "time_window": "last_24_hours",
  "max_emails": 20,
  "mode": "full"
}

---

## Modes

This skill supports three operational modes controlled by the `mode` parameter.

### `full` (default)
Full extraction: crop individual listing cards, extract all fields per card.
Use for: ingestion pipeline, audit Phase 3 (recovering missed listings).

### `count`
Count only: render the full email as a single image, return one integer — the number of distinct listing cards visible.
Use for: audit Phase 1 triage. Fast and cheap. No card cropping.

### `addresses`
Address list only: render the full email as a single image, return a JSON array of all listing addresses visible.
Use for: audit Phase 2 diff. One call per email. No card cropping.

### Mode behavior summary

| Mode | Image sent | Cards cropped | Fields extracted | Output |
|---|---|---|---|---|
| `count` | Full page (resized) | No | No | Integer |
| `addresses` | Full page (resized) | No | Address only | String array |
| `full` | Per card (cropped + resized) | Yes | All fields | JSON (see Output section) |

For `count` and `addresses` modes, send the full rendered email as a single image resized to 400px wide. Do not crop individual cards — the goal is a fast overview of the entire email at once.

---

## Supported senders

### Redfin
- listings@redfin.com
- alerts@redfin.com
- noreply@redfin.com
- any @redfin.com with listing content

### Zillow
- instant-updates@mail.zillow.com
- noreply@zillow.com
- alerts@zillow.com
- any @mail.zillow.com or @zillow.com with listing content

Ignore all other senders.

---

## Geographic filter (required)

Only include listings located in:

- Berkeley, CA
- Oakland, CA
- Albany, CA

---

## City matching rules (fuzzy, CA-only)

### Allowed cities
- Berkeley
- Oakland
- Albany

---

## State requirement

The listing must clearly indicate:
- CA
- or California

If the state is not present or not CA → discard the listing.

---

## Fuzzy matching rules

City matching should be:
- case-insensitive
- tolerant of formatting variations

Accept:
- "Berkeley, CA"
- "Berkeley CA"
- "Berkeley, California"
- "berkeley ca"
- "OAKLAND, CA"
- "Albany CA 94706"

---

## Matching behavior

### Include listing if:
- city matches one of:
  - Berkeley
  - Oakland
  - Albany
- AND state is CA or California

### Reject listing if:
- city is a neighborhood (e.g., "Oakland Hills")
- city is outside allowed list
- state is not CA
- city cannot be determined

---

## Important rules (geographic)

- Do NOT treat neighborhoods as cities
- Do NOT infer city from ZIP
- Do NOT infer city from nearby landmarks
- Do NOT guess missing state
- If state is missing → discard listing
- If city is unclear → discard listing

---

## Output

Return only valid JSON:

{
  "emails": [
    {
      "email_id": "string",
      "subject": "string",
      "sender": "string",
      "listings": [
        {
          "listing_index": 0,
          "card_position": 0,
          "property_url": "string or null",
          "extracted": {
            "address": "string or null",
            "zip_code": "string or null",
            "price": 0,
            "beds": 0,
            "baths": 0,
            "sqft": 0,
            "lot_sqft": 0,
            "garage_spots": 0,
            "walkability": "string or null"
          },
          "confidence": "high",
          "needs_review": false
        }
      ]
    }
  ]
}

---

## Workflow

### 0. Access inbox
Connect to Gmail using the Gmail MCP connector. Search for emails using the query `from:(redfin.com OR zillow.com)`. Retrieve up to `max_emails` (default: 20) from within the `time_window` (default: last 24 hours). Pass each matching email to the steps below.

### 1. Filter emails
From the retrieved emails, select only those from supported senders with listing-related content. Ignore all others.

### 2. Read content
Render each email body visually. Branch by mode:

- **`count` or `addresses`**: render the full email as a single image, resized to 400px wide. Do not crop cards.
- **`full`**: render the full email, then crop individual listing card regions. Resize each card before sending.

---

### 3. Branch by mode

---

#### Mode: `count`

Scan the rendered full-page image. Count the number of distinct property listing cards visible.

Return only:
```json
{ "email_id": "string", "count": 0 }
```

Stop here. Do not extract any other fields.

---

#### Mode: `addresses`

Scan the rendered full-page image. Identify every distinct property listing card visible. For each card, extract only the street address.

Apply geographic filter: only include addresses in Berkeley CA, Oakland CA, or Albany CA. Discard all others.

Return only:
```json
{
  "email_id": "string",
  "addresses": ["123 Main St", "456 Oak Ave"]
}
```

Stop here. Do not extract any other fields.

---

#### Mode: `full`

Continue to steps 4–9 below.

---

### 4. Group candidates
Each visually distinct listing card is treated as one listing. Do not merge cards or split a single card into multiple listings.

---

### 5. Extract fields

- address
- zip_code
- price
- beds
- baths
- sqft
- lot_sqft
- garage_spots
- walkability

Use null if unclear.

---

### 6. Normalize

- "$1,295,000" → 1295000
- "2,734 Sq Ft" → 2734

---

### 7. Extract property URL
If a URL is visibly printed or inferable from the listing card, capture it. Otherwise set to null.

---

### 8. Confidence

HIGH:
- all core fields clear

MEDIUM:
- partial data

LOW:
- weak signal

---

### 9. Review flag

Set needs_review = true if:
- missing address
- ambiguity
- low confidence

---

## Cost optimization

Visual extraction is token-intensive. Apply these rules in order to minimize unnecessary vision calls.

### 1. Skip already-processed emails
Before rendering any email, check whether its `email_id` has already been processed (e.g., stored in SQLite or a local cache). If yes → skip entirely. Do not re-process emails across runs.

### 2. Filter by metadata before rendering
Use sender address and subject line to confirm the email is a listing alert before rendering it visually. If the subject contains no listing signals (e.g., "Unsubscribe confirmation", "Account update") → discard without rendering.

### 3. Crop to listing cards before vision call
Do not send the full email render as a single image. Identify and crop individual listing card regions first, then send each card as a separate, smaller image. This reduces tokens per vision call significantly on multi-listing digest emails.

### 4. Resize images before sending
Resize each card image to the minimum resolution where text remains legible before passing to the vision model. Full-resolution renders are rarely necessary.

### 5. Cap emails per run
Respect the `max_emails` parameter (default: 20). Do not process more than this per run regardless of inbox size.

---



- Do not hallucinate
- Do not use external parsers
- Use null if unsure
- Do not force grouping
- Return JSON only
