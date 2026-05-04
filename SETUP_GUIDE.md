# Comprehensive Setup & Credential Guide

This guide will walk you through obtaining the necessary credentials to run the AWS Nonprofit Toolkit and move from synthetic data to live marketing synchronization.

---

## 1. Meta API Credentials

### 1.1 META_AD_ACCOUNT_ID
1.  Go to the [Meta Business Suite](https://business.facebook.com/).
2.  Navigate to **Settings > Ad Accounts**.
3.  Copy the ID for your specific Ad Account. It is a long string of numbers (e.g., `1475686827393876`).
4.  **Note**: Do NOT include the `act_` prefix in your `.env` file.

### 1.2 META_ACCESS_TOKEN
To synchronize donors, you need a **System User** token with specific permissions:
1.  Go to the [Meta Events Manager](https://www.facebook.com/events_manager2/list/dataset/).
2.  Select your **Data Plus** or **Dataset**.
3.  Go to **Settings** and scroll down to **Conversions API**.
4.  Click **Generate Access Token** under "Set up manually".
5.  Ensure your token has the `ads_management` permission.
6.  **Security**: This token is long-lived. Store it only in your `.env` file and never commit it to Git.

---

## 2. AWS Configuration

### 2.1 AWS_ACCESS_KEY_ID & SECRET_ACCESS_KEY
1.  Log in to the [AWS Console](https://console.aws.amazon.com/).
2.  Navigate to **IAM > Users**.
3.  Select your user (or create a new one for this toolkit).
4.  Go to the **Security Credentials** tab.
5.  Click **Create access key** and select "Command Line Interface (CLI)".
6.  Download the `.csv` containing your Key and Secret.

### 2.2 AWS_PERSONALIZ_BUCKET
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

## 4. Step-by-Step Walkthrough for First-Time Users

### Step 1: The Virtual Sandbox
Before spending any money, we create "Fake" data that looks like your real donors.
```bash
# Generate 500 potential donors
python3 generate_datasets.py --count 500 --vip-ratio 0.10
```

### Step 2: The Signal Check
We check if the data has a strong enough pattern for an AI to learn.
```bash
python3 uncover_signal_no_pandas.py aws_nonprofit_toolkit/datasets/large_nonprofit_interactions.csv
```
*Expected Output*: You should see a "SIGNAL DETECTED" message. This proves that if you train an AI on this data, it will actually be able to make smart recommendations.

### Step 3: Meta Sync (Safety First)
We send the "High Value" donor list to Meta to find a "Lookalike" audience.
```bash
python3 meta_growth_engine.py --dry-run
```
*Why Dry Run?*: This simulates the upload without actually sending data to Meta. Use this to verify your `.env` is loaded correctly.

### Step 4: S3 Synchronization
Finally, we move the data to Amazon S3 so you can click "Train" in the Amazon Personalize console.
```bash
python3 personalize_sync.py --s3-path my_nonprofit/v1/interactions.csv
```

---

## 🛠 Troubleshooting Credentials
- **Permissions**: If you get a `403 Forbidden`, your Meta Token likely lacks `ads_management`.
- **Invalid Key**: If you get an `AccessDenied`, double-check that your IAM User has the `S3FullAccess` policy attached in the AWS Console.
