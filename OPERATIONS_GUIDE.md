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

## 3. Monitoring & Observability
Once deployed, use **Amazon CloudWatch** to track the health of your automated synchronization.

### 2.1 Alarms and Notifications
The system is pre-configured with two critical alarms:
1.  **LambdaErrorAlarm**: Triggers if the sync fails.
2.  **DLQDepthAlarm**: Triggers if a failure is persistent and requires manual intervention.
*Note: You must manually subscribe your email to an SNS Topic to receive these alerts.*

---

## 3. Credential Management Protocol
To maintain security, organizations should follow this manual rotation protocol every 90 days.

### 3.1 Manual Rotation Protocol (User-Executed)
1.  **Generate New Key**: Create a new token in Meta Events Manager or AWS IAM.
2.  **Update Config**: Update the environment variables in the Lambda configuration or AWS Secrets Manager.
3.  **Verify**: Run a `meta_growth_engine.py --dry-run` locally to ensure the new key is valid.
4.  **Revoke Old Key**: Once verified, delete the old token from the provider.

---

## 4. Troubleshooting Meta API Errors

| Error Code | Description | Resolution |
| :--- | :--- | :--- |
| `190` | Access Token Expired | Generate a new System User token in Events Manager. |
| `200` | Permission Denied | Ensure the System User has been added to the Ad Account. |
| `400` | Bad Request | Check that the `AD_ACCOUNT_ID` does not contain the `act_` prefix. |
| `100` | Rate Limit Reached | The toolkit will automatically retry with exponential backoff. |
