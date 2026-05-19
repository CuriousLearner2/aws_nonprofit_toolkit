import boto3
import argparse
import logging
import sys
import time
from botocore.exceptions import ClientError
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("personalize_batch")

load_dotenv()

class PersonalizeBatchInference:
  """Interface with Amazon Personalize to trigger batch inference jobs."""

  def __init__(self, profile_name: str = 'personalize-sandbox', region: str = 'us-east-1'):
    self.session = boto3.Session(profile_name=profile_name)
    self.personalize = self.session.client('personalize', region_name=region)
    self.s3 = self.session.client('s3', region_name=region)
    self.region = region

  def validate_s3_path(self, s3_path: str) -> tuple:
    """Validates S3 path format and returns (bucket, key)."""
    if not s3_path.startswith('s3://'):
      raise ValueError(f"Invalid S3 path: {s3_path}. Must start with 's3://'")

    parts = s3_path[5:].split('/', 1)
    if len(parts) < 2:
      raise ValueError(f"Invalid S3 path: {s3_path}. Must be 's3://bucket/key'")

    bucket, key = parts
    if not bucket or not key:
      raise ValueError(f"Invalid S3 path: {s3_path}. Bucket and key cannot be empty")

    return bucket, key

  def validate_bucket_access(self, bucket: str):
    """Verify S3 bucket is accessible."""
    try:
      self.s3.head_bucket(Bucket=bucket)
      logger.info(f"✅ S3 bucket '{bucket}' is accessible")
    except ClientError as e:
      raise ValueError(f"Cannot access S3 bucket '{bucket}': {e}")

  @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10), reraise=True)
  def trigger_batch_inference_job(self, solution_version_arn: str, input_s3_path: str,
                                   output_s3_path: str, role_arn: str) -> str:
    """Triggers an Amazon Personalize Batch Inference Job with validation and retries."""
    # Validate inputs
    if not solution_version_arn or not role_arn:
      raise ValueError("solution_version_arn and role_arn are required")

    input_bucket, input_key = self.validate_s3_path(input_s3_path)
    output_bucket, output_key = self.validate_s3_path(output_s3_path)

    # Validate bucket access
    self.validate_bucket_access(input_bucket)
    if input_bucket != output_bucket:
      self.validate_bucket_access(output_bucket)

    job_name = f"BatchInference-{int(time.time())}"

    try:
      logger.info(f"Triggering Batch Inference Job: {job_name}")
      logger.info(f"  Input: {input_s3_path}")
      logger.info(f"  Output: {output_s3_path}")

      response = self.personalize.create_batch_inference_job(
        jobName=job_name,
        solutionVersionArn=solution_version_arn,
        jobInput={'s3DataSource': {'path': input_s3_path}},
        jobOutput={'s3DataDestination': {'path': output_s3_path}},
        roleArn=role_arn
      )

      job_arn = response['batchInferenceJobArn']
      logger.info(f"✅ SUCCESS: Batch job triggered. Job ARN: {job_arn}")
      return job_arn

    except ClientError as e:
      logger.error(f"Personalize API error: {e}")
      raise

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Trigger Amazon Personalize Batch Inference Job.")
  parser.add_argument("--solution-version-arn", required=True, help="ARN of trained solution version")
  parser.add_argument("--input-data", required=True, help="s3://bucket/path/to/input.json")
  parser.add_argument("--output-s3", required=True, help="s3://bucket/path/to/results/")
  parser.add_argument("--role-arn", required=True, help="IAM role ARN with Personalize permissions")

  args = parser.parse_args()

  try:
    inference = PersonalizeBatchInference()
    inference.trigger_batch_inference_job(
      args.solution_version_arn,
      args.input_data,
      args.output_s3,
      args.role_arn
    )
  except Exception as e:
    logger.error(f"Batch inference failed: {e}")
    sys.exit(1)
