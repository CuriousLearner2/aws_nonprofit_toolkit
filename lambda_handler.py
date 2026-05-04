import os
import json
import logging
import requests
from pathlib import Path
from botocore.exceptions import ClientError
from aws_nonprofit_toolkit.generate_datasets import generate_large_nonprofit
from aws_nonprofit_toolkit.meta_growth_engine import create_custom_audience, upload_donors_to_audience
from aws_nonprofit_toolkit.personalize_sync import upload_to_s3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """
    AWS Lambda handler to run the daily synchronization lifecycle.
    """
    tmp_dir = Path("/tmp/datasets")
    tmp_dir.mkdir(exist_ok=True)
    
    try:
        # 1. Generate Latest Synthetic Data
        logger.info("Step 1/3: Generating synthetic data...")
        generate_large_nonprofit(tmp_dir, count=2000, bias_ratio=0.25)
        
        interactions_path = tmp_dir / "large_nonprofit_interactions.csv"
        users_path = tmp_dir / "large_nonprofit_users.csv"
        
        # 2. Sync to Meta
        logger.info("Step 2/3: Syncing VIPs to Meta...")
        aud_id = create_custom_audience("Daily VIP Sync")
        upload_donors_to_audience(aud_id, str(users_path))
        
        # 3. Sync to S3
        logger.info("Step 3/3: Uploading interactions to S3...")
        bucket = os.getenv("AWS_PERSONALIZ_BUCKET")
        upload_to_s3(str(interactions_path), bucket)
        
        return {
            'statusCode': 200,
            'body': json.dumps('Daily toolkit synchronization successful.')
        }
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        logger.error(f"FATAL: AWS Service Error (Code: {error_code}): {str(e)}")
        raise e
    except requests.RequestException as e:
        logger.error(f"FATAL: Meta API Network Error: {str(e)}")
        raise e
    except ValueError as e:
        logger.error(f"FATAL: Configuration Error: {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"FATAL: Unexpected System Error: {str(e)}")
        raise e
