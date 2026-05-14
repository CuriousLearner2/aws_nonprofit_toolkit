import os
import json
import logging
import requests
from pathlib import Path
from botocore.exceptions import ClientError
from aws_nonprofit_toolkit.generate_datasets import generate_small_nonprofit, generate_large_nonprofit
from aws_nonprofit_toolkit.config import SimulationConfig
from aws_nonprofit_toolkit.uncover_signal_no_pandas import analyze_bias
from aws_nonprofit_toolkit.audit_seed_quality import run_audit
from aws_nonprofit_toolkit.meta_growth_engine import create_custom_audience, upload_donors_to_audience, create_lookalike_audience
from aws_nonprofit_toolkit.personalize_sync import upload_to_s3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """
    AWS Lambda handler to run the daily synchronization lifecycle.
    Configurable via environment variables: DONOR_COUNT, BIAS_RATIO
    """
    tmp_dir = Path("/tmp/datasets")
    tmp_dir.mkdir(exist_ok=True)

    # Load configuration from environment (with defaults)
    donor_count = int(os.getenv("DONOR_COUNT", "2000"))
    bias_ratio = float(os.getenv("BIAS_RATIO", "0.25"))

    try:
        # 1. Generate Latest Synthetic Data (Dual-Track Pipeline)
        logger.info("Step 1/5: Generating synthetic data (Dual-Track)...")
        logger.info(f"Configuration: count={donor_count}, bias_ratio={bias_ratio}")

        # Track 1: Small dataset (Acquisition - Meta seeding)
        logger.info("  - Track 1: Generating small dataset for Meta seeding...")
        generate_small_nonprofit(tmp_dir, SimulationConfig.SMALL_USER_COUNT)

        # Track 2: Large dataset (Personalization - ML training)
        logger.info("  - Track 2: Generating large dataset for ML training...")
        generate_large_nonprofit(tmp_dir, count=donor_count, bias_ratio=bias_ratio)

        small_users_path = tmp_dir / "small_nonprofit_users.csv"
        interactions_path = tmp_dir / "large_nonprofit_interactions.csv"
        
        # 2. Validate Signal Strength (Dual-Track Validation)
        logger.info("Step 2/5: Validating signal strength (Dual-Track)...")
        
        # Track 1 Validation (Meta Seed)
        if not run_audit(str(small_users_path), concentration_threshold=0.60):
            error_msg = "Meta seed concentration too weak (< 60%). Sync aborted."
            logger.error(f"FATAL: {error_msg}")
            raise ValueError(error_msg)

        # Track 2 Validation (ML training data)
        if not analyze_bias(str(interactions_path), threshold=20.0, count=donor_count, bias_ratio=bias_ratio):
            error_msg = "ML interaction signal too weak (< 20%). Sync aborted."
            logger.error(f"FATAL: {error_msg}")
            raise ValueError(error_msg)

        # 3. Sync Track 1: Meta (Acquisition)
        logger.info("Step 3/5: Syncing Track 1 (small dataset VIPs to Meta)...")
        aud_id = create_custom_audience("Daily VIP Sync")
        upload_donors_to_audience(aud_id, str(small_users_path))
        
        # Automated Lookalike (Safety Check: Sandbox/Dry-Run only in this phase)
        sandbox_id = os.getenv("META_SANDBOX_AD_ACCOUNT_ID")
        if sandbox_id:
            logger.info("  - Sandbox detected. Triggering automated 1% Lookalike...")
            create_lookalike_audience(
                aud_id, 
                sandbox_id, 
                "Daily VIP Lookalike (1%)"
            )
        else:
            logger.info("  - Skipping automated Lookalike (Production safety enabled).")

        # 4. Sync Track 2: S3/Personalize (Personalization)
        logger.info("Step 4/5: Syncing Track 2 (large dataset to S3 for ML)...")
        bucket = os.getenv("AWS_PERSONALIZE_BUCKET")
        upload_to_s3(str(interactions_path), bucket)
        
        return {
            'statusCode': 200,
            'body': json.dumps('Daily dual-track pipeline synchronization successful.')
        }
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        logger.error(f"FATAL: AWS Service Error (Code: {error_code}): {str(e)}")
        raise e
    except requests.RequestException as e:
        logger.error(f"FATAL: Meta API Network Error: {str(e)}")
        raise e
    except ValueError as e:
        logger.error(f"FATAL: {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"FATAL: Unexpected System Error: {str(e)}")
        raise e
