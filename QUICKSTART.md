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
Generate 1,000 donors with a 15% bias ratio (for Group A signal density).
```bash
python3 generate_datasets.py --count 1000 --bias-ratio 0.15
```

### 3. Validate Signal
Verify that the behavioral bias is strong enough for machine learning.
```bash
python3 uncover_signal_no_pandas.py aws_nonprofit_toolkit/datasets/large_nonprofit_interactions.csv
```

### 4. Upload to Meta (Dry Run)
Test the Meta sync logic safely. This validates your `.env` configuration and hashes PII locally without making any external network requests.
```bash
python3 meta_growth_engine.py --audience-name "nonprofit_vips_test" --dry-run
```

### 🚀 Transition to Live Sync
Once the dry run succeeds and you have verified the hashed data counts, remove the `--dry-run` flag to create a **Real Custom Audience** on Meta:
```bash
python3 meta_growth_engine.py --audience-name "Donor VIPs Fall 2026"
```
*Note: This will incur no ad spend, but will create an audience object in your Meta Ads Manager.*

### 5. Sync to AWS Personalize
Upload your interactions to S3 and trigger a Personalize Import Job. **(Requires AWS Credentials in .env)**
```bash
# Basic upload only
python3 personalize_sync.py --dataset aws_nonprofit_toolkit/datasets/large_nonprofit_interactions.csv

# Upload AND trigger import (requires ARNs)
python3 personalize_sync.py \
  --dataset aws_nonprofit_toolkit/datasets/large_nonprofit_interactions.csv \
  --dataset-arn "arn:aws:personalize:..." \
  --role-arn "arn:aws:iam:..."
```

---

### ✅ Success Criteria
- **Validation**: "SIGNAL DETECTED" message appears with >10% shift intensity.
- **Meta Sync**: "SUCCESS: Batch 1 synchronized" appears in logs.
- **S3 Sync**: "SUCCESS: File uploaded to S3" appears in logs.
