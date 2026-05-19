import boto3
import os
import logging
import argparse
from typing import Optional
from botocore.exceptions import ClientError
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("personalize_sync")

# Load configuration
load_dotenv()

class PersonalizeSync:
    def __init__(self, profile_name: str = 'personalize-sandbox', region: str = 'us-east-1'):
        self.session = boto3.Session(profile_name=profile_name)
        self.s3 = self.session.client('s3', region_name=region)
        self.personalize = self.session.client('personalize', region_name=region)
        self.region = region

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10), reraise=True)
    def upload_to_s3(self, file_path: str, bucket: str, object_name: Optional[str] = None):
        """Uploads a dataset to S3."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Dataset not found at {file_path}")
            
        object_name = object_name or os.path.basename(file_path)
        try:
            logger.info(f"Uploading {file_path} to s3://{bucket}/{object_name}...")
            self.s3.head_bucket(Bucket=bucket) # Validate bucket access
            self.s3.upload_file(file_path, bucket, object_name)
            logger.info("SUCCESS: File uploaded to S3.")
        except ClientError as e:
            logger.error(f"S3 Upload failed: {e}")
            raise

    def trigger_personalize_import(self, dataset_arn: str, s3_path: str, role_arn: str, bucket: str):
        """Triggers an Amazon Personalize Dataset Import Job."""
        try:
            logger.info(f"Triggering Personalize Import Job for {s3_path}...")
            response = self.personalize.create_dataset_import_job(
                jobName=f"PersonalizeImport-{int(os.path.basename(s3_path).split('.')[0])}",
                datasetArn=dataset_arn,
                dataSource={'dataLocation': f"s3://{bucket}/{s3_path}"},
                roleArn=role_arn
            )
            logger.info(f"SUCCESS: Import job triggered. Job ARN: {response['datasetImportJobArn']}")
            return response['datasetImportJobArn']
        except ClientError as e:
            logger.error(f"Personalize Import failed: {e}")
            raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload datasets to Amazon S3 and trigger Personalize Import.")
    parser.add_argument("--dataset", required=True, help="Path to CSV dataset")
    parser.add_argument("--bucket", required=True, help="S3 bucket name")
    parser.add_argument("--s3-path", help="Destination path in S3")
    parser.add_argument("--dataset-arn", help="Personalize Dataset ARN")
    parser.add_argument("--role-arn", help="IAM Role ARN")
    
    args = parser.parse_args()
    
    try:
        sync = PersonalizeSync()
        
        # Step 1: Upload
        sync.upload_to_s3(args.dataset, args.bucket, args.s3_path)
        
        # Step 2: Import
        if args.dataset_arn and args.role_arn:
            sync.trigger_personalize_import(args.dataset_arn, args.s3_path or os.path.basename(args.dataset), args.role_arn, args.bucket)
        else:
            logger.info("Data uploaded to S3. Skipping Personalize import (missing ARN arguments).")
            
    except Exception as e:
        logger.error(f"Sync process failed: {e}")
        sys.exit(1)
