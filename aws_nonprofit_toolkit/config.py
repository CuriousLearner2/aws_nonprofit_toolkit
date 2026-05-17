from typing import List, Dict

class SimulationConfig:
    """
    Centralized configuration for synthetic data generation.
    Nonprofits can adjust these weights and counts to match their specific domain.
    """
    
    # 1. SCALE & TARGETS
    SMALL_USER_COUNT = 1000
    LARGE_USER_COUNT = 2000
    INTERACTIONS_PER_USER = 5  # Average interactions per user
    
    # 2. CAUSE CATEGORIES
    ITEMS = [
        'CLEAN_WATER', 'ANIMAL_RESCUE', 'EDUCATION', 
        'DISASTER_RELIEF', 'ENVIRONMENT', 'COMMUNITY_HEALTH'
    ]
    
    # 3. BIAS CONFIGURATION (The "Signal" math)
    # The percentage of Group A users who will choose from the 'biased_items'
    CAUSE_BIAS_WEIGHT = 0.70  # Default 70%
    BIASED_ITEMS = ['CLEAN_WATER', 'ENVIRONMENT']
    
    # 4. DEMOGRAPHICS & LOYALTY
    LOYALTY_DISTRIBUTION = {
        'NEW': 0.50,      # 50%
        'REGULAR': 0.35,  # 35%
        'VIP': 0.15       # 15%
    }
    
    CONSENT_RATE = 0.80  # 80% of users opt-in to marketing
    
    # 5. SOURCE DISTRIBUTION
    SOURCE_WEIGHTS = {
        'ORGANIC': 0.60,
        'SMS': 0.25,
        'FACEBOOK': 0.15
    }

    @classmethod
    def get_loyalty_levels(cls) -> List[str]:
        return list(cls.LOYALTY_DISTRIBUTION.keys())

    @classmethod
    def get_loyalty_weights(cls) -> List[float]:
        return list(cls.LOYALTY_DISTRIBUTION.values())

    @classmethod
    def get_sources(cls) -> List[str]:
        return list(cls.SOURCE_WEIGHTS.keys())

    @classmethod
    def get_source_weights(cls) -> List[float]:
        return list(cls.SOURCE_WEIGHTS.values())

    @classmethod
    def validate(cls):
        """Ensures probability distributions sum to approximately 1.0."""
        loyalty_sum = sum(cls.LOYALTY_DISTRIBUTION.values())
        source_sum = sum(cls.SOURCE_WEIGHTS.values())
        
        if not (0.99 <= loyalty_sum <= 1.01):
            raise ValueError(f"LOYALTY_DISTRIBUTION weights must sum to 1.0 (got {loyalty_sum})")
        if not (0.99 <= source_sum <= 1.01):
            raise ValueError(f"SOURCE_WEIGHTS weights must sum to 1.0 (got {source_sum})")
        if not (0.0 <= cls.CAUSE_BIAS_WEIGHT <= 1.0):
            raise ValueError("CAUSE_BIAS_WEIGHT must be between 0.0 and 1.0")
