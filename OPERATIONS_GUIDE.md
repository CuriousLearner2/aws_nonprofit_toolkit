# Operations & Deployment Guide

This guide provides instructions for deploying the AWS Nonprofit Toolkit in a production-ready AWS environment and managing ongoing operations.

---

## 1. Deployment on AWS Lambda
To automate the synchronization of donor data, you can wrap the toolkit scripts in an AWS Lambda function.

### 1.1 Lambda Configuration
*   **Runtime**: Python 3.11+
*   **Trigger**: AWS EventBridge (Scheduled Rule) - e.g., every 24 hours.
*   **Environment Variables**: Upload your `.env` values to the Lambda Configuration tab.
*   **Layers**: You will need to create a Lambda Layer containing the dependencies in `requirements.txt` (`requests`, `tenacity`, `boto3`, etc.).

### 1.2 Execution Logic
Your Lambda handler should follow the standard workflow:
1.  Initialize `SimulationConfig`.
2.  Call `generate_datasets.py` logic.
3.  Execute `meta_growth_engine.py` and `personalize_sync.py` functions.

---

## 2. Monitoring & Observability
Use **Amazon CloudWatch** to track the health of your automated synchronization.

### 2.1 CloudWatch Logs
*   The toolkit uses the Python `logging` module, which automatically streams to CloudWatch Logs when running on Lambda.
*   **Filter Pattern**: Create a metric filter for the term `ERROR` or `CRITICAL` to track failed batches.

### 2.2 CloudWatch Alarms
*   Set up an SNS notification to alert your marketing team if the error rate exceeds 5% in a single run.

---

## 3. Credential Rotation
To maintain security, rotate your API keys every 90 days.

### 3.1 Rotation Protocol
1.  **Generate New Key**: Create a new token in Meta Events Manager or AWS IAM.
2.  **Update Config**: Add the new key to your environment variables.
3.  **Verify**: Run a `meta_growth_engine.py --dry-run` to ensure the new key is active.
4.  **Revoke Old Key**: Once verified, delete the old token from the provider.

---

## 4. Troubleshooting Meta API Errors

| Error Code | Description | Resolution |
| :--- | :--- | :--- |
| `190` | Access Token Expired | Generate a new System User token in Events Manager. |
| `200` | Permission Denied | Ensure the System User has been added to the Ad Account. |
| `400` | Bad Request | Check that the `AD_ACCOUNT_ID` does not contain the `act_` prefix. |
| `100` | Rate Limit Reached | The toolkit will automatically retry with exponential backoff. |
