#!/usr/bin/env python3
"""
Phase 1 Setup: Create and populate USERS dataset for Personalize

This script:
1. Creates a USERS dataset schema
2. Creates a USERS dataset in the dataset group
3. Uploads donor data from CSV
4. Monitors import job

Usage:
    python3 phase1_setup_users_dataset.py
"""

import boto3
import os
import csv
import json
import time
from pathlib import Path
from datetime import datetime

# Load credentials
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ[key] = value

# Configuration
DATASET_GROUP_ARN = "arn:aws:personalize:us-east-1:684039303576:dataset-group/nonprofit-donors-1779321550"
REGION = "us-east-1"
BUCKET = os.getenv("AWS_PERSONALIZE_BUCKET")
USERS_CSV = "datasets/small_nonprofit_users.csv"

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


def create_users_schema() -> str:
    """Create a USERS dataset schema."""
    schema = {
        "type": "record",
        "name": "Users",
        "namespace": "com.amazon.personalize.schema",
        "fields": [
            {"name": "USER_ID", "type": "string"},
            {"name": "INTEREST_TAG", "type": ["string", "null"]},
            {"name": "LTV", "type": ["int", "null"]},
            {"name": "LOYALTY_LEVEL", "type": ["string", "null"]},
            {"name": "SOURCE", "type": ["string", "null"]},
        ],
        "version": "1.0"
    }

    schema_json = json.dumps(schema)
    schema_name = f"nonprofit-users-schema-{int(time.time())}"

    try:
        response = personalize.create_schema(
            name=schema_name,
            schema=schema_json
        )
        print(f"✓ Users schema created: {response['schemaArn']}")
        return response['schemaArn']
    except personalize.exceptions.ResourceAlreadyExistsException:
        print(f"⚠ Schema {schema_name} already exists")
        return None


def create_users_dataset(schema_arn: str) -> str:
    """Create a USERS dataset in the dataset group or use existing."""
    try:
        dataset_name = f"nonprofit-users-{int(time.time())}"

        response = personalize.create_dataset(
            name=dataset_name,
            datasetGroupArn=DATASET_GROUP_ARN,
            datasetType="USERS",
            schemaArn=schema_arn
        )
        dataset_arn = response['datasetArn']
        print(f"✓ Users dataset created: {dataset_arn}")
    except personalize.exceptions.ResourceAlreadyExistsException:
        print(f"⚠ USERS dataset already exists, using existing...")
        # List datasets to find the USERS dataset
        datasets = personalize.list_datasets(datasetGroupArn=DATASET_GROUP_ARN)
        for ds in datasets["datasets"]:
            if ds["datasetType"] == "USERS":
                dataset_arn = ds["datasetArn"]
                print(f"  Using: {dataset_arn}")
                break

    # Wait for dataset to be ACTIVE
    print(f"  Waiting for dataset to be ACTIVE...")
    for i in range(30):
        response = personalize.describe_dataset(datasetArn=dataset_arn)
        status = response['dataset']['status']
        if status == "ACTIVE":
            print(f"  ✓ Dataset is ACTIVE")
            break
        print(f"    [{i+1}/30] Status: {status}")
        time.sleep(2)

    return dataset_arn


def upload_users_to_s3(csv_path: str) -> str:
    """Upload users CSV to S3."""
    s3_key = f"nonprofit/users/{Path(csv_path).name}"

    with open(csv_path, 'rb') as f:
        s3.put_object(Bucket=BUCKET, Key=s3_key, Body=f)

    s3_uri = f"s3://{BUCKET}/{s3_key}"
    print(f"✓ Users uploaded to S3: {s3_uri}")
    return s3_uri


def get_iam_role_arn() -> str:
    """Get the IAM role ARN for Personalize."""
    # This is a hardcoded ARN from manual IAM setup
    return "arn:aws:iam::684039303576:role/AmazonPersonalizeRole"


def import_dataset(dataset_arn: str, s3_uri: str, role_arn: str) -> str:
    """Import users data from S3."""
    job_name = f"nonprofit-users-import-{int(time.time())}"

    response = personalize.create_dataset_import_job(
        jobName=job_name,
        datasetArn=dataset_arn,
        dataSource={"dataLocation": s3_uri},
        roleArn=role_arn
    )
    job_arn = response['datasetImportJobArn']
    print(f"✓ Import job created: {job_arn}")
    return job_arn


def wait_for_import(job_arn: str, timeout_minutes: int = 15) -> bool:
    """Monitor import job until completion."""
    start_time = time.time()
    timeout_seconds = timeout_minutes * 60

    while True:
        response = personalize.describe_dataset_import_job(datasetImportJobArn=job_arn)
        status = response['datasetImportJob']['status']
        elapsed = int((time.time() - start_time) / 60)

        if status == "ACTIVE":
            print(f"✓ Import COMPLETE ({elapsed} minutes)")
            return True
        elif status == "CREATE_FAILED":
            error = response['datasetImportJob'].get('failureReason', 'Unknown error')
            print(f"✗ Import FAILED: {error}")
            return False
        else:
            print(f"  [{elapsed} min] Status: {status}")
            time.sleep(10)

            if time.time() - start_time > timeout_seconds:
                print(f"⚠ Timeout after {timeout_minutes} minutes. Import still in progress.")
                return False


def main():
    print("=" * 70)
    print("PHASE 1 SETUP: CREATE USERS DATASET")
    print("=" * 70)

    # Step 1: Create schema
    print(f"\n[1/5] Creating USERS dataset schema...")
    schema_arn = create_users_schema()
    if not schema_arn:
        print("⚠ Using existing schema")
        # List schemas and find the most recent users schema
        schemas = personalize.list_schemas()
        for schema in reversed(schemas["schemas"]):
            if "users" in schema["name"].lower():
                schema_arn = schema["schemaArn"]
                print(f"  Using: {schema_arn}")
                break

    # Step 2: Create dataset
    print(f"\n[2/5] Creating USERS dataset...")
    dataset_arn = create_users_dataset(schema_arn)

    # Step 3: Upload to S3
    print(f"\n[3/5] Uploading users CSV to S3...")
    s3_uri = upload_users_to_s3(USERS_CSV)

    # Step 4: Import data
    print(f"\n[4/5] Importing users data into Personalize...")
    role_arn = get_iam_role_arn()
    job_arn = import_dataset(dataset_arn, s3_uri, role_arn)

    # Step 5: Monitor import
    print(f"\n[5/5] Monitoring import job...")
    success = wait_for_import(job_arn)

    if success:
        print(f"\n✓ Users dataset ready for personalization model training!")
        print(f"\n  Next step: python3 phase1_train_model.py --wait-for-completion")
    else:
        print(f"\n⚠ Users dataset import incomplete. Check status manually.")
        print(f"  Job ARN: {job_arn}")

    print("=" * 70)


if __name__ == "__main__":
    main()
