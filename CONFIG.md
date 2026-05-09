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

## 2. Cause Categories & Item IDs

| Parameter | Default | Example Customization |
| :--- | :--- | :--- |
| `ITEMS` | `['CLEAN_WATER', ...]` | `['LITERACY', 'SCHOLARSHIPS', 'SCHOOL_SUPPLIES']` |

---

## 3. Behavioral Bias (The "Signal" Math)

These parameters control the statistical "bulge" used to train the machine learning models.

| Parameter | Default | Realistic Range | Description |
| :--- | :--- | :--- | :--- |
| `CAUSE_BIAS_WEIGHT` | `0.70` | 0.40 - 0.85 | 0.7 is a strong but realistic preference. < 0.4 is too noisy; > 0.9 is "too perfect" (overfit). |
| `BIASED_ITEMS` | `['CLEAN_WATER', ...]` | N/A | The specific items Group A is biased toward. |
| `DEFAULT_BIAS_RATIO`| `0.25` | 0.10 - 0.40 | **Standard Default**. 25% of users receive biased preferences. |

---

## 4. Demographics & Loyalty Distributions

| Parameter | Defaults | Realistic Context | Description |
| :--- | :--- | :--- | :--- |
| `LOYALTY_DISTRIBUTION` | `VIP: 0.15` | 5% - 20% | High-value donors (VIPs) typically make up 10-15% of a healthy nonprofit base. |
| `SOURCE_WEIGHTS` | `FB: 0.15` | 10% - 40% | Social media leads (Meta) usually account for 15-30% of multi-channel traffic. |
| `CONSENT_RATE` | `0.80` | 0.60 - 0.90 | Industry standard opt-in rates range from 70% to 85% for direct donors. |

---

## 5. Usage Example

If you wanted to simulate a specialized literacy nonprofit with a highly engaged Facebook audience:

```python
class SimulationConfig:
    # 1. Custom Mission
    ITEMS = ['LITERACY', 'LIBRARIES', 'TEACHER_TRAINING']
    BIASED_ITEMS = ['LITERACY']
    
    # 2. High Engagement Signal
    CAUSE_BIAS_WEIGHT = 0.90  # 90% bias for Group A
    
    # 3. Custom Source Bias
    SOURCE_WEIGHTS = {
        'ORGANIC': 0.10,
        'WHATSAPP': 0.10,
        'FACEBOOK': 0.80  # Most donors come from FB
    }
```

---

## 🛠 Strategic Impact
*   **VIP Signal**: By default, VIPs are generated to show **130x higher** donation values and **2.7x higher** engagement than standard users, providing a high-quality seed for Meta Lookalikes.
*   **Signal Density**: Standardizing on **2,000 users** with a **0.25 bias ratio** ensures that Amazon Personalize has enough interaction density to detect the Group A preference without overfitting.
