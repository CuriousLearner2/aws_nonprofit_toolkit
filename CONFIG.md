# Configuration Guide (config.py)

This document details the configurable parameters in `aws_nonprofit_toolkit/config.py`. These variables allow you to tune the data generation and simulation logic to match your specific nonprofit's mission and donor base.

---

## 1. Scale & Interaction Targets

| Parameter | Default | Reasonable Range | Description |
| :--- | :--- | :--- | :--- |
| `SMALL_USER_COUNT` | `200` | 100 - 1,000 | Number of users for Custom Audience seeding. Meta requires ~100 matches minimum. |
| `LARGE_USER_COUNT` | `2000` | 1,000 - 100K | **Standard Default**. Number of users for ML training. Personalize performs best with higher variety. |
| `INTERACTIONS_PER_USER`| `5` | 3 - 15 | Average donor interactions. < 3 is too sparse for ML; > 20 is rare for casual donors. |

---

## 2. Behavioral Bias (The "Signal" Math)

These parameters control the statistical "bulge" used to train the machine learning models.

| Parameter | Default | Realistic Range | Description |
| :--- | :--- | :--- | :--- |
| `DEFAULT_BIAS_RATIO`| `0.25` | 0.10 - 0.40 | **Group Size**. Percentage of users who will receive biased preferences. |
| `CAUSE_BIAS_WEIGHT` | `0.70` | 0.40 - 0.85 | **Preference Intensity**. The probability that a biased user will choose the target cause. |

*Note: Combined, these two parameters create a statistical shift of **20% to 45%** in the interaction stream, optimal for ML detection.*

---

## 3. Demographics & Loyalty Distributions

| Parameter | Defaults | Realistic Context | Description |
| :--- | :--- | :--- | :--- |
| `LOYALTY_DISTRIBUTION` | `VIP: 0.15` | 5% - 20% | High-value donors (VIPs) typically make up 10-15% of a healthy nonprofit base. |
| `SOURCE_WEIGHTS` | `FB: 0.15` | 10% - 40% | Social media leads (Meta) usually account for 15-30% of multi-channel traffic. |

---

## 4. Strategic Impact
*   **VIP Pareto Principle**: By default, the simulation ensures that **>80% of total donation value** comes from the VIP segment, reflecting real-world wealth concentration.
*   **Signal Density**: Standardizing on **2,000 users** with a **0.25 bias ratio** ensures that Amazon Personalize has enough interaction density to detect patterns without overfitting.
