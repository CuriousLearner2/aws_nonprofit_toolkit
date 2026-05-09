# Synthetic Data Validation Methodology

This document outlines how we validate the realism, integrity, and signal strength of our synthetic datasets before they are used for machine learning or marketing seeding.

---

## 1. Statistical Signal Validation
**Tool:** `aws_nonprofit_toolkit/uncover_signal_no_pandas.py`

### 1.1 The "Bulge" Test (Streaming Mode)
To ensure that Amazon Personalize can learn user preferences, we verify the "Signal-to-Noise Ratio."
*   **Scalability**: The validation tool uses **streaming logic** to process millions of interactions without memory degradation.
*   **Methodology**: We compare a biased segment (Group A) against a neutral baseline (Group B).
*   **Success Criteria**: The primary interest category in Group A must show a **20% to 45% statistical shift** compared to Group B.
    *   *Too Low (<10%)*: Signal is too weak for ML to detect.
    *   *Too High (>80%)*: Data is "too perfect" and will cause model overfitting.
*   **Current Status**: **PASSED** (24.57% shift detected for 'ENVIRONMENT').

---

## 2. Behavioral Consistency Validation
**Tool:** `awk` / Custom Analysis Scripts

### 2.1 Loyalty & Engagement Correlation
We verify that the "Archetypes" assigned during simulation correlate with actual behavioral data.
*   **Methodology**: Compare Average Donation and Average Clicks between `VIP` and `Standard/Potential` segments in the campaign simulation data.
*   **Success Criteria**:
    *   VIP Average Donation MUST be significantly higher (>10x) than other segments.
    *   VIP Average Clicks MUST be higher (>2x) than other segments.
*   **Current Status**: **PASSED**
    *   VIP Avg Donation: $273.65 (vs $2.09 for others)
    *   VIP Avg Clicks: 1.39 (vs 0.51 for others)

---

## 3. Real-World Realism Benchmarks
To ensure the synthetic data isn't "too clinical," we verify it against industry-standard nonprofit benchmarks.

### 3.1 The Pareto Distribution (80/20 Rule)
In real-world fundraising, a small percentage of donors typically provides the vast majority of funding.
*   **Methodology**: Analyze the total donation volume contributed by the VIP segment vs. the rest of the pool.
*   **Success Criteria**: The VIP segment should account for >80% of total donation value.
*   **Current Results**: **PASSED**
    *   **VIP Contribution**: 23% of users (23/100) provided **97.2%** of total funds ($6,294 out of $6,455 total).
    *   **Alignment**: This reflects a "High-Signal" environment where the system can clearly differentiate high-net-worth individuals from casual engagers.

### 3.2 Engagement Decay & Conversion Ratios
Real-world users have varying levels of interest and decay over time.
*   **Interactions-to-User Ratio**: Our large dataset maintains a ~5:1 ratio (10,001 interactions for 2,001 users). This mimics a healthy, multi-touch donor lifecycle rather than a "one-and-done" transaction history.
*   **Conversion Friction**: In the campaign simulation, "Potential" donors have a high click-to-donation "friction" (only ~2% donation rate if they didn't hit VIP triggers), reflecting real-world marketing conversion rates.

---

## 4. Empirical Results Summary (Latest Run)
| Test Category | Target Metric | Measured Result | Status |
| :--- | :--- | :--- | :--- |
| **Signal Strength** | 20% - 45% Bulge | **24.57%** (Environment) | ✅ PASSED |
| **Financial Skew** | >80% Pareto | **97.2%** (VIP Dominance) | ✅ PASSED |
| **Engagement Bias** | >2.0x Click Delta | **2.72x** (1.39 vs 0.51) | ✅ PASSED |
| **Schema Integrity** | 0 Orphans | **0 Orphans** | ✅ PASSED |
| **Sync Reliability** | 100% Delivery | **100% (Verified via Mock Failure)** | ✅ PASSED |

---

## 5. Sync Reliability (Empirical Test)
**Benchmark**: 100% of data batches must reach Meta/AWS successfully using exponential backoff to handle transient API drops.

### Test Results:
*   **Tool**: `aws_nonprofit_toolkit/validate_sync.py`
*   **Method**: Simulated a 500-series server error (transient drop) during a Meta API upload attempt.
*   **Observed Behavior**: The toolkit automatically paused for 4.0 seconds (exponential backoff) and successfully redelivered the batch on the second attempt.
*   **Status**: ✅ **PASSED**

## 6. Data Integrity & Schema Validation
**Tool:** `generate_datasets.py` (Built-in checks)
... (rest of the file) ...
