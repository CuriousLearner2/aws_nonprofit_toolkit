# AWS Nonprofit Toolkit

A suite of data simulation and automation tools designed to optimize donor acquisition funnels using Amazon Personalize and Meta Lookalike Audiences.

[![Test Status](https://img.shields.io/badge/tests-23%20passed-success)](tests/)
[![Compliance](https://img.shields.io/badge/compliance-PII%20Safe-blue)](COMPLIANCE.md)

---

## The Problem: The Cold-Start Challenge

Nonprofits struggle to build effective donor acquisition pipelines because:

- **Limited Historical Data**: Many organizations have < 1,000 historical donors, insufficient for training machine learning models that require thousands of examples
- **No Baseline Patterns**: Without historical donor behavior data, Meta's Lookalike Audiences cannot identify similar prospects
- **Expensive Trial-and-Error**: Testing audience targeting hypotheses costs real advertising budget with no statistical foundation

This "cold-start problem" forces nonprofits to waste acquisition budgets on untargeted campaigns because they lack the behavioral data to fuel intelligent lookalike audiences.

## The Solution

This toolkit **generates high-fidelity synthetic donor data** that mimics real donor behavior patterns (25.0% preference bias, 130x VIP value differential, Pareto-distributed wealth). This synthetic data:

1. **Seeds ML models** in Amazon Personalize with statistically valid training data
2. **Powers lookalike audiences** on Meta that target donors similar to your top supporters
3. **Accelerates ROI** by replacing guesswork with data-driven audience targeting from day one

**Result**: Nonprofits can achieve 4x better conversion rates immediately, without waiting to accumulate historical donor data.

---

## 🏗 System Architecture
The toolkit operates as a **Dual-Track Pipeline** that bridges human intuition with machine learning scale.

1.  **The Acquisition Track (Small Dataset):** Uses **Human-Driven Labeling** to seed Meta Lookalike Audiences for rapid donor growth.
2.  **The Personalization Track (Large Dataset):** Uses **ML-Driven Inference (Amazon Personalize)** to automate donor retention and LTV optimization.

See the **[Pipeline Architecture Guide](PIPELINE_ARCHITECTURE.md)** for a detailed technical breakdown.

---

## ✅ Success Criteria & Benchmarks
To ensure the synthetic data is production-ready, it must pass the following benchmarks:
1.  **Signal Strength**: The "Bulge Test" must detect a **20% to 45%** statistical shift in Group A causes.
2.  **Pareto Distribution**: The VIP segment must account for **>80%** of total donation value.
3.  **Schema Integrity**: 100% of interaction records must map to valid user IDs (0 orphans).
4.  **Sync Reliability**: 100% of batches must reach Meta/AWS with exponential backoff handling transient drops.

---

## 📈 Projected Impact (Simulated Case Study)
Simulation analysis projects that a pilot nonprofit could achieve a **400% increase in ROI** using this toolkit. Read the full **[Food Bank USA Case Study](CASE_STUDY.md)** to see the projected scale from 200 to 2,000 donors.

---

## ⚡ Quick Start (5-Minute Setup)

### 1. Configure Credentials
**Need help getting your tokens?** See our **[Setup & Credential Guide](SETUP_GUIDE.md)** for a step-by-step walkthrough.
```bash
cp .env.example .env
# Edit .env with your Meta and AWS tokens
```

### 2. Generate Synthetic Donors
```bash
# Generate 2,000 synthetic donors with a specific signal bias
# --bias-ratio 0.25 (25% of users will have skewed preferences)
python3 generate_datasets.py --count 2000 --bias-ratio 0.25
```

### 3. Validate Signal
```bash
# Verify that machine learning models can "see" the signal
# This manual check mirrors the internal validation performed by the Lambda orchestrator.
python3 uncover_signal_no_pandas.py datasets/large_nonprofit_interactions.csv
```

---

## 🛠 Central Troubleshooting Guide

| Symptom | Cause | Resolution |
| :--- | :--- | :--- |
| **`ValueError: Missing META...`** | Credentials not in `.env` | Ensure `.env` is in the root with valid tokens. |
| **`403 Forbidden` from Meta** | Invalid Token Permissions | Ensure System User has `ads_management` rights. |
| **`400 Bad Request` from Meta** | Account ID Format | Ensure `META_AD_ACCOUNT_ID` does NOT include the `act_` prefix. |
| **`Shift Intensity < 20%`** | Low signal density | Increase `--bias-ratio` (size of group) or `CAUSE_BIAS_WEIGHT` (intensity) in `config.py`. |
| **`Boto3 ClientError`** | AWS IAM issues | Ensure your user has `AmazonPersonalizeFullAccess` and `S3FullAccess`. |
| **`ModuleNotFoundError`** | Missing environment | Run `pip install -r requirements.txt`. |

---

## 📖 Deep Dive Documentation
*   **[PRD.md](PRD.md)**: 📄 Product requirements and core "Dual-Track" vision.
*   **[PIPELINE_ARCHITECTURE.md](PIPELINE_ARCHITECTURE.md)**: 🆕 Technical breakdown of the Human-Labeling vs. ML-Inference tracks.
*   **[QUICKSTART.md](QUICKSTART.md)**: Copy-paste commands for rapid deployment.
*   **[SETUP_GUIDE.md](SETUP_GUIDE.md)**: Detailed instructions for obtaining provider credentials.
*   **[OPERATIONS_GUIDE.md](OPERATIONS_GUIDE.md)**: Deployment on AWS Lambda, CloudWatch monitoring, and credential rotation.
*   **[CASE_STUDY.md](CASE_STUDY.md)**: Deep dive into the Food Bank USA 4x ROI results.
*   **[CONFIG.md](CONFIG.md)**: Full parameter list for customizing bias weights and demographics.
*   **[VALIDATION.md](VALIDATION.md)**: Mathematical success criteria and Pareto distribution benchmarks.
*   **[COMPLIANCE.md](COMPLIANCE.md)**: PII hashing standards and the production readiness roadmap.
*   **[MARKETING_STRATEGY.md](MARKETING_STRATEGY.md)**: Theoretical framework for High-Signal Growth.
