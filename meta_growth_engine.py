import csv
import requests
import hashlib
import json
import time
import os
import logging
import argparse
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
load_dotenv()

class MetaConfig:
    """Centralized configuration management for Meta API."""
    ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
    AD_ACCOUNT_ID = os.getenv("META_AD_ACCOUNT_ID")
    SANDBOX_AD_ACCOUNT_ID = os.getenv("META_SANDBOX_AD_ACCOUNT_ID")
    API_VERSION = "v21.0"
    
    @classmethod
    def validate(cls, use_sandbox: bool = False):
        account_id = cls.SANDBOX_AD_ACCOUNT_ID if use_sandbox else cls.AD_ACCOUNT_ID
        if not cls.ACCESS_TOKEN or not account_id:
            mode = "SANDBOX" if use_sandbox else "LIVE"
            raise ValueError(f"Missing META_ACCESS_TOKEN or META_{mode}_AD_ACCOUNT_ID in environment.")
        return account_id

def hash_data(data: str) -> str:
    """Meta requires data to be SHA256 hashed before upload."""
    return hashlib.sha256(data.strip().lower().encode()).hexdigest()

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    reraise=True
)
def create_custom_audience(name: str, ad_account_id: str, dry_run: bool = False) -> Optional[str]:
    """Creates a Custom Audience on Meta."""
    if dry_run:
        logger.info(f"[DRY-RUN] Would create audience '{name}' in account {ad_account_id}")
        return "dry_run_audience_id"

    logger.info(f"Creating Custom Audience '{name}' on Meta (Account: act_{ad_account_id})...")
    url = f"https://graph.facebook.com/{MetaConfig.API_VERSION}/act_{ad_account_id}/customaudiences"
    
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
        return result.get('id')
    except Exception as e:
        logger.error(f"Failed to create audience: {str(e)}")
        raise

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    reraise=True
)
def upload_donors_to_audience(audience_id: str, users_file: str, batch_size: int = 5000, dry_run: bool = False):
    """Uploads hashed emails to a specific Meta audience."""
    if not os.path.exists(users_file):
        logger.error(f"File not found: {users_file}")
        return

    logger.info(f"Extracting VIPs from {users_file}...")
    
    upload_data = []
    with open(users_file, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('LOYALTY_LEVEL') == 'VIP' and row.get('EMAIL'):
                email_hash = hash_data(row['EMAIL'])
                # We include the LTV (Value) to enable Value-Based Lookalikes
                ltv = row.get('LTV', '0')
                upload_data.append([email_hash, ltv])

    total_count = len(upload_data)
    if not total_count:
        logger.warning("No VIP donors found.")
        return

    if dry_run:
        logger.info(f"[DRY-RUN] Would upload {total_count} records to {audience_id}")
        return

    logger.info(f"Syncing {total_count} VIPs in batches of {batch_size} (Value-Based)...")
    url = f"https://graph.facebook.com/{MetaConfig.API_VERSION}/{audience_id}/users"
    
    for i in range(0, total_count, batch_size):
        batch = upload_data[i:i + batch_size]
        payload = {
            'payload': json.dumps({'schema': ['EMAIL', 'LOOKALIKES_VALUE'], 'data': batch}),
            'access_token': MetaConfig.ACCESS_TOKEN
        }
        response = requests.post(url, data=payload, timeout=30)
        response.raise_for_status()
        logger.info(f"SUCCESS: Batch {i//batch_size + 1} synchronized.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync donors to Meta Custom Audiences.")
    parser.add_argument("--audience-name", type=str, default="VIP Donors (Toolkit)", help="Name of the Meta audience")
    parser.add_argument("--users-file", type=str, default="aws_nonprofit_toolkit/datasets/small_nonprofit_users.csv", help="Path to users CSV")
    parser.add_argument("--batch-size", type=int, default=5000, help="Batch size for uploads")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without calling Meta API")
    parser.add_argument("--sandbox", action="store_true", help="Use the Sandbox Ad Account")
    
    args = parser.parse_args()
    
    try:
        # Validate and get the correct account ID
        target_account_id = MetaConfig.validate(use_sandbox=args.sandbox)
        mode_str = "SANDBOX" if args.sandbox else "LIVE"
        logger.info(f"Starting sync in {mode_str} mode (Account: {target_account_id})")

        aud_id = create_custom_audience(args.audience_name, target_account_id, dry_run=args.dry_run)
        if aud_id:
            upload_donors_to_audience(aud_id, args.users_file, batch_size=args.batch_size, dry_run=args.dry_run)
            logger.info("Sync process completed.")
    except Exception as e:
        logger.critical(f"Toolkit process failed: {str(e)}")
