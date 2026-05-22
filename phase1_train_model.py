#!/usr/bin/env python3
"""
Phase 1: Train Recommender Model for Donor Engagement Scoring

This script:
1. Creates a Personalize solution (model) using USER_PERSONALIZATION recipe
2. Trains the model on imported donor interactions
3. Monitors training progress
4. Reports model ARN for batch inference (Phase 1 step 2)

Option A: Overall Engagement Score per Donor
- The USER_PERSONALIZATION recipe learns each donor's propensity to engage
- Output: Ranking score (0-100) for each donor's likelihood to respond

Option B: Cause-Specific Recommendations (future)
- Same recipe recommends specific ITEM_IDs (causes) per donor
- Output: Ranked list of causes per donor

Usage:
    python3 phase1_train_model.py [--wait-for-completion]

    --wait-for-completion: Monitor training until ACTIVE (10-15 minutes)
"""

import boto3
import time
import os
import sys
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path

# Load credentials from .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ[key] = value

# Configuration
DATASET_GROUP_ARN = "arn:aws:personalize:us-east-1:684039303576:dataset-group/nonprofit-donors-1779321550"
RECIPE_ARN = "arn:aws:personalize:::recipe/aws-item-affinity"
REGION = "us-east-1"

# Initialize Personalize client with explicit credentials
aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

personalize = boto3.client(
    "personalize",
    region_name=REGION,
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key
)


def create_solution(solution_name: str) -> Dict:
    """
    Create a Personalize solution (model recipe + hyperparameters).

    Args:
        solution_name: Unique name for the solution

    Returns:
        Dict with solutionArn
    """
    try:
        response = personalize.create_solution(
            name=solution_name,
            datasetGroupArn=DATASET_GROUP_ARN,
            recipeArn=RECIPE_ARN
        )
        print(f"✓ Solution created: {response['solutionArn']}")
        return response
    except personalize.exceptions.ResourceAlreadyExistsException:
        print(f"⚠ Solution '{solution_name}' already exists")
        # List solutions to find the existing one
        solutions = personalize.list_solutions(
            datasetGroupArn=DATASET_GROUP_ARN
        )
        for sol in solutions.get("solutions", []):
            if sol["name"] == solution_name:
                print(f"  Using existing: {sol['solutionArn']}")
                return {"solutionArn": sol["solutionArn"]}
        raise


def create_solution_version(solution_arn: str, wait_for_completion: bool = False) -> Dict:
    """
    Create and train a solution version (training job).

    Args:
        solution_arn: ARN of the solution to train
        wait_for_completion: If True, block until training completes

    Returns:
        Dict with solutionVersionArn and status
    """
    response = personalize.create_solution_version(solutionArn=solution_arn)
    version_arn = response["solutionVersionArn"]

    print(f"\n✓ Training started: {version_arn}")
    print(f"  Expected duration: 10-15 minutes")
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")

    if wait_for_completion:
        print(f"\n⏳ Monitoring training progress...")
        wait_for_training(version_arn)
    else:
        print(f"\n💡 To monitor training, run:")
        print(f"   python3 -c \"import boto3; c = boto3.client('personalize', region_name='{REGION}')\"")
        print(f"   result = c.describe_solution_version(solutionVersionArn='{version_arn}')")
        print(f"   print(f'Status: {{result[\\\"solutionVersion\\\"][\\\"status\\\"]}}')")

    return response


def wait_for_training(solution_version_arn: str, timeout_minutes: int = 30) -> Dict:
    """
    Poll training status until completion or timeout.

    Args:
        solution_version_arn: ARN to monitor
        timeout_minutes: Max time to wait

    Returns:
        Final status response
    """
    start_time = time.time()
    timeout_seconds = timeout_minutes * 60

    while True:
        response = personalize.describe_solution_version(
            solutionVersionArn=solution_version_arn
        )
        status = response["solutionVersion"]["status"]
        elapsed = int((time.time() - start_time) / 60)

        if status == "ACTIVE":
            print(f"✓ Training COMPLETE ({elapsed} minutes)")
            print_training_metrics(response)
            return response
        elif status == "CREATE_FAILED":
            error = response["solutionVersion"].get("failureReason", "Unknown error")
            print(f"✗ Training FAILED: {error}")
            return response
        else:
            print(f"  [{elapsed} min] Status: {status}")
            time.sleep(30)  # Poll every 30 seconds

            if time.time() - start_time > timeout_seconds:
                print(f"⚠ Timeout after {timeout_minutes} minutes. Training still in progress.")
                return response


def print_training_metrics(response: Dict) -> None:
    """Print training quality metrics."""
    solution_version = response.get("solutionVersion", {})

    # Metrics vary by recipe; print what's available
    metrics = {
        "Coverage": solution_version.get("metrics", {}).get("coverage"),
        "Mean Average Precision": solution_version.get("metrics", {}).get("mean_average_precision"),
        "Normalized DCAG": solution_version.get("metrics", {}).get("normalized_discounted_cumulative_gain"),
    }

    if any(metrics.values()):
        print(f"\n  Training Metrics:")
        for metric_name, value in metrics.items():
            if value is not None:
                print(f"    {metric_name}: {value:.4f}")


def get_training_status(solution_version_arn: str) -> str:
    """Check status of a training job without waiting."""
    response = personalize.describe_solution_version(
        solutionVersionArn=solution_version_arn
    )
    status = response["solutionVersion"]["status"]
    return status


def list_trained_models() -> None:
    """List all trained solutions in the dataset group."""
    solutions = personalize.list_solutions(datasetGroupArn=DATASET_GROUP_ARN)

    if solutions["solutions"]:
        print("\n📊 Existing Solutions:")
        for sol in solutions["solutions"]:
            print(f"\n  Name: {sol['name']}")
            print(f"  ARN: {sol['solutionArn']}")

            # List versions for this solution
            versions = personalize.list_solution_versions(
                solutionArn=sol["solutionArn"]
            )
            for ver in versions.get("solutionVersions", []):
                print(f"    Version: {ver['solutionVersionArn']}")
                print(f"      Status: {ver['status']}")
                if ver["status"] == "ACTIVE":
                    print(f"      ✓ Ready for inference")


def main():
    """Main execution flow for Phase 1 model training."""
    wait_for_completion = "--wait-for-completion" in sys.argv

    print("=" * 70)
    print("PHASE 1: TRAIN DONOR ENGAGEMENT MODEL")
    print("=" * 70)

    # Step 1: Create solution
    solution_name = f"donor-engagement-{int(time.time())}"
    print(f"\n[1/3] Creating solution: {solution_name}")
    solution = create_solution(solution_name)
    solution_arn = solution["solutionArn"]

    # Step 2: Create and train solution version
    print(f"\n[2/3] Starting model training...")
    version = create_solution_version(solution_arn, wait_for_completion=wait_for_completion)
    version_arn = version["solutionVersionArn"]

    # Step 3: Report
    print(f"\n[3/3] Next Steps:")
    print(f"\n  ✓ Solution ARN: {solution_arn}")
    print(f"  ✓ Training Job ARN: {version_arn}")
    print(f"\n  When training is ACTIVE:")
    print(f"    1. Run: python3 phase1_batch_inference.py '{version_arn}'")
    print(f"    2. Then: python3 phase1_extract_segments.py")

    # List other trained models for reference
    print(f"\n" + "=" * 70)
    list_trained_models()
    print("=" * 70)


if __name__ == "__main__":
    main()
