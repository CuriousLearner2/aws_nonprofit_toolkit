# Configuration Guide (config.py)

This document details the configurable parameters in `aws_nonprofit_toolkit/config.py`. These variables allow you to tune the data generation and simulation logic to match your specific nonprofit's mission and donor base.

---

## 1. Scale & Interaction Targets

| Parameter | Default | Range | Description |
| :--- | :--- | :--- | :--- |
| `SMALL_USER_COUNT` | `200` | 10 - 5,000 | Number of users for the attribute-focused dataset (Custom Audiences). |
| `LARGE_USER_COUNT` | `2000` | 500 - 1M+ | Number of users for the ML-focused dataset (Amazon Personalize). |
| `INTERACTIONS_PER_USER`| `5` | 1 - 50 | Average number of views/donations per donor profile. |

---

## 2. Cause Categories & Item IDs

| Parameter | Default | Example Customization |
| :--- | :--- | :--- |
| `ITEMS` | `['CLEAN_WATER', 'ANIMAL_RESCUE', 'EDUCATION', ...]` | `['LITERACY', 'SCHOLARSHIPS', 'SCHOOL_SUPPLIES']` |

---

## 3. Behavioral Bias (The "Signal" Math)

These parameters control the statistical "bulge" used to train the machine learning models.

| Parameter | Default | Range | Description |
| :--- | :--- | :--- | :--- |
| `CAUSE_BIAS_WEIGHT` | `0.70` | 0.0 - 1.0 | Probability that "Group A" users interact with a biased cause. |
| `BIASED_ITEMS` | `['CLEAN_WATER', 'ENVIRONMENT']` | N/A | The specific items Group A is biased toward. |

---

## 4. Demographics & Loyalty Distributions

| Parameter | Defaults | Valid Sum | Description |
| :--- | :--- | :--- | :--- |
| `LOYALTY_DISTRIBUTION` | `NEW: 0.50, REGULAR: 0.35, VIP: 0.15` | **1.0** | Probability weights for assigning user loyalty tiers. |
| `SOURCE_WEIGHTS` | `ORGANIC: 0.60, WHATSAPP: 0.25, FB: 0.15` | **1.0** | Probability weights for donor acquisition sources. |
| `CONSENT_RATE` | `0.80` | 0.0 - 1.0 | Percentage of users who opt-in to marketing (PII hashing). |

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
*   **Base Validation**: Standard users (Baseline) default to an average donation of **$2.09**, while VIPs default to **$273.65**.
