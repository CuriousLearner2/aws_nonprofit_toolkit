# Operations & Deployment Guide

This guide provides instructions for deploying the **AWS Nonprofit Toolkit** in a production-ready AWS environment and managing ongoing operations.

---

## 1. Automated Deployment (AWS SAM)
The toolkit includes an **AWS SAM (Serverless Application Model)** template (`template.yaml`) that provisions the core infrastructure with built-in reliability and monitoring.

### 1.1 Provisions Infrastructure
When deployed via `sam deploy`, the template creates:
*   **AWS Lambda Engine**: Orchestrates data generation, validation, and synchronization.
*   **Daily Schedule**: Runs automatically every 24 hours via Amazon EventBridge.
*   **Reliability (DLQ)**: A **Dead Letter Queue (SQS)** to capture failed runs for manual replay.
*   **CloudWatch Alarms**: Automated alerts for Lambda failures and SQS queue depth.

### 1.2 Deployment Steps
1.  **Navigate to toolkit**: `cd aws_nonprofit_toolkit`
2.  **Build**: `sam build`
3.  **Deploy**: `sam deploy --guided`
    *   **Stack Name**: `nonprofit-toolkit`
    *   **Parameters**: Provide your Meta and S3 credentials when prompted.

---

## 2. Validation & Signal Audit
The toolkit performs automated quality checks before every data synchronization. If a signal is too weak, the sync will abort to prevent training models on poor data.

### 2.1 Track 1: Meta Seed Audit (Pareto Principle)
*   **Check**: Does the top 10% of donors represent >60% of total value?
*   **Seed Size Requirement**: **Mandatory:** You must provide at least **100 VIP donors**. The toolkit will abort the synchronization if fewer than 100 VIPs are detected, as Meta cannot generate stable Lookalike audiences with smaller seeds.
*   **Why**: Meta's Value-Based Lookalikes require a statistically significant number of high-value "twins" to match characteristics.
*   **Resolution**: If the sync fails with `WEAK SEED SIGNAL`, increase your donor list size or adjust the `LOYALTY_LEVEL` labels in your CSV.

### 2.2 Audience Synchronization (Polling & Match Rate)
*   **Process**: After uploading donors, the toolkit polls the audience status every 10 minutes for up to one hour.
*   **Verification**: The sync waits for a `Ready` status and verifies that the `match_rate` (approximate_count / uploaded_count) is > 40%.
*   **Failure**: If the match rate is < 40%, lookalike creation is aborted as the list is considered too stale or corrupted.

---

## 3. Pipeline Verification & Troubleshooting

Use the `verify_pipeline.py` script to check sandbox status and verify your pipeline is ready for ad targeting.

### 3.1 Quick Verification

```bash
cd aws_nonprofit_toolkit
python3 verify_pipeline.py
```

### 3.2 What the Verification Script Checks

The script performs **6 verification steps**:

1. **Credentials** - Validates that `META_ACCESS_TOKEN`, `META_SANDBOX_AD_ACCOUNT_ID`, and `META_AD_ACCOUNT_ID` are set in `.env`
2. **Token Validity** - Tests the access token against Meta's Debug API
3. **Sandbox Account** - Confirms the sandbox account is ACTIVE
4. **List Audiences** - Shows all audiences in your sandbox with:
   - Status (READY, BUILDING, PAUSED)
   - Type (CUSTOM seed vs LOOKALIKES)
   - Approximate user count
   - Creation timestamp
5. **Seed Audience Verification** - Checks if your seed audience:
   - Has status = READY
   - Has matched donors > 0
   - Shows match rate percentage
6. **Lookalike Verification** - Checks if your lookalike:
   - Has status = READY
   - Has sufficient size for ad targeting (100k+ users recommended)
   - Is ready for campaigns

### 3.3 Verification Workflow

**Before running the pipeline:**
```bash
python3 verify_pipeline.py
```
Ensures credentials are valid and sandbox account is accessible.

**After running the pipeline:**
```bash
python3 verify_pipeline.py
```
Confirms audiences were created and have reached READY status with acceptable match rates.

**Before launching ads:**
```bash
python3 verify_pipeline.py
```
Final check that lookalike audience is READY and has sufficient size for ad targeting.

### 3.4 Understanding the Output

