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

## 4. Customization & Domain Adaptability
Nonprofits can customize the entire simulation to match their specific mission by editing **`aws_nonprofit_toolkit/config.py`**.

### 4.1 Configurable Parameters
*   **Scale**: Adjust `LARGE_USER_COUNT` and `INTERACTIONS_PER_USER` to simulate different volumes of donor traffic.
*   **Cause Categories**: Modify the `ITEMS` list (e.g., change `CLEAN_WATER` to `LITERACY_PROGRAMS`).
*   **Signal Strength**: Tune `CAUSE_BIAS_WEIGHT` (default 0.70) to test how sensitive your ML model is to varying levels of behavioral bias.
*   **Donor Demographics**: Edit `LOYALTY_DISTRIBUTION` and `SOURCE_WEIGHTS` to reflect your real-world donor base (e.g., if most of your donors come from Facebook vs. Organic).

---

## 5. Benchmarks & Success Metrics
Based on industry standards for high-signal lookalike campaigns, we target the following benchmarks:

| Sector | Target ROAS | Conversion Rate | Primary Goal |
| :--- | :--- | :--- | :--- |
| **Nonprofit (Our Target)** | **1.5x - 2.0x** | **5% - 8%** | Donor Acquisition & LTV |
| **For-Profit (Benchmark)** | 3.0x - 10.0x | 10% - 15% | Direct Sales & ROAS |

*Note: For nonprofits, a 1.5x ROAS is considered a win because it covers the acquisition cost on the first gift, with profit realized through recurring donations.*

---

## 6. Version 2 Roadmap: Value-Based Lookalikes (VBL)
While V1 focuses on "Identity" (who the donors are), V2 will focus on **"Value"** (how much they contribute). 

### 6.1 How VBL Works
In V1, we upload a flat list of emails. Meta treats the $5 donor and the $500 donor as equals. In V2, we will provide a **Value Column (Lifetime Value - LTV)** alongside the email.

### 6.2 The Algorithmic Shift
When Meta receives a value-based seed:
1. **Weighted Signals**: The algorithm prioritizes the social graph and behavioral signals of your highest-spending donors.
2. **Quality Twin Search**: Instead of finding people who "look like" your average donor, Meta finds people who "look like" your **VIPs**.
3. **Optimized Reach**: This typically results in a **25% lower Cost Per Acquisition (CPA)** and higher initial gift sizes.

### 6.3 Implementation Plan (V2)
- **Data Export**: Update `generate_datasets.py` to include a weighted `LTV` field.
- **API Update**: Modify `meta_growth_engine.py` to use the Meta `customer_value` schema.
- **Feedback Loop**: Feed real donation values back from Supabase to Meta via the Conversions API.

---

## 7. Getting Started
... (rest of the file) ...

### 5.1 Prerequisites
*   **Python 3.11+**: Ensure you have a modern Python environment.
*   **Meta Business App**: You need a "System User" token with `ads_management` and `ads_read` permissions.
*   **AWS Account**: Permissions for **Amazon Personalize** (if running ML training).
*   **Environment Variables**: Create a `.env` file based on `.env.example`.

### 5.2 Installation Steps
1.  **Navigate to toolkit**: `cd aws_nonprofit_toolkit`
2.  **Create Virtual Env**: `python3 -m venv venv`
3.  **Activate**: `source venv/bin/activate`
4.  **Install**: `pip install -r requirements.txt`

---

## 6. Usage Examples & Real Output

### 6.1 Step 1: Generate Synthetic Data
Run the generator to create your baseline and biased datasets.
```bash
python3 generate_datasets.py
```
**Output:**
```text
Generating Small Nonprofit Dataset...
Generating Large Nonprofit Dataset...
Datasets generated in datasets/
```

### 6.2 Step 2: Verify Signal Strength
Analyze the interactions to ensure the behavioral bias was injected correctly.
```bash
python3 uncover_signal_no_pandas.py
```
**Example Output:**
```text
--- Analyzing datasets/large_nonprofit_interactions.csv ---
Total Interactions: 10000
Group A Interactions: 2468 | Group B Interactions: 7532
------------------------------
Item ID              | Group A %  | Group B % 
---------------------------------------------
CLEAN_WATER          |    38.78% |    16.04%
ENVIRONMENT          |    41.13% |    16.56%
------------------------------
MATH REVEALS: Group A has a disproportionate interest in 'ENVIRONMENT'.
Difference: 24.57% shift compared to the neutral group.
```

### 6.3 Step 3: Seed Meta Custom Audience
Synchronize your VIP donor list with Meta for Lookalike generation.
```bash
python3 meta_growth_engine.py
```
**Example Output:**
```text
--- STEP 1: Creating Custom Audience on Meta ---
SUCCESS: Created Audience ID

--- STEP 2: Uploading VIPs from datasets/small_nonprofit_users.csv ---
Found 23 VIP donors. Uploading to Meta...
SUCCESS: VIP list synchronized with Meta.
```

---

## 7. Troubleshooting Guide

| Issue | Potential Cause | Resolution |
| :--- | :--- | :--- |
| **`ModuleNotFoundError`** | Missing dependencies | Run `pip install -r requirements.txt`. |
| **Meta `403 Forbidden`** | Invalid token or permissions | Ensure your Meta System User has been added to the Ad Account in Business Manager. |
| **Meta `400 Bad Request`** | Wrong Account ID format | Ensure `META_AD_ACCOUNT_ID` does **not** include the `act_` prefix in your `.env`. |
| **AWS `AccessDenied`** | IAM Permission issues | Ensure your CLI user has `AmazonPersonalizeFullAccess`. |
| **Low Signal Shift (<10%)** | Generation randomness | Re-run `generate_datasets.py` to refresh the distribution. |

---

## 8. Benefits of This Approach
... (rest of the file) ...
