# Comprehensive Setup & Credential Guide

This guide will walk you through obtaining the necessary credentials to run the **AWS Nonprofit Toolkit** and move from synthetic data to live marketing synchronization.

---

## Configuration Requirements Matrix

Use the table below to identify which environment variables are required based on your specific use case.

┌────────────────────────┬─────────────┬─────────────┬─────────────┬─────────────┐
│ Variable               │ Data-Gen    │ Meta-Sync   │ Full AWS    │ Sandbox     │
│                        │ Only        │ Only        │ Pipeline    │ Testing     │
├────────────────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│ `META_ACCESS_TOKEN`    │ ❌ No        │ ✅ Yes       │ ✅ Yes       │ ✅ Yes       │
├────────────────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│ `META_AD_ACCOUNT_ID`   │ ❌ No        │ ✅ Yes       │ ✅ Yes       │ ✅ Yes       │
├────────────────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│ `META_SANDBOX_AD_...`  │ ❌ No        │ ❌ No        │ ❌ No        │ ✅ Optional* │
├────────────────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│ `AWS_ACCESS_KEY_ID`    │ ❌ No        │ ❌ No        │ ✅ Yes       │ ❌ No        │
├────────────────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│ `AWS_SECRET_KEY`       │ ❌ No        │ ❌ No        │ ✅ Yes       │ ❌ No        │
├────────────────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│ `AWS_PERSONALIZE_BUCKET`│ ❌ No        │ ❌ No        │ ✅ Yes       │ ❌ No        │
└────────────────────────┴─────────────┴─────────────┴─────────────┴─────────────┘

*Sandbox Testing: Set this to enable automated lookalike creation. Omit it for production safety mode.

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

## 2. Sandbox Configuration

### 2.1 What is the Sandbox?
The Sandbox is a **safe testing environment** for the Lookalike Audience creation workflow. Use it to:
- Test the full pipeline before Production
- Verify audience creation works with your Meta account
- Experiment with different donor lists without affecting real campaigns

**How it works:**
- If `META_SANDBOX_AD_ACCOUNT_ID` is set → Automated 1% Lookalike creation runs
- If `META_SANDBOX_AD_ACCOUNT_ID` is NOT set → Lookalike creation is skipped (Production safety mode)

### 2.2 Verified Sandbox Account
The project is configured for testing using the verified Sandbox Ad Account.

| Variable | Value | Status |
| :--- | :--- | :--- |
| `META_SANDBOX_AD_ACCOUNT_ID` | `986710934051280` | ✅ Verified Active |

*   **Note**: This account has been successfully tested with the Marketing API using the `is_adset_budget_sharing_enabled=false` parameter.

---

## 3. AWS Configuration

### 3.1 AWS_ACCESS_KEY_ID & SECRET_ACCESS_KEY
1.  Log in to the [AWS Console](https://console.aws.amazon.com/).
2.  Navigate to **IAM > Users**.
3.  Select your user (or create a new one for this toolkit).
4.  Go to the **Security Credentials** tab and click **Create access key** (select "CLI").

### 3.2 AWS_PERSONALIZE_BUCKET
1.  Navigate to **S3** in the AWS Console.
2.  Click **Create bucket**.
3.  Give it a unique name (e.g., `my-nonprofit-ml-data`).

---

## 4. Sandbox to Production Workflow

### Getting Started: Use Sandbox First
For your first run, always use the Sandbox environment:

1. **Set these environment variables:**
   ```bash
   export META_SANDBOX_AD_ACCOUNT_ID=986710934051280
   export META_ACCESS_TOKEN=your_token
   export META_AD_ACCOUNT_ID=your_production_account
   ```

2. **Run the daily pipeline:**
   ```bash
   python3 -m aws_nonprofit_toolkit.lambda_handler
   ```

3. **Verify the results:**
   - Automated 1% Lookalike audience will be created in the Sandbox account
   - Check Meta Business Suite for the "Daily VIP Lookalike (1%)" audience

### Transitioning to Production
Once you've verified the pipeline works:

1. **Remove Sandbox setting:**
   ```bash
   unset META_SANDBOX_AD_ACCOUNT_ID
   ```

2. **Verify Production safety mode:**
   - Lookalike creation will now be skipped automatically
   - Only custom audiences are synced to your production account
   - You can manually create lookalikes in Meta Ads Manager when ready

3. **Schedule with Lambda:**
   - Deploy to AWS Lambda for automated daily runs
   - The safety gate ensures no accidental lookalikes are created in production

---

## 5. Step-by-Step Walkthrough for First-Time Users

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
