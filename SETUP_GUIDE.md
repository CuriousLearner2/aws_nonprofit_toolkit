# Comprehensive Setup & Credential Guide

This guide will walk you through obtaining the necessary credentials to run the AWS Nonprofit Toolkit and move from synthetic data to live marketing synchronization.

---

## Configuration Requirements Matrix

Use the table below to identify which environment variables are required based on your specific use case.

┌────────────────────────┬─────────────┬─────────────┬─────────────┐
│ Variable               │ Data-Gen    │ Meta-Sync   │ Full AWS    │
│                        │ Only        │ Only        │ Pipeline    │
├────────────────────────┼─────────────┼─────────────┼─────────────┤
│ `META_ACCESS_TOKEN`    │ ❌ No        │ ✅ Yes       │ ✅ Yes       │
├────────────────────────┼─────────────┼─────────────┼─────────────┤
│ `META_AD_ACCOUNT_ID`   │ ❌ No        │ ✅ Yes       │ ✅ Yes       │
├────────────────────────┼─────────────┼─────────────┼─────────────┤
│ `AWS_ACCESS_KEY_ID`    │ ❌ No        │ ❌ No        │ ✅ Yes       │
├────────────────────────┼─────────────┼─────────────┼─────────────┤
│ `AWS_SECRET_KEY`       │ ❌ No        │ ❌ No        │ ✅ Yes       │
├────────────────────────┼─────────────┼─────────────┼─────────────┤
│ `AWS_PERSONALIZE_BUCKET`│ ❌ No        │ ❌ No        │ ✅ Yes       │
├────────────────────────┼─────────────┼─────────────┼─────────────┤
│ `GEMINI_API_KEY`       │ ❌ No        │ ❌ No        │ ⚠️  Optional  │
└────────────────────────┴─────────────┴─────────────┴─────────────┘

---

## 1. Meta API Credentials

### 1.1 META_AD_ACCOUNT_ID
1.  Go to the [Meta Business Suite](https://business.facebook.com/).
2.  Navigate to **Settings > Ad Accounts**.
3.  **Required Role**: You must be an **Admin** of the Ad Account to create Custom Audiences via API.
4.  Copy the ID for your specific Ad Account. It is a long string of numbers (e.g., `1475686827393876`).
5.  **Note**: Do NOT include the `act_` prefix in your `.env` file.

### 1.2 META_ACCESS_TOKEN
To synchronize donors, you need a **System User** token with specific permissions:
1.  Go to the [Meta Events Manager](https://www.facebook.com/events_manager2/list/dataset/).
2.  Select your **Data Plus** or **Dataset**.
3.  Go to **Settings** and scroll down to **Conversions API**.
4.  Click **Generate Access Token** under "Set up manually".
5.  Ensure your token has the **`ads_management`** and **`ads_read`** permissions.
6.  **Security**: This token is long-lived. Store it only in your `.env` file and never commit it to Git.

---

## 2. AWS Configuration

### 2.1 AWS_ACCESS_KEY_ID & SECRET_ACCESS_KEY
1.  Log in to the [AWS Console](https://console.aws.amazon.com/).
2.  Navigate to **IAM > Users**.
3.  Select your user (or create a new one for this toolkit).
4.  Go to the **Security Credentials** tab and click **Create access key** (select "CLI").
5.  **Permissions Required**: Attach the following inline policy to the user:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:ListBucket",
                "personalize:CreateDatasetImportJob"
            ],
            "Resource": [
                "arn:aws:s3:::YOUR_BUCKET_NAME",
                "arn:aws:s3:::YOUR_BUCKET_NAME/*",
                "*"
            ]
        }
    ]
}
```

### 2.2 AWS_PERSONALIZE_BUCKET
1.  Navigate to **S3** in the AWS Console.
2.  Click **Create bucket**.
3.  Give it a unique name (e.g., `my-nonprofit-ml-data`).
4.  Ensure "Block all public access" is checked for security.

---

## 3. Gemini AI Extraction

### 3.1 GEMINI_API_KEY
1.  Visit the [Google AI Studio](https://aistudio.google.com/app/apikey).
2.  Click **Create API Key**.
3.  Copy the key (starts with `AIza...`).
4.  This key is used to personalize the WhatsApp bot conversations based on the donor's inferred interests.

---

## 4. Pre-Flight Validation (.env Check)
Before attempting a live synchronization, use the built-in validation tool to ensure your `.env` is loaded correctly and keys have the right format.

```bash
# Verify Meta configuration
python3 meta_growth_engine.py --dry-run
```
*If this prints "[DRY-RUN] Would create audience," your Meta credentials are valid. If it prints a ValueError, check your .env file names.*

---

## 5. Step-by-Step Walkthrough for First-Time Users

### Step 1: The Virtual Sandbox
Before spending any money, we create "Fake" data that looks like your real donors.
```bash
# Generate 500 potential donors
python3 generate_datasets.py --count 500 --bias-ratio 0.10
```

### Step 2: The Signal Check
We check if the data has a strong enough pattern for an AI to learn.
```bash
python3 uncover_signal_no_pandas.py datasets/large_nonprofit_interactions.csv
```
*Expected Output*: You should see a "SIGNAL DETECTED" message. This proves that if you train an AI on this data, it will actually be able to make smart recommendations.

### Step 3: Meta Sync (Safety First)
We send the "High Value" donor list to Meta to find a "Lookalike" audience.
```bash
python3 meta_growth_engine.py --dry-run
```

### Step 4: S3 Synchronization
Finally, we move the data to Amazon S3 so you can click "Train" in the Amazon Personalize console.
```bash
python3 personalize_sync.py --s3-path my_nonprofit/v1/interactions.csv
```

---

## 🛠 Troubleshooting Credentials
- **Permissions**: If you get a `403 Forbidden`, your Meta Token likely lacks `ads_management`.
- **Invalid Key**: If you get an `AccessDenied`, double-check that your IAM User has the `S3FullAccess` policy attached in the AWS Console.
