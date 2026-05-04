import boto3
import os
import logging
from typing import Optional
from dotenv import load_dotenv
from botocore.exceptions import ClientError
from tenacity import retry, stop_after_attempt, wait_exponential

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("personalize_sync")

# Load configuration
load_dotenv('replate/.env')

class AWSConfig:
    ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
    SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    REGION = os.getenv("AWS_REGION", "us-east-1")
    S3_BUCKET = os.getenv("AWS_PERSONALIZ_BUCKET")
    
    @classmethod
    def validate(cls):
        if not all([cls.ACCESS_KEY, cls.SECRET_KEY, cls.S3_BUCKET]):
            raise ValueError("Missing AWS credentials or S3 bucket in environment.")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def upload_to_s3(file_path: str, object_name: Optional[str] = None):
    """Uploads a synthetic dataset to S3 for Amazon Personalize import."""
    AWSConfig.validate()
    
    if object_name is None:
        object_name = os.path.basename(file_path)

    s3_client = boto3.client(
        's3',
        aws_access_key_id=AWSConfig.ACCESS_KEY,
        aws_secret_access_key=AWSConfig.SECRET_KEY,
        region_name=AWSConfig.REGION
    )

    try:
        logger.info(f"Uploading {file_path} to s3://{AWSConfig.S3_BUCKET}/{object_name}...")
        s3_client.upload_file(file_path, AWSConfig.S3_BUCKET, object_name)
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
            jobName=f"ReplateImport-{os.path.basename(s3_path)}",
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
    # Example usage for local validation
    try:
        DATASET_PATH = "aws_nonprofit_toolkit/datasets/large_nonprofit_interactions.csv"
        if os.path.exists(DATASET_PATH):
            upload_to_s3(DATASET_PATH)
            print("\nREADY: Data is in S3. Use the AWS Console or trigger_personalize_import() to sync.")
        else:
            logger.error(f"Dataset not found at {DATASET_PATH}. Run generate_datasets.py first.")
    except Exception as e:
        logger.error(f"Sync process failed: {e}")
