#!/usr/bin/env python3
"""
Phase 1 Step 2: Run Batch Inference to Score All Donors

This script:
1. Takes the trained model ARN from Phase 1
2. Creates a batch inference job
3. Generates engagement scores for all donors
4. Saves results to S3 and locally

Usage:
    python3 phase1_batch_inference.py <solution-version-arn>

Example:
    python3 phase1_batch_inference.py arn:aws:personalize:us-east-1:...:solution-version/...
"""

import boto3
import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Load credentials
env_path = Path(".env")
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ[key] = value

# Configuration
REGION = "us-east-1"
BUCKET = os.getenv("AWS_PERSONALIZE_BUCKET")
DATASET_GROUP_ARN = "arn:aws:personalize:us-east-1:684039303576:dataset-group/nonprofit-donors-1779321550"

personalize = boto3.client(
    "personalize",
    region_name=REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)

s3 = boto3.client(
    "s3",
    region_name=REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)


def get_iam_role_arn() -> str:
    """Get IAM role ARN for Personalize."""
    return "arn:aws:iam::684039303576:role/AmazonPersonalizeRole"


def prepare_batch_input(input_file: str = "datasets/small_nonprofit_users.csv") -> str:
    """
    Prepare batch input file (one USER_ID per line for item-affinity recipe).

    For aws-item-affinity recipe, we need just USER_IDs to generate
    recommendations for all items (causes).
    """
    import csv

    # Extract USER_IDs from input file
    user_ids = []
    with open(input_file) as f:
        reader = csv.DictReader(f)
        for row in reader:
            user_ids.append(row['USER_ID'])

    # Write batch input file (one per line for personalize batch)
    batch_input_file = "batch_input.json"
    with open(batch_input_file, 'w') as f:
        for user_id in user_ids:
            # Format for aws-item-affinity batch inference
            f.write(json.dumps({"userID": user_id}) + "\n")

    print(f"✓ Batch input prepared: {batch_input_file} ({len(user_ids)} users)")
    return batch_input_file


def upload_batch_input_to_s3(batch_input_file: str) -> str:
    """Upload batch input file to S3."""
    timestamp = int(time.time())
    s3_key = f"personalize/batch_input/phase1_{timestamp}.json"

    with open(batch_input_file, 'rb') as f:
        s3.put_object(Bucket=BUCKET, Key=s3_key, Body=f)

    s3_uri = f"s3://{BUCKET}/{s3_key}"
    print(f"✓ Batch input uploaded to S3: {s3_uri}")
    return s3_uri


def create_batch_inference_job(solution_version_arn: str, input_s3: str) -> str:
    """
    Create and start batch inference job.

    Args:
        solution_version_arn: Trained model ARN
        input_s3: S3 path to batch input file

    Returns:
        Batch job ARN
    """
    timestamp = int(time.time())
    output_s3 = f"s3://{BUCKET}/personalize/batch_output/phase1_{timestamp}/"
    job_name = f"phase1-batch-{timestamp}"

    response = personalize.create_batch_inference_job(
        jobName=job_name,
        solutionVersionArn=solution_version_arn,
        jobInput={"s3DataSource": {"path": input_s3}},
        jobOutput={"s3DataDestination": {"path": output_s3}},
        roleArn=get_iam_role_arn()
    )

    job_arn = response['batchInferenceJobArn']
    print(f"✓ Batch inference job created: {job_arn}")
    print(f"  Input: {input_s3}")
    print(f"  Output: {output_s3}")
    return job_arn, output_s3


def wait_for_batch_job(job_arn: str, timeout_minutes: int = 30) -> bool:
    """Monitor batch inference job."""
    start_time = time.time()
    timeout_seconds = timeout_minutes * 60

    while True:
        response = personalize.describe_batch_inference_job(
            batchInferenceJobArn=job_arn
        )
        status = response['batchInferenceJob']['status']
        elapsed = int((time.time() - start_time) / 60)

        if status == "ACTIVE":
            print(f"✓ Batch inference COMPLETE ({elapsed} minutes)")
            return True
        elif status == "CREATE_FAILED":
            error = response['batchInferenceJob'].get('failureReason', 'Unknown')
            print(f"✗ Batch job FAILED: {error}")
            return False
        else:
            print(f"  [{elapsed} min] Status: {status}")
            time.sleep(30)

            if time.time() - start_time > timeout_seconds:
                print(f"⚠ Timeout after {timeout_minutes} minutes.")
                return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 phase1_batch_inference.py <solution-version-arn>")
        print("\nExample:")
        print("  python3 phase1_batch_inference.py arn:aws:personalize:us-east-1:...:solution-version/...")
        sys.exit(1)

    solution_version_arn = sys.argv[1]

    print("=" * 70)
    print("PHASE 1 STEP 2: BATCH INFERENCE")
    print("=" * 70)

    # Step 1: Prepare batch input
    print(f"\n[1/4] Preparing batch input file...")
    batch_input_file = prepare_batch_input()

    # Step 2: Upload to S3
    print(f"\n[2/4] Uploading to S3...")
    input_s3 = upload_batch_input_to_s3(batch_input_file)

    # Step 3: Create batch job
    print(f"\n[3/4] Starting batch inference job...")
    job_arn, output_s3 = create_batch_inference_job(solution_version_arn, input_s3)

    # Step 4: Wait for completion
    print(f"\n[4/4] Monitoring batch job...")
    success = wait_for_batch_job(job_arn)

    if success:
        print(f"\n✓ Batch inference complete!")
        print(f"\n  Results location: {output_s3}")
        print(f"\n  Next step: python3 phase1_extract_segments.py '{output_s3}'")
    else:
        print(f"\n⚠ Batch inference incomplete.")
        print(f"  Job ARN: {job_arn}")

    print("=" * 70)


if __name__ == "__main__":
    main()
