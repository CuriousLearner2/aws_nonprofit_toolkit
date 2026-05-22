#!/usr/bin/env python3
"""Quick check of import job status."""

import boto3
import os
from pathlib import Path

env_path = Path(".env")
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ[key] = value

personalize = boto3.client(
    "personalize",
    region_name="us-east-1",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)

# Check all import jobs in dataset group
dataset_group_arn = "arn:aws:personalize:us-east-1:684039303576:dataset-group/nonprofit-donors-1779321550"

print("=" * 70)
print("IMPORT JOB STATUS")
print("=" * 70)

# Get dataset group info
datasets = personalize.list_datasets(datasetGroupArn=dataset_group_arn)
print(f"\nDatasets in group:")
for ds in datasets["datasets"]:
    print(f"\n  {ds['datasetType']}: {ds['name']}")

    # List import jobs for this dataset
    import_jobs = personalize.list_dataset_import_jobs(datasetArn=ds['datasetArn'])
    if import_jobs['datasetImportJobs']:
        for job in import_jobs['datasetImportJobs']:
            print(f"    Import Job: {job['jobName']}")
            print(f"      Status: {job['status']}")
            print(f"      Created: {job['creationDateTime']}")
    else:
        print(f"    (No import jobs)")

print("\n" + "=" * 70)
