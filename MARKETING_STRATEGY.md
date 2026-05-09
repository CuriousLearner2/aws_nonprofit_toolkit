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
    *   The size of Group A is controlled by the **`--bias-ratio`** flag (e.g., 0.25 = 25% of users).
*   **The Bias Intensity**: Within Group A, the probability of choosing a specific cause is controlled by **`CAUSE_BIAS_WEIGHT`** (e.g., 0.70 = 70% preference) in `config.py`.
*   **The Logic**: This simulates a specific donor demographic (e.g., West Coast donors) having a distinct preference compared to the general population.

### 2.3 Verification of Output
We verify the "signal" using `aws_nonprofit_toolkit/uncover_signal_no_pandas.py`:
*   **Method**: The script calculates the percentage of total interactions per item for both groups.
*   **Standard Target**: A successful simulation shows a **20% to 45% statistical shift** in Group A compared to Group B.

---

## 3. Implementation Example: Content Affinity Tracks
In a real-world integration, the toolkit's signals are used to drive personalized email and SMS campaigns. By tracking engagement with different content "tracks," we can identify donor archetypes:

### 3.1 Efficiency Track (ROI & Scale)
*   **Content**: Focuses on logistics, infrastructure, and low overhead.
*   **Signal**: Clicks here identify donors who value professional validation and corporate-grade reliability.

### 3.2 Human Impact Track (Outcomes & Stories)
*   **Content**: Focuses on individual stories, community impact, and emotional resonance.
*   **Signal**: Clicks here identify donors who prioritize the direct human results of their contribution.

---

## 4. Customization & Domain Adaptability
Nonprofits can customize the entire simulation to match their specific mission by editing **`aws_nonprofit_toolkit/config.py`**.

### 4.1 Configurable Parameters
*   **Scale**: Standardize on **2,000 users** for optimal ML signal detection.
*   **Pareto Distribution**: The simulation is tuned to ensure **>80% of total donation value** comes from the VIP segment, mimicking real-world wealth distribution.
*   **Signal Strength**: Tune `CAUSE_BIAS_WEIGHT` (intensity) and `--bias-ratio` (group size) to test how sensitive your ML model is to varying levels of behavioral bias.

---

## 5. Benchmarks & Success Metrics
Based on industry standards for high-signal lookalike campaigns, we target the following benchmarks:

| Sector | Projected Lift | Conversion Rate | Primary Goal |
| :--- | :--- | :--- | :--- |
| **Nonprofit (Our Target)** | **4x ROI Increase** | **3.2% (Target)** | Donor Acquisition & LTV |
| **For-Profit (Benchmark)** | 3.0x - 10.0x | 10% - 15% | Direct Sales & ROAS |

---

## 6. Version 2 Roadmap
*   **Value-Based Lookalikes (VBL):** Providing Meta with a "Value Column" (Lifetime Value - LTV) to prioritize finding twins of the highest-contributing donors.
*   **Continuous Feedback Loop**: Integrating real-world donation data from production databases back into the interaction stream.
*   **QuickSight Dashboard**: Launching a visual "Donor Growth Command Center" to track metrics in real-time.

---

## 7. Getting Started

### 7.1 Installation Steps
1.  Navigate to toolkit: `cd aws_nonprofit_toolkit`
2.  Install: `pip install -r requirements.txt`
3.  Generate Data: `python3 generate_datasets.py --count 2000 --bias-ratio 0.25`
4.  Verify Signal: `python3 uncover_signal_no_pandas.py datasets/large_nonprofit_interactions.csv`
