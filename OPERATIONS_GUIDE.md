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
*   **Seed Size Requirement**: Meta recommends 100+ VIP donors for optimal Lookalike stability. The toolkit will warn if fewer are found.
*   **Why**: Meta's Value-Based Lookalikes require a clear wealth concentration to find high-value "twins."
*   **Resolution**: If the sync fails with `WEAK SEED SIGNAL`, increase the `SMALL_USER_COUNT` in `config.py` or adjust the `LOYALTY_DISTRIBUTION` weights.

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

## 4. Monitoring & Observability
Once deployed, use **Amazon CloudWatch** to track the health of your automated synchronization.

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
