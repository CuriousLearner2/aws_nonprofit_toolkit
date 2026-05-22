# Phase 1: Donor Engagement Validation Workflow

## Overview

Phase 1 validates the AWS Personalize pipeline end-to-end using our small dataset (200 donors, 500 interactions). We implement all three engagement scoring approaches:

- **Option A**: Overall engagement score per donor (0-100)
- **Option B**: Cause-specific recommendations (which causes each donor engages with most)
- **Option C**: Donor segmentation into engagement tiers (High/Medium/Low)

## Data

**Donors**: `datasets/small_nonprofit_users.csv` (200 donors)
- USER_ID, EMAIL, INTEREST_TAG, LTV, LOYALTY_LEVEL, SOURCE, CONSENT

**Interactions**: `datasets/small_nonprofit_interactions.csv` (500 interactions)
- USER_ID, ITEM_ID (cause), TIMESTAMP, EVENT_TYPE (DONATE, VIEW, etc.)

**Causes (ITEM_IDs)**: ENVIRONMENT, EDUCATION, DISASTER_RELIEF, COMMUNITY_HEALTH, etc.

## Workflow

### Step 1: Train Recommender Model (10-15 minutes)

**Script**: `phase1_train_model.py`

Creates and trains an AWS Personalize solution using the `aws-item-affinity` recipe.

```bash
python3 phase1_train_model.py --wait-for-completion
```

**What it does**:
1. Creates a Personalize "solution" (model configuration)
2. Trains a solution version using aws-item-affinity recipe
3. Polls until training completes (ACTIVE status)
4. Returns the solution version ARN

**Output**:
```
Solution ARN: arn:aws:personalize:us-east-1:...:solution/donor-engagement-xxx
Training Job ARN: arn:aws:personalize:us-east-1:...:solution-version/donor-engagement-xxx/xxx
```

**Expected training time**: 10-15 minutes (first run)

---

### Step 2: Run Batch Inference (5 minutes)

**Script**: `phase1_batch_inference.py`

Uses the trained model to score all donors on their engagement with all causes.

```bash
python3 phase1_batch_inference.py arn:aws:personalize:us-east-1:...:solution-version/...
```

**What it does**:
1. Prepares batch input file (one USER_ID per line)
2. Uploads to S3
3. Triggers batch inference job
4. Polls until complete (ACTIVE status)
5. Returns output S3 path

**Output**:
```
Batch results: s3://personalize-sandbox-.../personalize/batch_output/phase1_xxx/
```

**File format**:
```json
{
  "userID": "user_123",
  "output": {
    "recommendations": [
      {"itemId": "ENVIRONMENT", "score": 0.85},
      {"itemId": "EDUCATION", "score": 0.72}
    ]
  }
}
```

---

### Step 3: Extract Segments (2 minutes)

**Script**: `phase1_extract_segments.py`

Analyzes batch results and generates donor segments.

```bash
python3 phase1_extract_segments.py s3://personalize-sandbox-.../personalize/batch_output/phase1_xxx/
```

**What it does**:
1. Downloads batch inference results from S3
2. Parses recommendations per donor
3. **Calculates Option A**: Overall engagement score (0-100)
   - Composite of average score, peak score, and breadth of engagement
4. **Generates Option B**: Cause rankings (top causes per donor)
5. **Segments Option C**: High/Medium/Low engagement tiers

**Segments**:
- **HIGH (80+)**: "Likely Responders" - strong engagement across causes
- **MEDIUM (50-79)**: "Warm Leads" - moderate engagement
- **LOW (<50)**: "Cold Prospects" - weak engagement

**Outputs** (saved locally):
- `phase1_engagement_scores.csv`: USER_ID, ENGAGEMENT_SCORE, SEGMENT
- `phase1_cause_recommendations.csv`: USER_ID, CAUSE_RANK, CAUSE, SCORE
- `phase1_segments.csv`: SEGMENT, COUNT, DONOR_IDS

---

## Full Workflow Command Sequence

```bash
# Terminal 1: Start model training (will take 10-15 min)
python3 phase1_train_model.py --wait-for-completion

# (Training is running... go grab coffee ☕)

# Once training completes, you'll see the Solution Version ARN. Copy it.
# Example: arn:aws:personalize:us-east-1:684039303576:solution-version/donor-engagement-1779412XXX

# Terminal 2: Run batch inference (will take ~5 min)
python3 phase1_batch_inference.py <PASTE-SOLUTION-VERSION-ARN-HERE>

# Once batch inference completes, you'll see the output S3 path:
# Example: s3://personalize-sandbox-.../personalize/batch_output/phase1_1779412XXX/

# Terminal 2: Extract segments (instant)
python3 phase1_extract_segments.py <PASTE-S3-OUTPUT-PATH-HERE>

# View results
cat phase1_engagement_scores.csv
cat phase1_cause_recommendations.csv
cat phase1_segments.csv
```

---

## Expected Results

### Option A: Engagement Scores
```
USER_ID,ENGAGEMENT_SCORE,SEGMENT
user_0,75.2,MEDIUM
user_1,92.1,HIGH
user_2,38.4,LOW
...
```

### Option B: Cause Recommendations
```
USER_ID,CAUSE_RANK,CAUSE,SCORE
user_0,1,ENVIRONMENT,0.823
user_0,2,EDUCATION,0.715
user_1,1,DISASTER_RELIEF,0.945
...
```

### Option C: Segments
```
SEGMENT,COUNT,DONOR_IDS
HIGH,47,user_1; user_5; user_12; ...
MEDIUM,89,user_0; user_2; user_7; ...
LOW,64,user_3; user_4; user_6; ...
```

---

## Troubleshooting

### Training Takes Too Long
- Model training time depends on dataset size and AWS queue
- Typical range: 10-20 minutes for small dataset
- Check AWS Personalize console for status
- Wait at least 5 minutes before assuming it's stuck

### Batch Inference Fails
- **"User not found"**: Ensure batch input file format is correct
- **"Role doesn't have S3 access"**: Verify IAM role and bucket policy
- Check CloudWatch logs in AWS Personalize console

### No Results Downloaded
- Batch output path should end with `/` (trailing slash)
- Verify bucket and prefix are correct
- Check S3 console to see if files were created

### Low Engagement Scores
- May indicate weak signals in interaction data
- Check if event types are being counted correctly
- Verify ITEM_IDs (causes) match between datasets

---

## Success Criteria

✅ Model trains to ACTIVE status  
✅ Batch inference generates scores for all 200 donors  
✅ Segments created: High (80+), Medium (50-79), Low (<50)  
✅ Option A: Engagement scores show meaningful distribution  
✅ Option B: Cause rankings vary across donors  
✅ Option C: Segment sizes are non-trivial (not all in one segment)  

---

## Next Steps (Phase 2)

Once Phase 1 succeeds:
1. Repeat with large dataset (5,000+ interactions)
2. Compare results: are patterns stable at scale?
3. If yes → Phase 3: Integration with campaigns

---

## Useful AWS Personalize Commands

Check solution status:
```bash
aws personalize describe-solution \
  --solution-arn arn:aws:personalize:us-east-1:...:solution/...
```

Check solution version status:
```bash
aws personalize describe-solution-version \
  --solution-version-arn arn:aws:personalize:us-east-1:...:solution-version/...
```

Check batch job status:
```bash
aws personalize describe-batch-inference-job \
  --batch-inference-job-arn arn:aws:personalize:us-east-1:...:batch-inference-job/...
```

List all solutions in dataset group:
```bash
aws personalize list-solutions \
  --dataset-group-arn arn:aws:personalize:us-east-1:...:dataset-group/...
```
