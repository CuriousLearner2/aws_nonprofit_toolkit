# ⚡ Quick Start Guide

Follow these steps to get the AWS Nonprofit Toolkit running in under 5 minutes.

---

### 1. Set up Credentials
Create a `.env` file in the toolkit directory:
```bash
cp .env.example .env
# Open .env and add your META_ACCESS_TOKEN, META_AD_ACCOUNT_ID, and AWS keys.
```

### 2. Generate Synthetic Donors
Generate 1,000 donors with a 15% VIP ratio (for Group A bias).
```bash
python3 generate_datasets.py --count 1000 --vip-ratio 0.15
```

### 3. Validate Signal
Verify that the behavioral bias is strong enough for machine learning.
```bash
python3 uncover_signal_no_pandas.py aws_nonprofit_toolkit/datasets/large_nonprofit_interactions.csv
```

### 4. Upload to Meta (Dry Run)
Test the Meta sync without creating a real audience.
```bash
python3 meta_growth_engine.py --audience-name "nonprofit_vips_test" --dry-run
```

### 5. Sync to AWS Personalize
Upload your interactions to S3 to prepare for model training.
```bash
python3 personalize_sync.py --dataset aws_nonprofit_toolkit/datasets/large_nonprofit_interactions.csv --s3-path data/donors_v1.csv
```

---

### ✅ Success Criteria
- **Validation**: "SIGNAL DETECTED" message appears with >10% shift intensity.
- **Meta Sync**: "SUCCESS: Batch 1 synchronized" appears in logs.
- **S3 Sync**: "SUCCESS: File uploaded to S3" appears in logs.