**Success Indicators:**
- ✅ All credential checks pass
- ✅ Token is valid
- ✅ Sandbox account is ACTIVE
- ✅ Seed audience: Status = READY, Size > 0, Match rate >= 40%
- ✅ Lookalike audience: Status = READY, Size > 100,000 users

**When you see:** `Pipeline Status: READY FOR AD TARGETING` → You can launch campaigns

**Common Issues:**
- ❌ Token validation fails → Generate new System User token in Meta Events Manager
- ❌ Account not ACTIVE → Check your sandbox account ID and permissions
- ❌ No audiences found → Run the pipeline with `--create-lookalike` flag
- ❌ Match rate < 40% → Email list may be stale; re-upload with fresh data
- ❌ Lookalike size too small → Seed audience too small; increase VIP donor count

---

## 3.5 Running the Full Pipeline (Step-by-Step for Beginners)

This section walks you through running the donor sync pipeline from start to finish.

### Prerequisites

Before starting, make sure you have:

**1. `.env` file with your Meta credentials**
   - **Location:** Inside the `aws_nonprofit_toolkit` folder (the main toolkit directory)
   - **File name:** `.env` (starts with a dot)
   - **Contents:** Should have `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID`, `META_SANDBOX_AD_ACCOUNT_ID`
   - **How to create:** Run `cp .env.example .env` in the toolkit directory and edit it with your credentials
   - **Important:** This file is private - never upload it to GitHub or share it

**2. A CSV file with your donor data**
   - For testing: Use `tests/fixtures/test_donors.csv` (already included)
   - For real data: Upload your donor CSV file to the toolkit folder
   - **Required columns:** EMAIL, LOYALTY_LEVEL, LTV

**3. Terminal/Command Prompt**
   - Mac: Use "Terminal" app
   - Windows: Use "Command Prompt" or "PowerShell"

**4. Your sandbox account ID**
   - This is the number you set in the `.env` file as `META_SANDBOX_AD_ACCOUNT_ID`
   - You got this from Meta Business Suite (Settings → Ad Accounts)

### Step 1: Open Your Terminal

1. Open Terminal (Mac) or Command Prompt (Windows)
2. Navigate to the toolkit folder:
   ```bash
   cd aws_nonprofit_toolkit
   ```

### Step 2: Verify Everything is Ready

Before running the full pipeline, check that your credentials are set up correctly:
```bash
python3 verify_pipeline.py
```

You should see:
- ✅ `META_ACCESS_TOKEN: EAAc...` (masked token)
- ✅ `META_SANDBOX_AD_ACCOUNT_ID: 1665...` (your sandbox ID)
- ✅ `Token is valid`

**If you see errors:** Check that your `.env` file is in the `aws_nonprofit_toolkit` folder and has the correct values.

### Step 3: Run the Pipeline

Run this command (all on one line):
```bash
python3 -m aws_nonprofit_toolkit.meta_growth_engine \
  --sandbox \
  --audience-name "My_Donor_Audience" \
  --users-file tests/fixtures/test_donors.csv \
  --create-lookalike
```

**What each part means:**
- `--sandbox` = Use your sandbox account (safe for testing)
- `--audience-name` = Name for your donor audience (you can change "My_Donor_Audience")
- `--users-file` = Path to your CSV file with donors
- `--create-lookalike` = Automatically create a lookalike audience

### Step 4: Watch for Success Messages

As the pipeline runs, you'll see messages like:
```
✅ Creating Custom Audience 'My_Donor_Audience'...
✅ Audience is ready for upload.
✅ Batch 1 synced (4 emails).
✅ Uploaded 4 VIP donors.
✅ Audience is ready for lookalike creation after 0 seconds
```

**If you see errors**, check the "Troubleshooting" section below.

### Step 5: Wait for Meta to Process

After upload, the pipeline polls Meta every 10 minutes to check if your audience is ready for lookalike creation. **This is normal.** Meta takes 5-30 minutes to process in the sandbox.

The pipeline will:
1. Upload your donors (takes a few seconds)
2. Check audience status (every 10 minutes)
3. Create a lookalike when ready (automatically)

**You can monitor progress two ways:**

**Option A - Let it run:**
Just leave the terminal open. The pipeline will complete automatically and show a success message.

**Option B - Check status manually:**
Open a new terminal and run:
```bash
python3 verify_pipeline.py
```
Look for your audience name. You'll see:
- ⏳ Status: "Updating" = Still processing
- ✅ Status: "Normal" = Ready (lookalike will be created next)

