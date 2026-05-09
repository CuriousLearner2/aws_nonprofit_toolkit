# ⚡ Quick Start Guide

Follow these steps to execute the **Dual-Track Pipeline** strategy.

---

## 1. Setup
Create a `.env` file in the toolkit directory:
```bash
cp .env.example .env
# Open .env and add your META and AWS credentials.
```

---

## 2. Track 1: The Acquisition Track (Donor Growth)
**Goal**: Use a small seed of VIP donors to find millions of new potential supporters via Meta.

1.  **Generate Seed**: Create 2,000 synthetic donors.
    ```bash
    python3 generate_datasets.py --count 2000 --bias-ratio 0.25
    ```
2.  **Sync to Meta (Dry Run)**: Verify your credentials and PII hashing without making a live call.
    ```bash
    python3 meta_growth_engine.py --audience-name "VIP_Seed_Test" --dry-run
    ```
3.  **Sync to Meta (Live)**: Create the audience in your Meta Ad Manager.
    ```bash
    python3 meta_growth_engine.py --audience-name "Donor VIPs Fall 2026"
    ```

---

## 3. Track 2: The Personalization Track (Donor Retention)
**Goal**: Use high-volume behavioral data to train machine learning models for personalized engagement.

1.  **Validate Behavioral Signal**: Verify the "statistical bulge" is strong enough for ML detection.
    ```bash
    python3 uncover_signal_no_pandas.py datasets/large_nonprofit_interactions.csv
    ```
2.  **Sync to AWS Personalize**: Upload the interaction stream to S3 to begin model training.
    ```bash
    python3 personalize_sync.py --dataset datasets/large_nonprofit_interactions.csv
    ```

---

## 4. Summary of Architecture
*   **Track 1 (Meta)**: Uses **Human-Labeling** (VIP tags) to drive acquisition.
*   **Track 2 (AWS)**: Uses **ML-Inference** (Behavioral patterns) to drive personalization.

For a deep dive into the technology, see **[PIPELINE_ARCHITECTURE.md](PIPELINE_ARCHITECTURE.md)**.
