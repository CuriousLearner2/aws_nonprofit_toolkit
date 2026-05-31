# Givebutter Processor API Reference

Complete API documentation for programmatic access to the processor.

## Base URL

```
http://127.0.0.1:8000
```

## Endpoints

### Upload CSV File

Process a Givebutter CSV export with validation.

```http
POST /upload
Content-Type: multipart/form-data
```

**Parameters:**
- `file` (required) - CSV file to process

**Response (200):**
```json
{
  "filename": "upload_20260530_212146_realistic_export.csv",
  "record_count": 10,
  "warning_count": 9,
  "fail_count": 0,
  "status": "processed"
}
```

**Response (400):**
```json
{
  "error": "Only CSV files allowed"
}
```

---

### List Files in Processing

Get all files currently being reviewed.

```http
GET /api/processing
```

**Response (200):**
```json
[
  {
    "filename": "upload_20260530_212146_realistic_export.csv",
    "rows": 10,
    "mtime": 1780199484.4634426
  }
]
```

---

### Get Records from File

Retrieve all records from a processing file with validation results.

```http
GET /api/processing/<filename>
```

**Parameters:**
- `filename` (path) - Name of the processing file (URL-encoded)

**Response (200):**
```json
{
  "filename": "upload_20260530_212146_realistic_export.csv",
  "records": [
    {
      "idx": 0,
      "Transaction ID": "tr_7b82f19a0c",
      "Payout ID": "po_91a283f",
      "Status": "Settled",
      "Date": "2026-05-02 14:22:11",
      "Name": "Morgan Davis",
      "Email": "morgan.davis42@gmail.com",
      "Phone": "555-019-2834",
      "Address 1": "123 Main St",
      "Address 2": "",
      "City": "San Jose",
      "State": "CA",
      "Zip": "95112",
      "Country": "US",
      "Amount": "50.00",
      "Processing Fee": "1.75",
      "Givebutter Fee": "0.00",
      "Fees Covered": "Yes",
      "Campaign Title": "General Operating Fund",
      "Payment Method": "Card",
      "utm_source": "facebook",
      "utm_medium": "cpc",
      "Validation_Tier": "WARNING",
      "Issues": "Duplicate: Phone match: tr_8b291c3d4e",
      "Suggested_Modifications": ""
    }
  ]
}
```

**Response (400):**
```json
{
  "error": "Invalid filename"
}
```

---

### Submit Operator Decisions

Process operator decisions and generate output files.

```http
POST /api/processing/<filename>/submit
Content-Type: application/json
```

**Parameters:**
- `filename` (path) - Name of the processing file

**Request Body:**
```json
{
  "decisions": [
    {
      "idx": 0,
      "decision": "approved",
      "notes": ""
    },
    {
      "idx": 1,
      "decision": "followup",
      "notes": "Verify email typo correction"
    },
    {
      "idx": 2,
      "decision": "rejected",
      "notes": "Invalid phone format"
    }
  ]
}
```

**Fields:**
- `idx` (number, required) - Record index (0-based)
- `decision` (string, required) - One of: `approved`, `followup`, `rejected`
- `notes` (string, optional) - Operator comments (max 500 chars)

**Response (200):**
```json
{
  "status": "success",
  "approved": 5,
  "followup": 4,
  "rejected": 1
}
```

**Response (400):**
```json
{
  "error": "No decisions provided"
}
```

**Side Effects:**
- Creates `review/approved/<filename>_APPROVED.csv` (if approved records)
- Creates `review/followup/<filename>_FOLLOWUP.csv` (if followup records)
- Creates `review/rejected/<filename>_REJECTED.csv` (if rejected records)
- Moves processing file to `archive/<filename>`
- Adds `Operator_Notes` column to followup file

---

### Cancel Review

Cancel ongoing review and return file to intake queue.

```http
POST /api/processing/<filename>/cancel
```

**Parameters:**
- `filename` (path) - Name of the processing file

**Response (200):**
```json
{
  "status": "cancelled"
}
```

**Response (400):**
```json
{
  "error": "Invalid filename"
}
```

**Side Effects:**
- Moves file from `processing/` to `intake/new/`

---

### Health Check

Verify API is running.

```http
GET /health
```

