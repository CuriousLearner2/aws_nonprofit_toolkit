import csv
import random
import time
import os
from pathlib import Path
from aws_nonprofit_toolkit.config import SimulationConfig

def generate_small_nonprofit(base_path):
    """Generates a dataset focused on user attributes/tags based on SimulationConfig."""
    users_file = base_path / 'small_nonprofit_users.csv'
    interactions_file = base_path / 'small_nonprofit_interactions.csv'
    
    # Create Users with tags and growth metadata
    with open(users_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['USER_ID', 'EMAIL', 'INTEREST_TAG', 'LAST_DONATION_AMOUNT', 'LOYALTY_LEVEL', 'SOURCE', 'CONSENT'])
        for i in range(SimulationConfig.SMALL_USER_COUNT):
            loyalty = random.choices(
                SimulationConfig.get_loyalty_levels(), 
                weights=SimulationConfig.get_loyalty_weights()
            )[0]
            
            source = random.choices(
                SimulationConfig.get_sources(),
                weights=SimulationConfig.get_source_weights()
            )[0]

            writer.writerow([
                f'user_{i}',
                f'donor_{i}@example.com',
                random.choice(SimulationConfig.ITEMS),
                random.randint(0, 500),
                loyalty,
                source,
                random.random() < SimulationConfig.CONSENT_RATE
            ])
            
    # Create Interactions
    total_interactions = SimulationConfig.SMALL_USER_COUNT * SimulationConfig.INTERACTIONS_PER_USER
    with open(interactions_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['USER_ID', 'ITEM_ID', 'TIMESTAMP', 'EVENT_TYPE', 'REFERRED_BY'])
        for i in range(total_interactions):
            writer.writerow([
                f'user_{random.randint(0, SimulationConfig.SMALL_USER_COUNT-1)}',
                random.choice(SimulationConfig.ITEMS),
                int(time.time()) - random.randint(0, 10**7),
                random.choice(['VIEW', 'DONATE', 'SIGN_UP']),
                None
            ])

def generate_large_nonprofit(base_path):
    """Generates a dataset optimized for ML (Amazon Personalize) with configurable bias."""
    users_file = base_path / 'large_nonprofit_users.csv'
    interactions_file = base_path / 'large_nonprofit_interactions.csv'
    
    # Create Users
    with open(users_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['USER_ID', 'EMAIL', 'SOURCE', 'CONSENT'])
        for i in range(SimulationConfig.LARGE_USER_COUNT):
            writer.writerow([
                f'user_{i}', 
                f'donor_{i}@example.com',
                'ORGANIC',
                random.random() < SimulationConfig.CONSENT_RATE
            ])
            
    # Create Interactions with Weighted Bias
    total_interactions = SimulationConfig.LARGE_USER_COUNT * SimulationConfig.INTERACTIONS_PER_USER
    with open(interactions_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['USER_ID', 'ITEM_ID', 'TIMESTAMP', 'EVENT_TYPE'])
        for i in range(total_interactions):
            user_idx = random.randint(0, SimulationConfig.LARGE_USER_COUNT-1)
            
            # Group A (0-499) gets the cause bias
            if user_idx < 500:
                if random.random() < SimulationConfig.CAUSE_BIAS_WEIGHT:
                    item = random.choice(SimulationConfig.BIASED_ITEMS)
                else:
                    item = random.choice(SimulationConfig.ITEMS)
            else:
                # Group B remains neutral/random
                item = random.choice(SimulationConfig.ITEMS)
                
            writer.writerow([
                f'user_{user_idx}',
                item,
                int(time.time()) - random.randint(0, 10**7),
                random.choice(['VIEW', 'DONATE', 'SIGN_UP'])
            ])

if __name__ == "__main__":
    output_dir = Path("aws_nonprofit_toolkit/datasets")
    output_dir.mkdir(exist_ok=True, parents=True)
    
    print(f"--- Generating Datasets using SimulationConfig ---")
    print(f"Target Items: {SimulationConfig.ITEMS}")
    print(f"Cause Bias: {SimulationConfig.CAUSE_BIAS_WEIGHT * 100}% toward {SimulationConfig.BIASED_ITEMS}")
    
    generate_small_nonprofit(output_dir)
    generate_large_nonprofit(output_dir)
    
    print(f"SUCCESS: Datasets generated in {output_dir}/")
