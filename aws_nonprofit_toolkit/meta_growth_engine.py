import csv
import requests
import hashlib
import json
import time
import os
import logging
import argparse
from typing import Optional, List, Dict, Any, Tuple
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
    API_VERSION = "v21.0"
    
    @classmethod
    def get_credentials(cls, use_sandbox: bool = False):
        """Fetch latest credentials from environment."""
        token = os.getenv("META_ACCESS_TOKEN")
        account_id = os.getenv("META_SANDBOX_AD_ACCOUNT_ID") if use_sandbox else os.getenv("META_AD_ACCOUNT_ID")
        return token, account_id

    @classmethod
    def validate(cls, use_sandbox: bool = False):
        token, account_id = cls.get_credentials(use_sandbox)
        if not token or not account_id:
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
def get_custom_audience_by_name(name: str, ad_account_id: str) -> Optional[str]:
    """Checks if a Custom Audience with the given name already exists."""
    token, _ = MetaConfig.get_credentials() 
    url = f"https://graph.facebook.com/{MetaConfig.API_VERSION}/act_{ad_account_id}/customaudiences"
    params = {'fields': 'name,id', 'access_token': token}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        audiences = response.json().get('data', [])
        for aud in audiences:
            if aud.get('name') == name:
                logger.info(f"Found existing audience '{name}' (ID: {aud.get('id')})")
                return aud.get('id')
        return None
    except Exception as e:
        logger.error(f"Failed to fetch audiences: {str(e)}")
        raise

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    reraise=True
)
def create_custom_audience(name: str, ad_account_id: Optional[str] = None, dry_run: bool = False) -> Optional[str]:
    """Creates a Custom Audience on Meta, or returns existing if name matches."""
    token, env_account_id = MetaConfig.get_credentials(use_sandbox=(ad_account_id is not None))
    ad_account_id = ad_account_id or env_account_id
    
    if not token or not ad_account_id:
        raise ValueError("Missing Meta credentials.")

    if not dry_run:
        existing_id = get_custom_audience_by_name(name, ad_account_id)
        if existing_id:
            return existing_id

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
        'access_token': token
    }

    try:
        response = requests.post(url, data=payload, timeout=15)
        response.raise_for_status()
        return response.json().get('id')
    except Exception as e:
        logger.error(f"Failed to create audience: {str(e)}")
        raise

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    reraise=True
)
def get_audience_details(audience_id: str, use_sandbox: bool = False) -> Optional[dict]:
    """Fetch audience metadata with correct credential toggle."""
    token, _ = MetaConfig.get_credentials(use_sandbox=use_sandbox)
    url = f"https://graph.facebook.com/{MetaConfig.API_VERSION}/{audience_id}"
    params = {'fields': 'id,name,subtype,approximate_count,status', 'access_token': token}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch audience {audience_id}: {str(e)}")
        return None

def wait_for_audience_uploadable(audience_id: str, use_sandbox: bool = False, max_wait_seconds: int = 360, poll_interval: int = 120) -> bool:
    """Poll audience until status is 'READY' for data upload (Max 6 mins, 2 min interval)."""
    start_time = time.time()
    while time.time() - start_time < max_wait_seconds:
        details = get_audience_details(audience_id, use_sandbox=use_sandbox)
        if not details: return False
        
        # Audience status can be 'READY', 'BUILDING', etc.
        status = details.get('status')
        logger.info(f"Audience {audience_id}: status={status}")
        
        # We look for a state that permits upload (often 'READY')
        if status in ['READY', 'ACTIVE']:
            logger.info("Audience is ready for upload.")
            return True
        
        time.sleep(poll_interval)
    logger.error("Audience failed to reach uploadable status in time.")
    return False

def wait_for_audience_ready(audience_id: str, expected_count: int, use_sandbox: bool = False, max_wait_seconds: int = 3600, poll_interval: int = 600) -> bool:
    """Poll audience until status is 'READY' for lookalike creation."""
    start_time = time.time()
    while time.time() - start_time < max_wait_seconds:
        details = get_audience_details(audience_id, use_sandbox=use_sandbox)
        if not details: return False
        
        status = details.get('status')
        approximate_count = details.get('approximate_count', 0)
        logger.info(f"Audience {audience_id}: status={status}, size={approximate_count}")
        
        if status == 'READY':
            match_rate = (approximate_count / expected_count) if expected_count > 0 else 0
            if match_rate >= 0.40:
                logger.info(f"Audience ready. Match rate: {match_rate:.1%}")
                return True
            else:
                logger.error(f"Match rate {match_rate:.1%} < 40%. Sync aborted.")
                return False
        time.sleep(poll_interval)
    return False

