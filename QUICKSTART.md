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
Generate 2,000 donors with a 25% bias ratio (for Group A signal density).
```bash
python3 generate_datasets.py --count 2000 --bias-ratio 0.25
```
*Note: --bias-ratio 0.25 means 25% of users receive biased preferences. This is independent of the loyalty tier distribution.*

### 3. Validate Signal
Verify that the behavioral bias is strong enough for machine learning. 
*Note: This manual step allows you to verify data quality locally. The automated Lambda handler performs this same check internally before every synchronization.*
```bash
python3 uncover_signal_no_pandas.py datasets/large_nonprofit_interactions.csv
```

### 4. Upload to Meta (Dry Run)
Test the Meta sync logic safely. This validates your `.env` configuration and hashes PII locally without making any external network requests.
```bash
python3 meta_growth_engine.py --audience-name "nonprofit_vips_test" --dry-run
```

### 4a. Production Sync (Live)
Remove the `--dry-run` flag to create actual Meta Custom Audiences. This will make the audiences visible in your Meta Ad Manager.
```bash
python3 meta_growth_engine.py --audience-name "Donor VIPs Fall 2026"
```
*Note: This will create an audience object but will not incur any ad spend until you manually create a campaign targeting this audience.*

### 5. Sync to AWS Personalize
Upload your interactions to S3 and trigger a Personalize Import Job. **(Requires AWS Credentials in .env)**
```bash
# Basic upload only
python3 personalize_sync.py --dataset datasets/large_nonprofit_interactions.csv

# Upload AND trigger import (requires ARNs)
python3 personalize_sync.py \
  --dataset datasets/large_nonprofit_interactions.csv \
  --dataset-arn "arn:aws:personalize:..." \
  --role-arn "arn:aws:iam:..."
```

---

### ✅ Success Criteria
- **Validation**: "SIGNAL DETECTED" message appears with >20% shift intensity.
- **Meta Sync**: "SUCCESS: Batch 1 synchronized" appears in logs.
- **S3 Sync**: "SUCCESS: File uploaded to S3" appears in logs.
