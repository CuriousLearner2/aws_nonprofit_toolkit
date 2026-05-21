# Pipeline Architecture: From Cold-Start to Automated Scale
**A Guide to Human-Labeling vs. ML-Inference for Nonprofit Growth**

This document outlines the two distinct data tracks within the AWS Nonprofit Toolkit: the **Acquisition Pipeline** (for finding new donors) and the **Personalization Pipeline** (for retaining existing ones).

---

## 1. The Acquisition Pipeline (Small Dataset)
**Goal:** Finding "Digital Twins" of your best supporters.
**Focus:** Identity and Quality.

### A. The Input: `small_nonprofit_users.csv`
This dataset contains high-level information about your donors (Email, City, Interest Tags).

### B. The Labeling: Human-Driven (Surgical)
*   **The Process:** A nonprofit manager or a CRM rule manually identifies "VIPs."
*   **The Signal:** You decide who is a high-value donor based on your organizational goals (e.g., "Gave > $500" or "Influential Community Leader").
*   **Why Human?** At the start, you don't have enough data for an AI to know who a VIP is. Human intuition and simple business rules are the most accurate way to "seed" the system.

### C. The Service: Meta Lookalike Audiences
*   We upload these **Human-Labeled VIPs** to Meta.
*   Meta’s AI analyzes their millions of social signals to find new people who share the same characteristics.
*   **Result:** A massive audience of potential new donors who "look like" your best existing ones.

### D. The Quality Guardrail: Pareto Principle Audit
*   **The Process:** Automated audit (`audit_seed_quality.py`) before every sync.
*   **The Signal:** Verifies that the top 10% of donors represent >60% of total organizational value.
*   **Why?** Meta's Value-Based Lookalike AI requires a clear "value slope" to work. If donor value is too flat/random, the AI cannot distinguish between a casual donor and a major giver.

---

## 2. The Personalization Pipeline (Large Dataset)
**Goal:** Maximizing the Lifetime Value (LTV) of every donor.
**Focus:** Behavior and Intent.

### A. The Input: `large_nonprofit_interactions.csv`
This dataset is a "stream" of events. Every click, every read, and every "forward" is recorded here as a raw log.

### B. The Labeling: ML-Driven (Inference)
*   **The Process:** **Amazon Personalize** (Machine Learning) reads the raw logs.
*   **The Signal:** The AI "infers" the donor's archetype by spotting patterns too complex for humans to see. It doesn't need you to tell it who is "Eco-Conscious"; it notices that "User 123" always clicks on carbon-offset stories and labels them automatically.
*   **Why ML?** Once you have thousands of donors and millions of clicks, a human can no longer keep up. The AI takes over the labeling at scale.

### C. The Service: Amazon Personalize
*   We feed the raw stream into Amazon Personalize.
*   The service creates **User Segments** (e.g., "The Pragmatist," "The Empath").
*   **Result:** Personalized email campaigns (via Amazon SES) that send the right story to the right person at the right time.

---

## 3. The Growth Flywheel: How they Connect
The power of the toolkit is that the **Small Dataset grows into the Large Dataset** in a continuous loop:

1.  **SEED (Human):** You label 200 VIPs in the **Small Dataset**.
2.  **SCALE (Meta):** Meta uses that seed to bring in **2,000 new donors** via ads.
3.  **STREAM (Activity):** Those 2,000 new donors start clicking and interacting with your content.
4.  **REVEAL (Large):** Their activity creates the **Large Dataset**.
5.  **PERSONALIZE (ML):** Amazon Personalize reads that dataset and ensures those 2,000 donors stay engaged for years.

---

## 4. Infrastructure Mapping

| Feature | Acquisition Track (Meta) | Personalization Track (AWS) |
| :--- | :--- | :--- |
| **Dataset** | `small_nonprofit_users.csv` | `small_nonprofit_interactions.csv` or `large_nonprofit_interactions.csv` |
| **Validation** | **Pareto Concentration Audit** | **Signal Validation** (coverage > 0 after training) |
| **Labeling Method** | **Human/Manual** (CRM Rules) | **Machine Learning** (Inferred) |
| **Setup** | Meta Marketing API | AWS Personalize (boto3) + IAM Role + S3 |
| **AI "Brain"** | Meta Lookalike AI | Amazon Personalize Recommender |
| **Output** | Lookalike Audiences (100k+) | Donor Rankings + Segments |

---

## 5. Track 2 Implementation Status (as of 2026-05-21)

### ✅ Completed
1. **Schema Definition**: `personalize_schema.json` created and applied
   - Fields: USER_ID, ITEM_ID, TIMESTAMP, EVENT_TYPE
   - Status: Active in dataset group

2. **Data Infrastructure**: Dataset group and interactions dataset created
   - Dataset Group ARN: `arn:aws:personalize:us-east-1:684039303576:dataset-group/nonprofit-donors-1779321550`
   - Dataset ARN: `arn:aws:personalize:us-east-1:684039303576:dataset/nonprofit-donors-1779321550/INTERACTIONS`
   - Status: ACTIVE

3. **Data Upload & Import**: Successfully imported ~500 donor interactions
   - Source: `datasets/small_nonprofit_interactions.csv`
   - S3 Location: `s3://personalize-sandbox-{account}/nonprofit/interactions/small_interactions.csv`
   - Import Job Status: ACTIVE (complete)

4. **AWS Setup**: IAM role and bucket policy configured
   - Role: `AmazonPersonalizeRole` (created via AWS Console)
   - Permissions: S3FullAccess + Personalize service trust
   - Bucket Policy: Allows Personalize service read access
   - Status: Verified working

### ⏳ Pending (Next Steps)
1. **Model Training**: Create solution and train recommender model
   - Input: Imported interaction dataset
   - Output: Trained model ARN
   - Time: ~10-15 minutes

2. **Batch Inference**: Generate predictions for all donors
   - Script: `personalize_batch_inference.py`
   - Output: JSON rankings (donor ID + engagement score)
   - Write to: S3 batch_output/ path
   - Time: ~5-10 minutes

3. **Segmentation & Archetype Mapping**: Extract donor segments
   - Script: `personalize_segmentation.py`
   - Config: `aws_nonprofit_toolkit/archetypes_config.json`
   - Output: Donor segments (High/Medium/Low engagement)
   - Time: ~5 minutes

4. **Campaign Integration**: Use segments for personalized outreach
   - High engagement: Email campaigns
   - Medium: Nurture sequences
   - Low: Re-engagement focus

### Current Roadmap
- **Phase 1 (Setup)**: ✅ Complete - schema, dataset, import all ACTIVE
- **Phase 2 (Training)**: ⏳ Next - train recommender model
- **Phase 3 (Inference)**: ⏳ Then - generate predictions
- **Phase 4 (Segmentation)**: ⏳ Finally - extract donor archetypes

