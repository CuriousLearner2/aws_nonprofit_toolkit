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
def get_custom_audience_by_name(name: str, ad_account_id: str) -> Optional[str]:
    """Checks if a Custom Audience with the given name already exists."""
    url = f"https://graph.facebook.com/{MetaConfig.API_VERSION}/act_{ad_account_id}/customaudiences"
    params = {
        'fields': 'name,id',
        'access_token': MetaConfig.ACCESS_TOKEN
    }
    
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
    MetaConfig.validate()

    if ad_account_id is None:
        ad_account_id = MetaConfig.AD_ACCOUNT_ID

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
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    reraise=True
)
def get_audience_details(audience_id: str, ad_account_id: str) -> Optional[dict]:
    """Fetch audience metadata to verify it exists and check its properties."""
    MetaConfig.validate()

    url = f"https://graph.facebook.com/{MetaConfig.API_VERSION}/{audience_id}"
    params = {
        'fields': 'id,name,subtype,approximate_count,data_source,status',
        'access_token': MetaConfig.ACCESS_TOKEN
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch audience {audience_id}: {str(e)}")
        return None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    reraise=True
)
def wait_for_audience_ready(audience_id: str, ad_account_id: str, max_wait_seconds: int = 600, poll_interval: int = 30) -> bool:
    """Poll audience until status is 'READY' or timeout.

    Args:
        audience_id: The audience ID to monitor
        ad_account_id: The ad account ID
        max_wait_seconds: Maximum seconds to wait (default: 10 minutes)
        poll_interval: Seconds between polls (default: 30)

    Returns:
        True if audience becomes READY, False if timeout or error

    Status progression:
        BUILDING → READY (usually 5-30 minutes in sandbox)
    """
    import time

    start_time = time.time()
    poll_count = 0

    while time.time() - start_time < max_wait_seconds:
        details = get_audience_details(audience_id, ad_account_id)

        if not details:
            logger.error(f"Failed to fetch audience {audience_id}")
            return False

        status = details.get('status')
        approximate_count = details.get('approximate_count', 0)
        elapsed = int(time.time() - start_time)

        logger.info(f"Poll #{poll_count + 1} (elapsed {elapsed}s): status={status}, size={approximate_count}")

        if status == 'READY':
            logger.info(f"✓ Audience {audience_id} is READY after {elapsed} seconds")
            return True

        if status == 'PAUSED' or status == 'DELETED':
            logger.error(f"Audience {audience_id} has unexpected status: {status}")
            return False

        # Status is BUILDING, wait and poll again
        time.sleep(poll_interval)
        poll_count += 1

    logger.error(f"Audience {audience_id} did not reach READY status within {max_wait_seconds} seconds")
    return False


def verify_lookalike_created(audience_id: str, ad_account_id: str, expected_name: str) -> bool:
    """Verify that a lookalike audience was actually created."""
    details = get_audience_details(audience_id, ad_account_id)

    if not details:
        logger.error(f"Could not fetch audience {audience_id}")
        return False

    # Check it exists and is a lookalike
    is_lookalike = details.get('subtype') == 'LOOKALIKES'
    has_name = expected_name in details.get('name', '')
    has_size = details.get('approximate_count', 0) > 0

    logger.info(f"Audience {audience_id} verification:")
    logger.info(f"  - Name: {details.get('name')} (expected to contain '{expected_name}')")
    logger.info(f"  - Type: {details.get('subtype')} (is lookalike: {is_lookalike})")
    logger.info(f"  - Status: {details.get('status')}")
    logger.info(f"  - Approximate size: {details.get('approximate_count')}")

    if not is_lookalike:
        logger.error(f"Audience {audience_id} is not a lookalike (subtype={details.get('subtype')})")
        return False

    if not has_name:
        logger.warning(f"Audience name doesn't match. Got '{details.get('name')}', expected to contain '{expected_name}'")

    return True


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    reraise=True
)
def create_lookalike_audience(seed_audience_id: str, ad_account_id: str, name: str, dry_run: bool = False) -> Optional[str]:
    """
    Creates a 1% Lookalike Audience from a seed audience.
    NOTE: Only triggered in Sandbox/Development for this phase.
    Includes retry logic with exponential backoff for network resilience.
    """
    MetaConfig.validate()
    if dry_run:
        logger.info(f"[DRY-RUN] Would create 1% Lookalike for seed {seed_audience_id} in US")
        return "dry_run_lookalike_id"

    logger.info(f"Creating 1% Lookalike Audience from seed {seed_audience_id}...")
    url = f"https://graph.facebook.com/{MetaConfig.API_VERSION}/act_{ad_account_id}/customaudiences"
    
    # 1% similarity in the US
    lookalike_spec = {
        'type': 'similarity',
        'ratio': 0.01,
        'location_spec': {
            'geo_locations': {
                'countries': ['US'],
            },
        },
    }

    payload = {
        'name': name,
        'subtype': 'LOOKALIKES',
        'origin_audience_id': seed_audience_id,
        'lookalike_spec': json.dumps(lookalike_spec),
        'access_token': MetaConfig.ACCESS_TOKEN
    }
    
    try:
        response = requests.post(url, data=payload, timeout=15)
        response.raise_for_status()
        result = response.json()
        return result.get('id')
    except Exception as e:
        logger.error(f"Failed to create lookalike: {str(e)}")
        raise

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    reraise=True
)
def upload_donors_to_audience(audience_id: str, users_file: str, batch_size: int = 5000, dry_run: bool = False):
    """Uploads hashed emails to a specific Meta audience."""
    MetaConfig.validate()
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

                # Validate LTV is numeric and warn if missing for VIP
                if not ltv or ltv.strip() == '':
                    logger.warning(f"VIP donor {row.get('EMAIL')} missing LTV, using 0")
                    ltv = '0'
                else:
                    try:
                        float(ltv)  # Validate numeric
                    except ValueError:
                        logger.warning(f"Invalid LTV '{ltv}' for {row.get('EMAIL')}, using 0")
                        ltv = '0'

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
    parser.add_argument("--create-lookalike", action="store_true", help="Automatically trigger a 1%% lookalike (Sandbox only)")
    
    args = parser.parse_args()
    
    try:
        # Validate and get the correct account ID
        target_account_id = MetaConfig.validate(use_sandbox=args.sandbox)
        mode_str = "SANDBOX" if args.sandbox else "LIVE"
        logger.info(f"Starting sync in {mode_str} mode (Account: {target_account_id})")

        aud_id = create_custom_audience(args.audience_name, target_account_id, dry_run=args.dry_run)
        if aud_id:
            upload_donors_to_audience(aud_id, args.users_file, batch_size=args.batch_size, dry_run=args.dry_run)
            
            # Automated Lookalike (Safety Check: Only in Sandbox for now)
            if args.create_lookalike:
                if args.sandbox or args.dry_run:
                    lla_name = f"Lookalike (1%%) - {args.audience_name}"
                    create_lookalike_audience(aud_id, target_account_id, lla_name, dry_run=args.dry_run)
                else:
                    logger.warning("Automated Lookalike creation is restricted to SANDBOX mode to prevent unintended production spend.")

            logger.info("Sync process completed.")
    except Exception as e:
        logger.critical(f"Toolkit process failed: {str(e)}")
