# Marketing Strategy: High-Signal Donor Growth

This document outlines the strategic use of simulations to optimize Replate's donor acquisition funnel using AWS services and Meta's Lookalike Audiences.

---

## 1. Overview
The goal of this strategy is to solve the "Cold Start" problem in donor acquisition. By simulating donor behavior before launching paid campaigns, we ensure that our Meta Lookalike seed lists are high-quality and our WhatsApp conversion bot is tuned to specific donor archetypes.

---

## 2. Simulation 1: Behavioral Bias (The "Signal" Engine)
**Location:** `aws_nonprofit_toolkit/generate_datasets.py`

### 2.1 Dataset Characteristics
We generate two distinct CSV datasets to simulate different scales of nonprofit operations:
*   **Small Dataset (200 users)**: Focused on qualitative attributes like `LOYALTY_LEVEL` (VIP, Regular, New) and `INTEREST_TAG`. Used for seeding Meta Custom Audiences.
*   **Large Dataset (2,000 users / 10,000+ interactions)**: Optimized for machine learning (Amazon Personalize). It requires a high volume of interactions to "learn" user preferences.

### 2.2 Injecting Behavioral Bias
To simulate real-world donor preferences, we intentionally skewed the data for a subset of the large dataset:
*   **Segmentation**: Users are split into **Group A** (IDs 0-499) and **Group B** (IDs 500-1999).
*   **The Bias**: Group A is assigned a **70% probability** of interacting with `CLEAN_WATER` or `ENVIRONMENT` items. Group B remains "neutral," with a perfectly random distribution across all categories.
*   **The Logic**: This simulates a specific donor demographic (e.g., West Coast donors) having a distinct preference compared to the general population.

### 2.3 Verification of Output
We verify the "signal" using `aws_nonprofit_toolkit/uncover_signal_no_pandas.py`:
*   **Method**: The script calculates the percentage of total interactions per item for both groups.
*   **Desired Outcome**: A successful simulation shows a **~25-30% statistical "bulge"** for `CLEAN_WATER` in Group A compared to Group B.
*   **Significance**: This delta is the "High Signal" that Amazon Personalize detects to provide accurate recommendations.

---

## 3. Simulation 2: Campaign Archetypes (The "Conversion" Engine)
**Location:** `replate/generate_campaign_simulation.py`

### 3.1 Dataset Characteristics
This simulation generates **Campaign Responses** for 100 potential donors, tracking their engagement with specific marketing content.

### 3.2 Injecting Content Bias (Efficiency vs. Impact)
We simulate two distinct creative directions to identify donor archetypes:
*   **Efficiency Track (40% click rate)**: Content focused on logistics, scale, and low overhead.
*   **Human Impact Track (35% click rate)**: Content focused on individual stories and emotional resonance.
*   **Conversion Logic**: We program a higher donation probability for users who click *any* track, with a slightly higher "Impact" bias (25% vs 20%).

### 3.3 Archetype Identification
The script automatically categorizes donors based on their response:
*   **VIP Seed**: Users who clicked **both** tracks OR donated > $100.
*   **Standard**: Users who donated but didn't meet VIP criteria.
*   **Potential**: Users who clicked but haven't donated yet.

---

## 4. The Growth Loop (Meta Lookalike Integration)
**Location:** `aws_nonprofit_toolkit/meta_growth_engine.py`

The output of the simulations feeds directly into the Meta growth engine:
1.  **VIP Extraction**: We extract only the `VIP` loyalty level from our datasets.
2.  **Hashing**: Emails are SHA256 hashed to comply with Meta's privacy requirements.
3.  **Audience Seeding**: The hashed VIP list is uploaded to a **Meta Custom Audience**.
4.  **Lookalike Generation**: Meta uses this "High Signal" seed to find 1% of the population that "looks like" our best donors.
5.  **Conversion**: These new leads are driven to the **WhatsApp Bot**, which uses the archetype data to personalize the initial greeting.

---

## 5. Benefits of This Approach
*   **Risk Mitigation**: We debug the conversion flow with synthetic data before spending budget.
*   **Optimized ROAS**: By seeding Meta with "Group A" (High Signal) VIPs instead of random users, the Lookalike algorithm finds much more relevant leads.
*   **Personalization at Scale**: We know before the user even says "Hi" on WhatsApp whether they are likely motivated by "Efficiency" or "Impact."
