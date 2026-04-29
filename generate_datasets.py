import csv
import random
import time
from pathlib import Path

# Configuration
SMALL_USER_COUNT = 200
LARGE_USER_COUNT = 2000
MIN_ML_INTERACTIONS = 1000

ITEMS = [
    'CLEAN_WATER', 'ANIMAL_RESCUE', 'EDUCATION', 
    'DISASTER_RELIEF', 'ENVIRONMENT', 'COMMUNITY_HEALTH'
]

EVENT_TYPES = ['VIEW', 'DONATE', 'SIGN_UP']

def generate_small_nonprofit(base_path):
    """Generates a dataset for < 500 users, focused on user attributes/tags."""
    users_file = base_path / 'small_nonprofit_users.csv'
    interactions_file = base_path / 'small_nonprofit_interactions.csv'
    
    # Create Users with tags and growth metadata
    with open(users_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['USER_ID', 'EMAIL', 'INTEREST_TAG', 'LAST_DONATION_AMOUNT', 'LOYALTY_LEVEL', 'SOURCE', 'CONSENT'])
        for i in range(SMALL_USER_COUNT):
            writer.writerow([
                f'user_{i}',
                f'donor_{i}@example.com',
                random.choice(ITEMS),
                random.randint(0, 500),
                random.choice(['NEW', 'REGULAR', 'VIP']),
                random.choice(['ORGANIC', 'WHATSAPP', 'FACEBOOK']),
                True # Existing donors are opted in
            ])
            
    # Create Interactions
    with open(interactions_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['USER_ID', 'ITEM_ID', 'TIMESTAMP', 'EVENT_TYPE', 'REFERRED_BY'])
        for i in range(SMALL_USER_COUNT * 2): # Avg 2 interactions per user
            writer.writerow([
                f'user_{random.randint(0, SMALL_USER_COUNT-1)}',
                random.choice(ITEMS),
                int(time.time()) - random.randint(0, 10**7),
                random.choice(EVENT_TYPES),
                None # No referrals yet
            ])

def generate_large_nonprofit(base_path):
    """Generates a dataset for > 500 users, optimized for ML (Amazon Personalize)."""
    users_file = base_path / 'large_nonprofit_users.csv'
    interactions_file = base_path / 'large_nonprofit_interactions.csv'
    
    # Create Users
    with open(users_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['USER_ID', 'EMAIL', 'SOURCE', 'CONSENT'])
        for i in range(LARGE_USER_COUNT):
            writer.writerow([
                f'user_{i}', 
                f'donor_{i}@example.com',
                'ORGANIC',
                random.random() > 0.2 # 80% consent rate
            ])
            
    # Create Interactions (Ensuring > 1000 for Personalize)
    with open(interactions_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['USER_ID', 'ITEM_ID', 'TIMESTAMP', 'EVENT_TYPE'])
        for i in range(MAX_INTERACTIONS := max(LARGE_USER_COUNT * 5, MIN_ML_INTERACTIONS + 100)):
            # Simulating some bias for ML to pick up
            user_idx = random.randint(0, LARGE_USER_COUNT-1)
            # Users 0-500 like Clean Water, others random
            if user_idx < 500:
                item = random.choice(['CLEAN_WATER', 'ENVIRONMENT']) if random.random() > 0.3 else random.choice(ITEMS)
            else:
                item = random.choice(ITEMS)
                
            writer.writerow([
                f'user_{user_idx}',
                item,
                int(time.time()) - random.randint(0, 10**7),
                random.choice(EVENT_TYPES)
            ])

if __name__ == "__main__":
    output_dir = Path("datasets")
    output_dir.mkdir(exist_ok=True)
    
    print("Generating Small Nonprofit Dataset...")
    generate_small_nonprofit(output_dir)
    
    print("Generating Large Nonprofit Dataset...")
    generate_large_nonprofit(output_dir)
    
    print(f"Datasets generated in {output_dir}/")
