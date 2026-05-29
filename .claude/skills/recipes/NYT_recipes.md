---
name: nyt-recipe-manager
description: Gmail-to-SQLite recipe ingestion with deep-link crawling and comment-based substitution analysis.
---

> **Prerequisite:** This skill requires a `nyt_cookies.json` file in the project root before it can crawl recipe pages. See `SETUP.md` for one-time setup instructions.

# NYT Cooking Recipe Manager Skill

## 1. Discovery & Search (Gmail)
* **Target Query:** `from:nytdirect@nytimes.com`
* **Sender Filter:** Only process emails where the sender display name is "NYT Cooking". Do not filter by subject — NYT Cooking email subjects vary widely and are not a reliable signal.
* **Message Handling:** Use the Gmail tool to retrieve the raw HTML body. Before parsing, decode the body using Python's `quopri.decodestring()` or the `email` standard library (`email.message_from_bytes` with `get_payload(decode=True)`). The emails use `Content-Transfer-Encoding: quoted-printable`, which encodes `=` as `=3D` and line breaks as `=0D=0A`. Failing to decode before parsing will produce malformed HTML.
* **Duplicate Check:** Query the local SQLite `Recipes` table for the `source_email_id` before proceeding.

## 2. Navigation Logic (The "Crawl")
NYT emails contain nested links. All links in the email are wrapped in NYT redirect URLs (`nl.nytimes.com/f/a/...`) — they do not link directly to `cooking.nytimes.com`. Always follow redirects to resolve the final destination URL before classifying the link.

At each level, programmatically follow the resolved URL using the authenticated session and parse the response HTML before proceeding to the next level. Do not assume link destinations — always fetch and inspect.

Follow this hierarchy:

1. **Level 1 (Email):** Find links whose resolved destination URL contains `cooking.nytimes.com` or `nytimes.com/newsletters` or `nytimes.com/topics`. Do NOT rely on CSS class names like `css-le6lgc` — these are hashed names that change with NYT deploys. Instead match on link text containing "View Recipe", "View the recipes", or "Get the recipe", OR on the resolved destination URL pattern.

2. **Level 2 (Digest/Collection):** Detect email type by the resolved URL:
   - If resolved URL contains `/newsletters/` or `/topics/` → **Digest email**: crawl that page to find all `cooking.nytimes.com/recipes/` links, then process each as Level 3.
   - If resolved URL contains `/recipes/` directly → **Single recipe email**: skip to Level 3 immediately.

3. **Level 3 (Recipe Page):** This is the terminal node for extraction. Requires authenticated session (see Section 4a).

## 3. Extraction Schema (SQLite)
Extract the following text data for insertion into your existing database.

### Extraction approach: two-pass

**Pass 1 — Schema.org JSON-LD (primary)**
Every NYT Cooking recipe page embeds structured data in a `<script type="application/ld+json">` block. Extract this first using BeautifulSoup. It reliably covers standard fields and requires no interpretation. Log each field as `source: json-ld`.

**Pass 2 — Haiku fallback (for missing fields)**
For any standard field that is null after Pass 1, fall back to a Haiku call against the page HTML to extract the missing value. Log each field as `source: haiku`.

**Substitution Summary — always Haiku**
This field is never in JSON-LD. Always use Haiku to read and summarize the Community comments section regardless of Pass 1 results. Log as `source: haiku`.

### Field table

| Field | JSON-LD key | Haiku fallback? |
| :--- | :--- | :--- |
| **Recipe Name** | `name` | Yes |
| **Author** | `author.name` | Yes |
| **Total Time** | `totalTime` | Yes |
| **Yield/Servings** | `recipeYield` | Yes |
| **Ingredients** | `recipeIngredient` | Yes |
| **Instructions** | `recipeInstructions` | Yes |
| **Substitution Summary** | — | Always (never in JSON-LD) |

## 4a. Authentication (NYT Paywall)
Recipe pages at `cooking.nytimes.com` require an authenticated session. This skill expects a `nyt_cookies.json` file in the project root containing exported browser cookies from an active NYT login. See `SETUP.md` for one-time setup instructions.

* **Usage:** Load `nyt_cookies.json` and pass to `requests.Session` before crawling recipe pages:
  ```python
  import json, requests
  session = requests.Session()
  with open("nyt_cookies.json") as f:
      for cookie in json.load(f):
          session.cookies.set(cookie["name"], cookie["value"])
  ```
* **Cookie expiry:** NYT session cookies expire periodically. If a recipe page returns a login redirect (check for `location` header pointing to `myaccount.nytimes.com`) → log a warning and skip that recipe rather than failing silently.

## 4b. SQLite Persistence
* **Persistence:** Persist the extracted recipe data to the SQLite database.
* **Database Path:** Read the database path from the shared project config file (e.g., `config.json` or `.env`). Ask Claude Code where the existing recipe-related code stores this path — use the same config entry. Do not hardcode the path in this skill.
* **Semantic Note:** Ensure the `substitution_summary` and `ingredients` fields are populated with clean text so Claude can perform native semantic search later.

## 5. Examples & Patterns

### Example A: Single Featured Recipe (e.g., San Choy Bao)
**Email Link Pattern:**
```html
<a href="[https://cooking.nytimes.com/recipes/1024032-san-choy-bao](https://cooking.nytimes.com/recipes/1024032-san-choy-bao)" class="css-le6lgc">
  View Recipe: San Choy Bao
</a>
```
**Processing path:** Level 1 → Level 3 (skip Level 2). The redirect resolves directly to a `/recipes/` URL. Extract one recipe.

---

### Example B: Digest / Collection Email (e.g., "24 Easy Pastas to Welcome Spring")
**Email Link Pattern (after quoted-printable decode):**
```html
<a href="https://nl.nytimes.com/f/cooking/y11xySWACuXa95rhmVUiIg~~/.../..." class="css-le6lgc">
  <h3>24 Easy Pastas to Welcome Spring</h3>
  <p>These recipes make a case for pasta as the season's perfect food...</p>
  <span>View the recipes.</span>
</a>
```
**Signal:** Link text contains "View the recipes." (note the period). The wrapping anchor contains a headline and blurb — this is the primary featured link in the email.

**Resolved URL pattern:** After following the `nl.nytimes.com/f/cooking/` redirect, the destination will be a `/newsletters/` or `/topics/` collection page (e.g., `cooking.nytimes.com/topics/pasta`).

**Processing path:** Level 1 → Level 2 → Level 3.
1. Follow the redirect from the email link to the collection page.
2. On the collection page, find all `<a>` tags whose `href` contains `cooking.nytimes.com/recipes/`.
3. Process each as a Level 3 recipe page extraction.