def delete_custom_audience(audience_id: str, ad_account_id: str):
    """Deletes a Custom Audience."""
    token, _ = MetaConfig.get_credentials()
    url = f"https://graph.facebook.com/{MetaConfig.API_VERSION}/{audience_id}"
    params = {'access_token': token}
    try:
        requests.delete(url, params=params, timeout=10).raise_for_status()
        logger.info(f"Successfully deleted audience {audience_id}")
    except Exception as e:
        logger.error(f"Failed to delete audience {audience_id}: {str(e)}")
        raise

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    reraise=True
)
def create_lookalike_audience(seed_audience_id: str, ad_account_id: str, name: str, dry_run: bool = False) -> Optional[str]:
    """Creates a 1% Lookalike Audience from a seed audience."""
    token, _ = MetaConfig.get_credentials(use_sandbox=True)
    if dry_run:
        logger.info(f"[DRY-RUN] Would create 1% Lookalike for seed {seed_audience_id}")
        return "dry_run_lookalike_id"
    url = f"https://graph.facebook.com/{MetaConfig.API_VERSION}/act_{ad_account_id}/customaudiences"
    lookalike_spec = {'type': 'similarity', 'ratio': 0.01, 'location_spec': {'geo_locations': {'countries': ['US']}}}
    payload = {
        'name': name,
        'subtype': 'LOOKALIKES',
        'origin_audience_id': seed_audience_id,
        'lookalike_spec': json.dumps(lookalike_spec),
        'access_token': token
    }
    response = requests.post(url, data=payload, timeout=15)
    response.raise_for_status()
    return response.json().get('id')

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    reraise=True
)
def upload_donors_to_audience(audience_id: str, users_file: str, batch_size: int = 5000, dry_run: bool = False) -> int:
    """Uploads hashed emails to a specific Meta audience and returns VIP count."""
    token, _ = MetaConfig.get_credentials()
    if not os.path.exists(users_file):
        logger.error(f"File not found: {users_file}")
        return 0
    
    upload_data = []
    with open(users_file, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('LOYALTY_LEVEL') == 'VIP' and row.get('EMAIL'):
                email_hash = hash_data(row['EMAIL'])
                ltv = row.get('LTV', '0')
                upload_data.append([email_hash, ltv])
    
    total_count = len(upload_data)
    if total_count == 0: return 0
    if dry_run: return total_count

    url = f"https://graph.facebook.com/{MetaConfig.API_VERSION}/{audience_id}/users"
    for i in range(0, total_count, batch_size):
        batch = upload_data[i:i + batch_size]
        payload = {
            'payload': json.dumps({'schema': ['EMAIL', 'LOOKALIKES_VALUE'], 'data': batch}),
            'access_token': token
        }
        
        requests.post(url, data=payload, timeout=30).raise_for_status()
        logger.info(f"Batch {i//batch_size + 1} synced.")
    return total_count

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--audience-name", type=str, default="VIP Donors (Toolkit)")
    parser.add_argument("--users-file", type=str, default="aws_nonprofit_toolkit/datasets/small_nonprofit_users.csv")
    parser.add_argument("--sandbox", action="store_true")
    parser.add_argument("--create-lookalike", action="store_true")
    args = parser.parse_args()
    
    try:
        target_account_id = MetaConfig.validate(use_sandbox=args.sandbox)
        aud_id = create_custom_audience(args.audience_name, target_account_id)
        if aud_id and wait_for_audience_uploadable(aud_id, use_sandbox=args.sandbox):
            vip_count = upload_donors_to_audience(aud_id, args.users_file)
            logger.info(f"Uploaded {vip_count} VIP donors.")
            
            if wait_for_audience_ready(aud_id, vip_count, use_sandbox=args.sandbox):
                 if args.create_lookalike:
                     lla_id = create_lookalike_audience(aud_id, target_account_id, "Lookalike (1%)")
                     if lla_id:
                         logger.info(f"Lookalike created: {lla_id}")
    except Exception as e:
        logger.critical(f"Toolkit process failed: {str(e)}")