### Step 6: Verify in Meta Ads Manager

Once the pipeline completes, check [Meta Ads Manager](https://adsmanager.facebook.com):

1. Click **Audiences** (left sidebar)
2. Look for two audiences:
   - 🌱 `My_Donor_Audience` (your seed audience with your donors)
   - 🎯 Lookalike version (automatically created, ~150k prospects)

**Both should show status: Ready**

### Step 7: Launch Your First Campaign

Once you see both audiences in Meta Ads Manager:

1. Create a new campaign in Meta Ads Manager
2. Go to **Audience** section
3. Select your lookalike audience (the one with 🎯 icon)
4. Set your budget and launch!

### Troubleshooting

**"Failed to fetch audiences"**
- **Problem:** Token doesn't have permission
- **Fix:** Check that your System User is added to the sandbox account with Admin role

**"Invalid hash"**
- **Problem:** Email format is wrong in your CSV
- **Fix:** Make sure your CSV has columns: EMAIL, LOYALTY_LEVEL, LTV
- **Fix:** Emails should be lowercase (the code does this automatically)

**"Audience failed to reach uploadable status"**
- **Problem:** Meta sandbox is taking longer than usual
- **Fix:** Wait and run verification script again
- **Fix:** Try again in 15 minutes

**"No audiences found"**
- **Problem:** Pipeline hasn't run yet or failed silently
- **Fix:** Check error messages in the terminal output
- **Fix:** Run with smaller test file first

---

## 4. Track 2: Personalization (Retention)
Now that we've found new donors, this track uses machine learning to keep them engaged for the long term.

1.  **Prepare Your Data**: Ensure your donor interaction file (clicks, opens, donations) is saved as `aws_nonprofit_toolkit/datasets/large_nonprofit_interactions.csv`.
2.  **Send to AWS**: Run the tool to upload this file to your secure AWS folder (the "bucket"):
    ```bash
    python3 personalize_sync.py --dataset aws_nonprofit_toolkit/datasets/large_nonprofit_interactions.csv
    ```
3.  **Start Training**: Once uploaded, log into the [AWS Personalize Console](https://console.aws.amazon.com/personalize/). Select your "Solution" and click **Train**. This tells the AI to learn the unique donor patterns for your organization.
4. **Identify Archetypes**: Once training is complete, the AI can categorize donors. Run the segmentation tool to get your donor segments:
    ```bash
    python3 aws_nonprofit_toolkit/personalize_segmentation.py --user-id USER_ID --campaign-arn YOUR_CAMPAIGN_ARN
    ```
    *   **USER_ID**: The ID of the donor you want to segment.
    *   **CAMPAIGN_ARN**: The Amazon Resource Name (ARN) of your trained Personalize Campaign.

5.  **Targeted Engagement**: Use these segments to send personalized emails or newsletters based on what each donor likes (e.g., "Eco-Conscious" vs. "Emergency Relief").

### 4.1 Alarms and Notifications
The system is pre-configured with two critical alarms:
1.  **LambdaErrorAlarm**: Triggers if the sync fails.
2.  **DLQDepthAlarm**: Triggers if a failure is persistent and requires manual intervention.
*Note: You must manually subscribe your email to an SNS Topic to receive these alerts.*

---

## 5. Credential Management Protocol
To maintain security, organizations should follow this manual rotation protocol every 90 days.

### 5.1 Manual Rotation Protocol (User-Executed)
1.  **Generate New Key**: Create a new token in Meta Events Manager or AWS IAM.
2.  **Update Config**: Update the environment variables in the Lambda configuration or AWS Secrets Manager.
3.  **Verify**: Run a `meta_growth_engine.py --dry-run` locally to ensure the new key is valid.
4.  **Revoke Old Key**: Once verified, delete the old token from the provider.

---

## 6. Troubleshooting Meta API Errors

| Error Code | Description | Resolution |
| :--- | :--- | :--- |
| `190` | Access Token Expired | Generate a new System User token in Events Manager. |
| `200` | Permission Denied | Ensure the System User has been added to the Ad Account. |
| `400` | Bad Request | Check that the `AD_ACCOUNT_ID` does not contain the `act_` prefix. |
| `100` | Rate Limit Reached | The toolkit will automatically retry with exponential backoff. |
