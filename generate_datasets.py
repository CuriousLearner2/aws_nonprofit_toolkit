import csv
import random
import time
import argparse
from pathlib import Path
from aws_nonprofit_toolkit.config import SimulationConfig

def generate_small_nonprofit(base_path, count):
    """Generates a dataset focused on user attributes/tags."""
    users_file = base_path / 'small_nonprofit_users.csv'
    interactions_file = base_path / 'small_nonprofit_interactions.csv'
    
    with open(users_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['USER_ID', 'EMAIL', 'INTEREST_TAG', 'LAST_DONATION_AMOUNT', 'LOYALTY_LEVEL', 'SOURCE', 'CONSENT'])
        for i in range(count):
            loyalty = random.choices(
                SimulationConfig.get_loyalty_levels(), 
                weights=SimulationConfig.get_loyalty_weights()
            )[0]
            
            writer.writerow([
                f'user_{i}',
                f'donor_{i}@example.com',
                random.choice(SimulationConfig.ITEMS),
                random.randint(0, 500),
                loyalty,
                random.choice(SimulationConfig.get_sources()),
                random.random() < SimulationConfig.CONSENT_RATE
            ])
            
    total_interactions = count * SimulationConfig.INTERACTIONS_PER_USER
    with open(interactions_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['USER_ID', 'ITEM_ID', 'TIMESTAMP', 'EVENT_TYPE', 'REFERRED_BY'])
        for i in range(total_interactions):
            writer.writerow([
                f'user_{random.randint(0, count-1)}',
                random.choice(SimulationConfig.ITEMS),
                int(time.time()) - random.randint(0, 10**7),
                random.choice(['VIEW', 'DONATE', 'SIGN_UP']),
                None
            ])

def generate_large_nonprofit(base_path, count, vip_ratio):
    """Generates a dataset optimized for ML with configurable bias."""
    users_file = base_path / 'large_nonprofit_users.csv'
    interactions_file = base_path / 'large_nonprofit_interactions.csv'
    
    with open(users_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['USER_ID', 'EMAIL', 'SOURCE', 'CONSENT'])
        for i in range(count):
            writer.writerow([
                f'user_{i}', 
                f'donor_{i}@example.com',
                'ORGANIC',
                random.random() < SimulationConfig.CONSENT_RATE
            ])
            
    total_interactions = count * SimulationConfig.INTERACTIONS_PER_USER
    with open(interactions_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['USER_ID', 'ITEM_ID', 'TIMESTAMP', 'EVENT_TYPE'])
        
        # Determine the Group A threshold based on vip_ratio
        group_a_threshold = int(count * vip_ratio)

        for i in range(total_interactions):
            user_idx = random.randint(0, count-1)
            
            if user_idx < group_a_threshold:
                if random.random() < SimulationConfig.CAUSE_BIAS_WEIGHT:
                    item = random.choice(SimulationConfig.BIASED_ITEMS)
                else:
                    item = random.choice(SimulationConfig.ITEMS)
            else:
                item = random.choice(SimulationConfig.ITEMS)
                
            writer.writerow([
                f'user_{user_idx}',
                item,
                int(time.time()) - random.randint(0, 10**7),
                random.choice(['VIEW', 'DONATE', 'SIGN_UP'])
            ])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic nonprofit datasets.")
    parser.add_argument("--count", type=int, default=2000, help="Number of users to generate (Large dataset)")
    parser.add_argument("--vip-ratio", type=float, default=0.25, help="Ratio of users in biased Group A (0.0 to 1.0)")
    parser.add_argument("--output", type=str, default="aws_nonprofit_toolkit/datasets", help="Output directory")
    
    args = parser.parse_args()
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True, parents=True)
    
    SimulationConfig.validate()
    
    print(f"--- Generating Datasets (Count: {args.count}, VIP Ratio: {args.vip_ratio}) ---")
    generate_small_nonprofit(output_dir, SimulationConfig.SMALL_USER_COUNT)
    generate_large_nonprofit(output_dir, args.count, args.vip_ratio)
    
    print(f"SUCCESS: Datasets generated in {output_dir}/")
