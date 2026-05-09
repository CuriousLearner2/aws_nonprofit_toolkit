# Marketing Strategy: High-Signal Donor Growth

This document outlines the strategic use of simulations to optimize a nonprofit's donor acquisition funnel using AWS services and Meta's Lookalike Audiences.

---

## 1. Overview
The goal of this strategy is to solve the "Cold Start" problem in donor acquisition. By simulating donor behavior before launching paid campaigns, we ensure that our Meta Lookalike seed lists are high-quality and our conversion efforts are tuned to specific donor archetypes.

---

## 2. Simulation 1: Behavioral Bias (The "Signal" Engine)
**Location:** `aws_nonprofit_toolkit/generate_datasets.py`

### 2.1 Dataset Characteristics
We generate synthetic datasets to simulate different scales of nonprofit operations:
*   **Acquisition Seed (Small)**: Focused on qualitative attributes like `LOYALTY_LEVEL` (VIP, Regular, New) and `INTEREST_TAG`. Used for seeding Meta Custom Audiences.
*   **Behavioral Stream (Large)**: Optimized for machine learning (Amazon Personalize). Requires high-volume interactions to "learn" user preferences.

### 2.2 Injecting Behavioral Bias
To simulate real-world donor preferences, we intentionally skewed the data for a subset of the dataset:
*   **Segmentation**: Users are split into **Group A** (Biased) and **Group B** (Neutral).
*   **The Bias**: Group A is assigned a higher probability of interacting with specific causes (e.g., `CLEAN_WATER`). Group B remains "neutral."
*   **The Logic**: This simulates a specific donor demographic (e.g., West Coast donors) having a distinct preference compared to the general population.

### 2.3 Verification of Output
We verify the "signal" using `aws_nonprofit_toolkit/uncover_signal_no_pandas.py`:
*   **Method**: The script calculates the percentage of total interactions per item for both groups.
*   **Standard Target**: A successful simulation shows a **~25% statistical "bulge"** in Group A compared to Group B.

---

## 3. Integration Example: Campaign Archetypes (The "Conversion" Engine)
*Note: This specific implementation example uses the **Replate** application as a client.*

### 3.1 Scenario
In a real-world integration, the toolkit's signals are used to drive personalized campaigns. For example, the **Replate** project uses a campaign simulator to identify donor archetypes:
*   **Efficiency Track**: Content focused on logistics, scale, and low overhead.
*   **Human Impact Track**: Content focused on individual stories and emotional resonance.

### 3.2 Archetype Identification
Donors are categorized based on their response to these tracks:
*   **VIP Seed**: Users who clicked **both** tracks OR donated > $100.
*   **Standard**: Users who donated but didn't meet VIP criteria.
*   **Potential**: Users who clicked but haven't donated yet.

---

## 4. Customization & Domain Adaptability
Nonprofits can customize the entire simulation to match their specific mission by editing **`aws_nonprofit_toolkit/config.py`**.

### 4.1 Configurable Parameters
*   **Scale**: Standardize on **2,000 users** for optimal ML signal detection.
*   **Cause Categories**: Modify the `ITEMS` list (e.g., change `CLEAN_WATER` to `LITERACY_PROGRAMS`).
*   **Signal Strength**: Tune `CAUSE_BIAS_WEIGHT` (default 0.70) to test how sensitive your ML model is to varying levels of behavioral bias.

---

## 5. Benchmarks & Success Metrics
Based on industry standards for high-signal lookalike campaigns, we target the following benchmarks:

| Sector | Projected Lift | Conversion Rate | Primary Goal |
| :--- | :--- | :--- | :--- |
| **Nonprofit (Our Target)** | **4x ROI Increase** | **3.2% (Target)** | Donor Acquisition & LTV |
| **For-Profit (Benchmark)** | 3.0x - 10.0x | 10% - 15% | Direct Sales & ROAS |

*Note: The target conversion rate is based on the 4x improvement (0.8% baseline to 3.2% target) identified in the Food Bank USA case study simulation.*

---

## 6. Version 2 Roadmap: Value-Based Lookalikes (VBL)
While V1 focuses on "Identity" (who the donors are), V2 will focus on **"Value"** (how much they contribute). 

### 6.1 How VBL Works
In V2, we will provide a **Value Column (Lifetime Value - LTV)** alongside the email. Meta’s algorithm will prioritize finding people similar to your **highest-spending** donors, typically resulting in a **25% lower Cost Per Acquisition (CPA)**.

---

## 7. Getting Started

### 7.1 Prerequisites
*   **Python 3.11+**
*   **Meta Business App**: "System User" token with `ads_management` permissions.
*   **AWS Account**: Permissions for **Amazon Personalize**.

### 7.2 Installation Steps
1.  Navigate to toolkit: `cd aws_nonprofit_toolkit`
2.  Install: `pip install -r requirements.txt`
3.  Generate Data: `python3 generate_datasets.py --count 2000 --bias-ratio 0.25`
4.  Verify Signal: `python3 uncover_signal_no_pandas.py datasets/large_nonprofit_interactions.csv`
