# AWS Nonprofit Toolkit

A suite of data simulation and marketing tools designed to optimize donor acquisition funnels using AWS services and Meta's Lookalike Audiences.

---

## 🚀 Key Features

### 1. Behavioral Bias Simulation (Amazon Personalize Ready)
Generate high-signal donor datasets specifically formatted for **Amazon Personalize**.
*   **Location**: `generate_datasets.py`
*   **Method**: Splits users into Group A/B and injects a 70% weighted distribution toward specific causes (e.g., Clean Water).
*   **Verification**: Use `uncover_signal_no_pandas.py` to detect statistical "bulges" in donor interests.
*   **AWS Sync**: Use `personalize_sync.py` to upload these datasets to Amazon S3 and trigger Personalize Import Jobs.

### 2. Meta Growth Engine
Automate the integration with Meta's Custom and Lookalike Audience APIs.
*   **Location**: `meta_growth_engine.py`
*   **Flow**: Extract VIP donors -> SHA256 Hash -> Upload to Meta -> Simulate Lookalike growth.

### 3. Strategy & Governance Documentation
*   **[MARKETING_STRATEGY.md](MARKETING_STRATEGY.md)**: Deep dive into simulation methodologies and growth loops.
*   **[VALIDATION.md](VALIDATION.md)**: Mathematical success criteria and empirical test results.
*   **[COMPLIANCE.md](COMPLIANCE.md)**: Data handling standards and production readiness roadmap.

---

## 🛠 Installation & Setup

### Requirements
*   Python 3.11+
*   Meta Graph API Tokens (for live uploads)
*   AWS Credentials (for Amazon Personalize integration)

### Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 📂 Project Structure
*   `datasets/`: Generated CSV files for simulation.
*   `generate_datasets.py`: Data generation logic.
*   `uncover_signal_no_pandas.py`: Lightweight statistical analysis tool.
*   `meta_growth_engine.py`: Meta API integration script.
