# Case Study: Food Bank USA

This case study demonstrates how a fictional nonprofit, **Food Bank USA**, used the AWS Nonprofit Toolkit to scale their donor acquisition and improve marketing efficiency.

---

## 1. Scenario: The "Cold Start" Challenge
**Organization**: Food Bank USA (Regional food logistics NPO).
**Starting State**: 
*   **Database**: 1,000 historical donors.
*   **ML Status**: No recommendation model; using broad interest-based targeting on Facebook.
*   **Performance**: 0.8% conversion rate on "Click-to-WhatsApp" ads.

---

## 2. The Intervention
Food Bank USA used the AWS Nonprofit Toolkit to bootstrap their machine learning and marketing efforts.

### Step 1: Scaling the Seed
Instead of waiting years to collect data from 50,000 donors, they generated **50,000 synthetic donor profiles** using `generate_datasets.py`, mirroring the behavior of their top 15% VIP donors.

### Step 2: Training the AI
They uploaded the synthetic interactions to **Amazon Personalize**. The model learned that donors interested in "Childhood Hunger" (Group A) had a high statistical correlation with "Sustainable Logistics" (The Bulge).

### Step 3: Seeding the Lookalike
They synchronized the hashed emails of their high-signal synthetic VIPs to **Meta Custom Audiences** via `meta_growth_engine.py`.
---

## 3. Results: Scaling Reach
By using a high-signal synthetic seed for their Meta Lookalike Audience, Food Bank USA achieved the following (Projected):

*   **Reach Expansion**: Expanded cold prospect reach by **500%**.
*   **Conversion Lift**: Improved WhatsApp conversion rate from **0.8% to 3.2%**.
*   **Cost Efficiency**: Reduced Cost-Per-Lead (CPL) by **45%**.

---

## 4. Methodology & Assumptions
The results above are **projected performance benchmarks** based on the following simulation assumptions:

1.  **High-Signal Seed**: We assume that generating 50,000 synthetic donors at a **15% VIP ratio** creates a dense enough behavioral signal for Amazon Personalize to accurately map Group A/B interests.
2.  **Lookalike Quality**: Meta’s Lookalike Audiences typically show a **2x-4x improvement** in conversion when seeded with high-value/VIP data vs. a generic audience. Our 4x projection (0.8% to 3.2%) reflects the "Ideal State" output of this toolkit.
3.  **Signal Persistence**: We assume that the behavioral bias (The "Bulge") injected in Step 2 persists through the Meta ML training phase.

---

## 5. Replication Template
...

Use this template to track your own results when using the toolkit:

| Stage | Metric | Baseline | Target | Actual |
| :--- | :--- | :--- | :--- | :--- |
| **Generation** | Donor Count | 1,000 | 50,000 | |
| **Validation**| Signal Intensity| N/A | >20% | |
| **Sync** | Meta Match Rate | N/A | >60% | |
| **Growth** | Conversion Rate | 0.8% | 2.5% | |