**Response (200):**
```json
{
  "status": "ok",
  "version": "3.0"
}
```

---

## Error Handling

All errors return appropriate HTTP status codes:

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | File processed, decisions saved |
| 400 | Bad Request | Missing required parameters |
| 401 | Unauthorized | Invalid authentication token |
| 404 | Not Found | File not found |
| 500 | Server Error | Processing failed |

**Error Response Format:**
```json
{
  "error": "Human-readable error message"
}
```

---

## Authentication

Optional token-based authentication. Set `ADMIN_TOKEN` environment variable:

```bash
export ADMIN_TOKEN="your-secret-token"
python3 scripts/uploader/app.py
```

When enabled, include token in requests:

```http
POST /api/processing/<filename>/submit
Authorization: Bearer your-secret-token
Content-Type: application/json
```

Requests without valid token return 401 Unauthorized.

---

## File Management

### Upload Directory
- Location: `intake/new/`
- Naming: `upload_<timestamp>_<original_filename>.csv`
- Lifecycle: Created on upload → moved to processing → archived after decision

### Processing Directory
- Location: `review/processing/`
- Contains: Files currently being reviewed
- Cleanup: Automatic after decisions submitted

### Output Directories
- Approved: `review/approved/` → `*_APPROVED.csv`
- Follow-up: `review/followup/` → `*_FOLLOWUP.csv`
- Rejected: `review/rejected/` → `*_REJECTED.csv`

### Archive Directory
- Location: `archive/`
- Contains: All processed files (with/without decisions)
- Purpose: Audit trail of processed uploads

---

## Validation Response Format

Each record in the processing response includes validation results:

**Validation_Tier:**
- `PASS` - Record passes reference list validation
- `WARNING` - Record has anomalies but is valid
- `FAIL` - Record violates rules

**Issues:**
- Semicolon-separated list of validation failures
- Examples:
  - `Duplicate: Phone match: tr_8b291c3d4e`
  - `Missing amount`
  - `Invalid: all digits are identical`

**Suggested_Modifications:**
- Semicolon-separated list of recommended fixes
- Examples:
  - `Email typo detected. Consider: taylor.smith11@gmail.com`
  - `Format: (555) 015-2931`
  - `High-dollar donation (>= $1000)`

---

## Example Workflows

### Workflow 1: Bulk Approve with Selective Review

```bash
# 1. Upload
curl -X POST -F "file=@donations.csv" http://127.0.0.1:8000/upload

# 2. Get records
curl http://127.0.0.1:8000/api/processing/upload_*.csv | jq '.records'

# 3. Approve all, mark questionable ones for followup
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "decisions": [
      {"idx": 0, "decision": "approved", "notes": ""},
      {"idx": 1, "decision": "followup", "notes": "Verify"}
    ]
  }' \
  http://127.0.0.1:8000/api/processing/upload_*.csv/submit
```

### Workflow 2: Reject All Invalid Records

```bash
# Get records with FAIL tier
curl http://127.0.0.1:8000/api/processing/upload_*.csv | \
  jq '.records[] | select(.Validation_Tier == "FAIL")'

# Reject all failures
# (construct decisions array with idx and "rejected")
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"decisions": [{"idx": 2, "decision": "rejected", "notes": "Invalid email"}]}' \
  http://127.0.0.1:8000/api/processing/upload_*.csv/submit
```

### Workflow 3: Export for Analysis

```bash
# Get all records with validation info
curl http://127.0.0.1:8000/api/processing/upload_*.csv | \
  jq '.records[] | {Name, Email, Validation_Tier, Issues}' > analysis.json
```

---

## Rate Limiting

No built-in rate limiting. If needed, implement at reverse proxy level.

---

## CORS

CORS is disabled by default. For cross-origin requests, add to `app.py`:

```python
from flask_cors import CORS
CORS(app)
```

---

## Timeouts

- File upload: 30 seconds (depends on file size)
- Processing: Depends on record count (typically < 5 seconds for 1000 records)
- UI timeout: 60 seconds for inactive reviews

---

## Version

Current API version: **3.0**

Check at `/health` endpoint.

---

## Support

For detailed information on validation rules, see `PROCESSOR_GUIDE.md`.

For quick start guide, see `QUICK_START.md`.
