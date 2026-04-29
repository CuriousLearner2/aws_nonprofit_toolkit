import csv
import requests
import hashlib
import json
import time
import os
from dotenv import load_dotenv

# Load from replate/.env (assuming script is run from project root)
load_dotenv('replate/.env')

# Meta Configuration
ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
AD_ACCOUNT_ID = "1475686827393876"
API_VERSION = "v21.0"

def hash_data(data):
    """Meta requires data to be SHA256 hashed before upload for privacy."""
    return hashlib.sha256(data.strip().lower().encode()).hexdigest()

def create_custom_audience():
    print(f"--- STEP 1: Creating Custom Audience on Meta ---")
    url = f"https://graph.facebook.com/{API_VERSION}/act_{AD_ACCOUNT_ID}/customaudiences"
    
    payload = {
        'name': 'VIP Donors (Replate Growth Lab)',
        'subtype': 'CUSTOM',
        'description': 'High-value donors for lookalike seed',
        'customer_file_source': 'USER_PROVIDED_ONLY',
        'access_token': ACCESS_TOKEN
    }
    
    response = requests.post(url, data=payload)
    result = response.json()
    
    if 'id' in result:
        audience_id = result['id']
        print(f"SUCCESS: Created Audience ID {audience_id}")
        return audience_id
    else:
        print(f"ERROR: {result}")
        return None

def upload_donors_to_audience(audience_id, users_file):
    print(f"\n--- STEP 2: Uploading VIPs from {users_file} ---")
    
    # Extract VIP emails
    hashed_emails = []
    with open(users_file, mode='r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['LOYALTY_LEVEL'] == 'VIP':
                hashed_emails.append([hash_data(row['EMAIL'])])
    
    print(f"Found {len(hashed_emails)} VIP donors. Uploading to Meta...")
    
    url = f"https://graph.facebook.com/{API_VERSION}/{audience_id}/users"
    
    payload = {
        'payload': json.dumps({
            'schema': ['EMAIL'],
            'data': hashed_emails
        }),
        'access_token': ACCESS_TOKEN
    }
    
    response = requests.post(url, data=payload)
    print(f"RESPONSE: {response.json()}")

def simulate_lookalike_growth(original_count):
    print(f"\n--- STEP 3: Simulating Lookalike Growth (WhatsApp Conversion) ---")
    print("Meta ML is now finding people who 'look like' your VIPs...")
    time.sleep(1)
    
    new_users = 50 # Let's say we converted 50 new donors from the Lookalike ad
    print(f"RESULT: 50 new users joined via 'Click-to-WhatsApp' Ads!")
    
    # Show how this data looks in our system now
    print("-" * 30)
    print(f"{'User ID':<10} | {'Source':<12} | {'Consent':<8}")
    print("-" * 30)
    for i in range(5):
        uid = f"user_{original_count + i}"
        print(f"{uid:<10} | {'META_LOOKALIK':<12} | {'True':<8}")
    print("...")
    print("-" * 30)
    print("STRATEGY COMPLETE: You have expanded your donor base by targeting the networks of your VIPs.")

if __name__ == "__main__":
    # 1. Create the sandbox audience
    aud_id = create_custom_audience()
    
    if aud_id:
        # 2. Upload our synthetic VIPs
        upload_donors_to_audience(aud_id, "aws_nonprofit_toolkit/datasets/small_nonprofit_users.csv")
        
        # 3. Simulate the downstream effect
        simulate_lookalike_growth(200) # Assuming we started with 200 users
