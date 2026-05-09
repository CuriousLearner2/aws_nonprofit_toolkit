# Comprehensive Setup & Credential Guide

This guide will walk you through obtaining the necessary credentials to run the **AWS Nonprofit Toolkit** and move from synthetic data to live marketing synchronization.

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

### 1.2 META_ACCESS_TOKEN
To synchronize donors, you need a **System User** token with specific permissions:
1.  Go to the [Meta Events Manager](https://www.facebook.com/events_manager2/list/dataset/).
2.  Select your **Data Plus** or **Dataset**.
3.  Go to **Settings** and scroll down to **Conversions API**.
4.  Click **Generate Access Token** under "Set up manually".
5.  Ensure your token has the **`ads_management`** and **`ads_read`** permissions.

---

## 2. AWS Configuration

### 2.1 AWS_ACCESS_KEY_ID & SECRET_ACCESS_KEY
1.  Log in to the [AWS Console](https://console.aws.amazon.com/).
2.  Navigate to **IAM > Users**.
3.  Select your user (or create a new one for this toolkit).
4.  Go to the **Security Credentials** tab and click **Create access key** (select "CLI").

### 2.2 AWS_PERSONALIZE_BUCKET
1.  Navigate to **S3** in the AWS Console.
2.  Click **Create bucket**.
3.  Give it a unique name (e.g., `my-nonprofit-ml-data`).

---

## 3. Gemini AI Extraction

### 3.1 GEMINI_API_KEY
1.  Visit the [Google AI Studio](https://aistudio.google.com/app/apikey).
2.  Click **Create API Key**.
3.  This key is used to personalize donor engagement communications based on inferred interests.

---

## 4. Step-by-Step Walkthrough for First-Time Users

### Step 1: The Virtual Sandbox
Before spending any money, we create "Fake" data that looks like your real donors.
```bash
# Generate 2,000 potential donors
python3 generate_datasets.py --count 2000 --bias-ratio 0.25
```

### Step 2: The Signal Check
We check if the data has a strong enough pattern for an AI to learn.
```bash
python3 uncover_signal_no_pandas.py datasets/large_nonprofit_interactions.csv
```

### Step 3: Meta Sync (Safety First)
We send the "High Value" donor list to Meta to find a "Lookalike" audience.
```bash
python3 meta_growth_engine.py --dry-run
```

### Step 4: S3 Synchronization
Finally, we move the data to Amazon S3 so you can click "Train" in the Amazon Personalize console.
```bash
python3 personalize_sync.py --dataset datasets/large_nonprofit_interactions.csv
```
