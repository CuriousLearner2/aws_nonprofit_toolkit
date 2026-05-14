# Case Study: Food Bank USA (Hypothetical Template)

> **⚠️ IMPORTANT**: This case study is a **hypothetical simulation** designed to demonstrate the potential impact of the AWS Nonprofit Toolkit. All results are **PROJECTED BENCHMARKS** and have not yet been verified in a live pilot.

---

## 1. Scenario: The "Cold Start" Challenge
**Organization**: Food Bank USA (Regional food logistics NPO).
**Starting State**: 
*   **Database**: 1,000 historical donors.
*   **Performance**: 0.8% conversion rate on ads using broad interest targeting.

---

## 2. The Intervention (The Toolkit Lifecycle)
Food Bank USA used the toolkit to bootstrap their ML-driven growth:
1.  **Generate**: Created **2,000 synthetic donor profiles** mirroring their top 15% VIPs.
2.  **Validate (Pareto Audit)**: Confirmed a **63% wealth concentration** in the top 10% of donors, providing Meta with a clean "Value-Based" signal.
3.  **Validate (ML Signal)**: Confirmed a **24% interaction bulge** for childhood hunger causes using `uncover_signal_no_pandas.py`.
4.  **Sync**: Automatically seeded a Meta Lookalike Audience and triggered a **1% Lookalike (Sandbox)**.

---

## 3. Projected Results: Scaling Reach
The following metrics are **ASSUMED SUCCESS CRITERIA** for a successful toolkit implementation:

| Metric | Projection | Type | Rationale |
| :--- | :--- | :--- | :--- |
| **Reach Expansion** | **500%** | PROJECTED | Seeding Meta with 2,000 high-signal users allows for a 1% Lookalike (approx. 2M people) vs. niche interest targeting. |
| **Conversion Lift** | **0.8% → 3.2%** | ASSUMED | Reflects a 4x increase in ROI typically seen when moving from broad interests to high-value Lookalike seeds. |
| **Cost Efficiency** | **45% CPL Reduction** | PROJECTED | Assumes higher relevance scores on Meta leading to lower auction costs. |

---

## 4. Mathematical Methodology & Assumptions
These projections rely on the following technical assumptions:
1.  **High-Signal Accuracy**: We assume the synthetic data generates a signal bulge of **>20%**, allowing ML models to accurately classify donor archetypes.
2.  **Pareto Integrity**: We assume the **Seed Quality Audit** maintains a >60% concentration, ensuring Meta optimizations target givers over casual users.
3.  **Meta Match Rate**: We assume a **>60% match rate** when hashing and uploading the synthetic seed to Meta.
3.  **Lookalike Correlation**: We assume that Meta's "People similar to your VIPs" algorithm correctly identifies high-intent donors from the synthetic seed.

---

## 5. Recommended Validation Flow (Real-World A/B Test)
To verify these results in your own organization, we recommend the following control group setup:

| Group | Targeting Method | Creative | Success Metric |
| :--- | :--- | :--- | :--- |
| **Control (A)** | Broad Interest (e.g., "Charity") | Standard | Conversion Rate % |
| **Test (B)** | **Toolkit Lookalike (1%)** | Standard | Conversion Rate % |

---

## 6. Replication Template
*(Copy this table into your quarterly growth report)*

| Stage | Milestone | Baseline | Target | Actual |
| :--- | :--- | :--- | :--- | :--- |
| **Bootstrapping** | Synthetic Seed Count | 200 | 2,000 | |
| **Validation**| Signal Intensity Bulge | N/A | >20% | |
| **Sync** | Meta Match Rate | N/A | >60% | |
| **Execution** | Conversion Rate % | 0.8% | 2.5% | |
