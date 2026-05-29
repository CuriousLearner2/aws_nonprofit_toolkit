---
name: parse-real-estate-email
description: Extract structured property listing data from Redfin and Zillow emails.
---

# Real Estate Email Parsing

## Input Format

One of the following:
- Raw email content in plain text or HTML or an image (provided directly by the user)
- **Inbox mode**: no input provided — fetch emails from Gmail using the steps below

---

## Inbox Fetch Workflow

If no email input is provided, fetch from Gmail:

1. Authenticate with Gmail if not already authenticated
2. Search for the 2 most recent Redfin emails: query `from:redfin.com`
3. Search for the 2 most recent Zillow emails: query `from:zillow.com`
4. Retrieve the full content of each email (up to 4 total)
5. Parse each email using the Workflow below
6. Combine all valid listings into a single output array

---

## Definitions

- **Candidate listing**: A section of content that may represent a single property
- **Valid listing**: A candidate listing that satisfies the Validation Rules

---

## Workflow

1. Identify sections of the email that may represent individual property listings (candidate listings)
2. For each candidate listing, attempt to extract:
   - address
   - city
   - state
   - price
   - beds
   - baths
   - house_sqft
   - lot_size_sqft
   - hoa_monthly
   - garage_spots
   - listing_url
3. Normalize extracted values
4. Apply validation rules to determine whether to keep or discard each candidate
5. Return only valid listings in the required JSON format

---

## Normalization Rules

- price → integer (remove `$` and commas)
- beds → number (float)
- baths → number (float)
- house_sqft → integer
- lot_size_sqft → integer
- hoa_monthly → integer (monthly HOA fee in dollars)
- garage_spots → integer

- If a non-required field cannot be found, set it to `null`
- Do not guess or infer missing values

---
## Field Disambiguation Rules

- Use the square footage associated with the property interior (e.g., "Sq. Ft.")
- Ignore lot size (e.g., "sq ft lot") for the square footage of the interior.  If lot size is present include it in the lot size field.
---

## Validation Rules

A candidate listing is valid only if it contains at least one of:
- address
- listing_url

If both are missing:
- discard the candidate listing
- do not include it in the output

---

## Filtering Rules

Ignore any section of content that does not represent a specific property listing.

Do NOT treat a section as a listing unless it refers to a specific property.

Non-listing content includes:
- advertisements
- promotional or branding text
- navigation links
- app download prompts
- email footer content
- unsubscribe or preference links

Examples of non-listing content:
- "See more homes in San Jose"
- "Download the Redfin app"
- "Manage your alerts"
- "Homes you may like"
- "Buy with a Redfin agent"
- "Get pre-approved"
- "Unsubscribe"
- "Improve your recommedations"
- "Get pre-qualified"
- "See latest search results"

A section should be treated as a listing only if it contains at least one strong listing identifier:
- address
- listing_url

If it is unclear whether a section represents a valid listing, exclude it.

---

## Output Format

Return a JSON array of valid listings using this schema:

[
  {
    "address": "string or null",
    "city": "string or null",
    "state": "string or null",
    "price": currency or null,
    "beds": number or null,
    "baths": number or null,
    "house_sqft": integer or null,
    "lot_size_sqft": integer or null,
    "hoa_monthly": integer or null,
    "garage_spots": integer or null,
    "listing_url": "string or null"
  }
]

---

## Output Rules

- Output only valid JSON
- Include only listings that satisfy the Validation Rules
- For each included listing, include all defined fields
- Use `null` for any missing non-required values
- Do not omit fields
- Do not include explanations, comments, or markdown formatting
- `listing_url` → raw URL string (machine readable), or `null` if not found