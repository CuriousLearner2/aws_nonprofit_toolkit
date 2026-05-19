import boto3
import argparse
import logging
import time
import os
from dotenv import load_dotenv

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("personalize_batch")

load_dotenv()

def trigger_batch_inference_job(solution_version_arn: str, input_s3_path: str, output_s3_path: str, role_arn: str):
    """Triggers an Amazon Personalize Batch Inference Job."""
    client = boto3.client(
        'personalize',
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION", "us-east-1")
    )
    
    job_name = f"BatchInference-{int(time.time())}"
    try:
        response = client.create_batch_inference_job(
            jobName=job_name,
            solutionVersionArn=solution_version_arn,
            jobInput={'s3DataSource': {'path': input_s3_path}},
            jobOutput={'s3DataDestination': {'path': output_s3_path}},
            roleArn=role_arn
        )
        logger.info(f"SUCCESS: Batch job triggered. Job ARN: {response['batchInferenceJobArn']}")
        return response['batchInferenceJobArn']
    except Exception as e:
        logger.error(f"Failed to trigger batch job: {e}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trigger Personalize Batch Inference.")
    parser.add_argument("--solution-version-arn", required=True)
    parser.add_argument("--input-data", required=True, help="s3://bucket/input.json")
    parser.add_argument("--output-s3", required=True, help="s3://bucket/results/")
    parser.add_argument("--role-arn", required=True)
    
    args = parser.parse_args()
    
    trigger_batch_inference_job(
        args.solution_version_arn, 
        args.input_data, 
        args.output_s3, 
        args.role_arn
    )
