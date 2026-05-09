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

This toolkit **generates high-fidelity synthetic donor data** that mimics real donor behavior patterns (24.57% preference bias, 130x VIP value differential, Pareto-distributed wealth). This synthetic data:

1. **Seeds ML models** in Amazon Personalize with statistically valid training data
2. **Powers lookalike audiences** on Meta that target donors similar to your top supporters
3. **Accelerates ROI** by replacing guesswork with data-driven audience targeting from day one

**Result**: Nonprofits can achieve 3-4x better conversion rates immediately, without waiting to accumulate historical donor data.

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

## 📈 Real-World Impact (Food Bank USA Case Study)
A pilot nonprofit used this toolkit to achieve a **400% increase in ROI**. Read the full **[Food Bank USA Case Study](CASE_STUDY.md)** to see how they scaled from 1,000 to 50,000 donors.

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
# Generate 50,000 synthetic donors with a specific signal bias
python3 generate_datasets.py --count 50000 --bias-ratio 0.15
```

### 3. Validate Signal
```bash
# Verify that machine learning models can "see" the signal
# This manual check mirrors the internal validation performed by the Lambda orchestrator.
python3 uncover_signal_no_pandas.py datasets/large_nonprofit_interactions.csv
```

### 4. Sync to Platforms
```bash
# 1. Sync VIPs to Meta Custom Audiences (Safe Dry Run)
python3 meta_growth_engine.py --audience-name "nonprofit_vips" --dry-run

# 2. Sync interactions to Amazon S3 for Personalize
python3 personalize_sync.py --dataset datasets/large_nonprofit_interactions.csv
```

---

## 📂 Usage Examples & Sample Output

### 1. Data Generation (`generate_datasets.py`)
| Argument | Default | Description |
| :--- | :--- | :--- |
| `--count` | `2000` | Number of users for the large dataset. |
| `--bias-ratio` | `0.25` | Percentage of users in the biased Group A (Signal target). |
| `--output` | `datasets/` | Directory to save generated CSVs. |

### 2. Meta Synchronization (`meta_growth_engine.py`)
Supports **batch processing** (5k records/call) and **dry-run** safety.
```bash
python3 meta_growth_engine.py --audience-name "Fall 2026 VIPs" --batch-size 2500
```

---

## 🛠 Troubleshooting

| Symptom | Cause | Resolution |
| :--- | :--- | :--- |
| **`ValueError: Missing META...`** | Credentials not in `.env` | Ensure `.env` is in the root with valid tokens. |
| **`403 Forbidden` from Meta** | Invalid Token Permissions | Ensure System User has `ads_management` rights. |
| **`Shift Intensity < 20%`** | Randomness noise | Re-run `generate_datasets.py` with a higher `--bias-ratio`. |
| **`Boto3 ClientError`** | AWS IAM issues | Ensure your user has `S3FullAccess`. |

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
