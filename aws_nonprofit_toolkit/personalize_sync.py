import boto3
import os
import logging
import argparse
from typing import Optional
from botocore.exceptions import ClientError
from tenacity import retry, stop_after_attempt, wait_exponential
from aws_nonprofit_toolkit.your_config import AWSConfig

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("personalize_sync")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10), reraise=True)
def upload_to_s3(file_path: str, bucket: str, object_name: Optional[str] = None):
    """Uploads a synthetic dataset to S3 for Amazon Personalize import using the personalize-sandbox profile."""
    if object_name is None:
        object_name = os.path.basename(file_path)

    # Use the profile configured via `aws configure --profile personalize-sandbox`
    session = boto3.Session(profile_name='personalize-sandbox')
    s3_client = session.client('s3', region_name=AWSConfig.REGION)

    try:
        logger.info(f"Uploading {file_path} to s3://{bucket}/{object_name} using personalize-sandbox profile...")
        s3_client.upload_file(file_path, bucket, object_name)
        logger.info("SUCCESS: File uploaded to S3.")
    except ClientError as e:
        logger.error(f"S3 Upload failed: {e}")
        raise

def trigger_personalize_import(dataset_arn: str, s3_path: str, role_arn: str):
    """Triggers an Amazon Personalize Dataset Import Job."""
    personalize = boto3.client(
        'personalize',
        aws_access_key_id=AWSConfig.ACCESS_KEY,
        aws_secret_access_key=AWSConfig.SECRET_KEY,
        region_name=AWSConfig.REGION
    )

    try:
        logger.info(f"Triggering Personalize Import Job for {s3_path}...")
        response = personalize.create_dataset_import_job(
            jobName=f"PersonalizeImport-{os.path.basename(s3_path)}",

            datasetArn=dataset_arn,
            dataSource={'dataLocation': f"s3://{AWSConfig.S3_BUCKET}/{s3_path}"},
            roleArn=role_arn
        )
        logger.info(f"SUCCESS: Import job triggered. Job ARN: {response['datasetImportJobArn']}")
        return response['datasetImportJobArn']
    except ClientError as e:
        logger.error(f"Personalize Import failed: {e}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload datasets to Amazon S3 and trigger Personalize Import.")
    parser.add_argument("--dataset", type=str, default="aws_nonprofit_toolkit/datasets/large_nonprofit_interactions.csv", help="Path to CSV dataset")
    parser.add_argument("--bucket", type=str, help="S3 bucket name (overrides .env)")
    parser.add_argument("--s3-path", type=str, help="Destination path in S3 (e.g., data/interactions.csv)")
    parser.add_argument("--dataset-arn", type=str, help="Amazon Personalize Dataset ARN (to trigger import)")
    parser.add_argument("--role-arn", type=str, help="IAM Role ARN with Personalize access")
    
    args = parser.parse_args()
    
    # ... (args parsing setup) ...
    
    target_bucket = args.bucket or AWSConfig.BUCKET
    s3_path = args.s3_path or os.path.basename(args.dataset)
    
    try:
        # Step 1: Upload to S3
        upload_to_s3(args.dataset, target_bucket, object_name=s3_path)
        
        # Step 2: Trigger Personalize Import (Optional based on ARNs)
        if args.dataset_arn and args.role_arn:
            trigger_personalize_import(args.dataset_arn, s3_path, args.role_arn)
        else:
            logger.info("SKIP: Personalize import not triggered (Missing --dataset-arn or --role-arn).")
            logger.info("Data is ready in S3. Use the AWS Console to finish synchronization.")

        logger.info("Sync process completed.")
    except Exception as e:
        logger.error(f"Personalize sync failed: {e}")
