# Test Suite Overview

This directory contains the automated test suite for the AWS Nonprofit Toolkit.

---

## 🛡 Security & Mocking
The test suite is designed for **100% offline execution**. 
*   **No Real API Calls**: All calls to the Meta Graph API (via `requests`) and AWS Services (via `boto3`) are fully mocked using `unittest.mock` and `responses`.
*   **Sandbox Safety**: You can run these tests without providing any real credentials in your `.env` file. The suite uses "fake" tokens for validation.

---

## 🔄 End-to-End Coverage (`test_e2e_flow.py`)
Our primary verification script simulates the entire nonprofit growth lifecycle:
1.  **Generate**: Creates synthetic CSV donors.
2.  **Validate**: Runs the streaming analysis to detect the interest "Bulge."
3.  **Sync (Meta)**: Mocks the batch upload of VIPs to Custom Audiences.
4.  **Sync (AWS)**: Mocks the upload of interactions to Amazon S3.

---

## 🛠 Running the Tests
Ensure you have `pytest` and `responses` installed, then run:
```bash
PYTHONPATH=. pytest aws_nonprofit_toolkit/tests/
```
