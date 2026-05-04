import csv
import requests
import hashlib
import json
import time
import os
import logging
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("meta_growth_engine")

# Load configuration
load_dotenv('replate/.env')

class MetaConfig:
    """Centralized configuration management for Meta API."""
    ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
    AD_ACCOUNT_ID = os.getenv("META_AD_ACCOUNT_ID")
    API_VERSION = "v21.0"
    
    @classmethod
    def validate(cls):
        if not cls.ACCESS_TOKEN or not cls.AD_ACCOUNT_ID:
            raise ValueError("Missing META_ACCESS_TOKEN or META_AD_ACCOUNT_ID in environment.")

def hash_data(data: str) -> str:
    """
    Meta requires data to be SHA256 hashed before upload.
    Compliance: No raw PII is sent to Meta servers.
    """
    return hashlib.sha256(data.strip().lower().encode()).hexdigest()

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(requests.exceptions.RequestException)
)
def create_custom_audience(name: str = "VIP Donors (Replate Growth Lab)") -> Optional[str]:
    """Creates a Custom Audience on Meta with retry logic."""
    MetaConfig.validate()
    
    logger.info("Creating Custom Audience on Meta...")
    url = f"https://graph.facebook.com/{MetaConfig.API_VERSION}/act_{MetaConfig.AD_ACCOUNT_ID}/customaudiences"
    
    payload = {
        'name': name,
        'subtype': 'CUSTOM',
        'description': 'High-value donors for lookalike seed',
        'customer_file_source': 'USER_PROVIDED_ONLY',
        'access_token': MetaConfig.ACCESS_TOKEN
    }
    
    try:
        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        audience_id = result.get('id')
        if audience_id:
            logger.info("SUCCESS: Created Audience ID (sanitized)")
            return audience_id
    except requests.exceptions.HTTPError as e:
        logger.error(f"Meta API Error (HTTP {response.status_code}): {response.text}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error creating audience: {str(e)}")
        raise

    return None

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(requests.exceptions.RequestException)
)
def upload_donors_to_audience(audience_id: str, users_file: str):
    """Extracts VIPs and uploads hashed emails to a specific Meta audience."""
    if not os.path.exists(users_file):
        logger.error(f"File not found: {users_file}")
        return

    logger.info(f"Uploading VIPs from {users_file}...")
    
    # Extract VIP emails
    hashed_emails = []
    try:
        with open(users_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('LOYALTY_LEVEL') == 'VIP' and row.get('EMAIL'):
                    hashed_emails.append([hash_data(row['EMAIL'])])
    except Exception as e:
        logger.error(f"Error reading users file: {str(e)}")
        return

    if not hashed_emails:
        logger.warning("No VIP donors found to upload.")
        return

    logger.info(f"Found {len(hashed_emails)} VIP donors. Syncing with Meta...")
    
    url = f"https://graph.facebook.com/{MetaConfig.API_VERSION}/{audience_id}/users"
    
    payload = {
        'payload': json.dumps({
            'schema': ['EMAIL'],
            'data': hashed_emails
        }),
        'access_token': MetaConfig.ACCESS_TOKEN
    }
    
    try:
        response = requests.post(url, data=payload, timeout=30)
        response.raise_for_status()
        logger.info("SUCCESS: VIP list synchronized with Meta.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to upload donors: {str(e)}")
        raise

def simulate_lookalike_growth(original_count: int):
    """Logs simulated growth results for local validation."""
    logger.info("Simulating Lookalike Growth (WhatsApp Conversion)...")
    logger.info("Meta ML is now finding people who 'look like' your VIPs...")
    time.sleep(1)
    
    new_users_count = 50
    logger.info(f"RESULT: {new_users_count} new users joined via 'Click-to-WhatsApp' Ads!")
    
    print("-" * 30)
    print(f"{'User ID':<10} | {'Source':<12} | {'Consent':<8}")
    print("-" * 30)
    for i in range(5):
        uid = f"user_{original_count + i}"
        print(f"{uid:<10} | {'META_LOOKALIK':<12} | {'True':<8}")
    print("...")
    print("-" * 30)
    logger.info("STRATEGY COMPLETE: Growth loop simulated successfully.")

if __name__ == "__main__":
    try:
        aud_id = create_custom_audience()
        if aud_id:
            upload_donors_to_audience(aud_id, "aws_nonprofit_toolkit/datasets/small_nonprofit_users.csv")
            simulate_lookalike_growth(200)
    except Exception as e:
        logger.critical(f"Toolkit process failed: {str(e)}")
