import os
import json
import logging
import requests
from pathlib import Path
from botocore.exceptions import ClientError
from aws_nonprofit_toolkit.generate_datasets import generate_small_nonprofit, generate_large_nonprofit
from aws_nonprofit_toolkit.config import SimulationConfig
from aws_nonprofit_toolkit.uncover_signal_no_pandas import analyze_bias
from aws_nonprofit_toolkit.meta_growth_engine import create_custom_audience, upload_donors_to_audience
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
        
        # 2. Validate Signal Strength (for ML training data)
        logger.info("Step 2/5: Validating ML signal strength...")
        if not analyze_bias(str(interactions_path), threshold=20.0, count=donor_count, bias_ratio=bias_ratio):
            error_msg = "Signal too weak (< 20%). Data not ready for Meta sync."
            logger.error(f"FATAL: {error_msg}")
            raise ValueError(error_msg)

        # 3. Sync Track 1: Meta (Acquisition)
        logger.info("Step 3/5: Syncing Track 1 (small dataset VIPs to Meta)...")
        aud_id = create_custom_audience("Daily VIP Sync")
        upload_donors_to_audience(aud_id, str(small_users_path))

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
