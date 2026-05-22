#!/usr/bin/env python3
"""
Phase 1 Batch Inference: Personalized Ranking v2

For personalized-ranking-v2, batch input is (userId, itemId) pairs to rank.
We'll rank all 5 causes for each of 200 donors = 1,000 ranking requests.

Usage:
    python3 phase1_batch_ranking.py <solution-version-arn>
"""

import boto3
import os
import sys
import json
import csv
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
from collections import defaultdict

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
    """Get IAM role for Personalize."""
    return "arn:aws:iam::684039303576:role/AmazonPersonalizeRole"


def prepare_ranking_input(
    users_csv: str = "datasets/small_nonprofit_users.csv",
    interactions_csv: str = "datasets/small_nonprofit_interactions.csv"
) -> str:
    """
    Prepare batch input: (userId, itemId) pairs to rank.

    For personalized-ranking, we rank ALL items for each user.
    Extract unique items (causes) from interactions.
    """
    # Get unique causes
    causes = set()
    with open(interactions_csv) as f:
        reader = csv.DictReader(f)
        for row in reader:
            causes.add(row['ITEM_ID'])

    causes = sorted(list(causes))
    print(f"Found {len(causes)} unique causes: {causes}")

    # Get users
    users = []
    with open(users_csv) as f:
        reader = csv.DictReader(f)
        for row in reader:
            users.append(row['USER_ID'])

    print(f"Found {len(users)} users")

    # Create ranking input: each user ranks all causes
    batch_input_file = "batch_ranking_input.json"
    with open(batch_input_file, 'w') as f:
        for user_id in users:
            # For personalized-ranking, input is a list of items to rank for a user
            input_obj = {
                "userId": user_id,
                "itemList": causes
            }
            f.write(json.dumps(input_obj) + "\n")

    print(f"✓ Created {batch_input_file} ({len(users)} users × {len(causes)} causes)")
    return batch_input_file, causes


def upload_to_s3(batch_input_file: str) -> str:
    """Upload batch input to S3."""
    timestamp = int(time.time())
    s3_key = f"personalize/batch_ranking_input/phase1_{timestamp}.json"

    with open(batch_input_file, 'rb') as f:
        s3.put_object(Bucket=BUCKET, Key=s3_key, Body=f)

    s3_uri = f"s3://{BUCKET}/{s3_key}"
    print(f"✓ Uploaded to S3: {s3_uri}")
    return s3_uri


def create_batch_job(solution_version_arn: str, input_s3: str) -> Tuple[str, str]:
    """Create and start batch inference job."""
    timestamp = int(time.time())
    output_s3 = f"s3://{BUCKET}/personalize/batch_ranking_output/phase1_{timestamp}/"
    job_name = f"phase1-ranking-batch-{timestamp}"

    print(f"Creating batch job: {job_name}")
    response = personalize.create_batch_inference_job(
        jobName=job_name,
        solutionVersionArn=solution_version_arn,
        jobInput={"s3DataSource": {"path": input_s3}},
        jobOutput={"s3DataDestination": {"path": output_s3}},
        roleArn=get_iam_role_arn()
    )

    job_arn = response['batchInferenceJobArn']
    print(f"✓ Batch job: {job_arn}")
    print(f"  Output: {output_s3}")
    return job_arn, output_s3


def wait_for_batch_job(job_arn: str, timeout_minutes: int = 30) -> bool:
    """Wait for batch job completion."""
    start_time = time.time()
    timeout_seconds = timeout_minutes * 60

    print(f"⏳ Monitoring batch job...")

    while True:
        response = personalize.describe_batch_inference_job(
            batchInferenceJobArn=job_arn
        )
        status = response['batchInferenceJob']['status']
        elapsed = int((time.time() - start_time) / 60)

        if status == "ACTIVE":
            print(f"✓ Batch job COMPLETE ({elapsed} minutes)")
            return True
        elif status == "CREATE_FAILED":
            error = response['batchInferenceJob'].get('failureReason', 'Unknown')
            print(f"✗ Batch job FAILED: {error}")
            return False
        else:
            print(f"  [{elapsed} min] Status: {status}")
            time.sleep(30)

            if time.time() - start_time > timeout_seconds:
                print(f"⚠ Timeout after {timeout_minutes} minutes")
                return False


def download_and_parse_results(output_s3: str, causes: List[str]) -> Dict[str, Dict[str, float]]:
    """Download batch results and parse rankings."""
    bucket, prefix = output_s3.replace("s3://", "").split("/", 1)
    prefix = prefix.rstrip("/")

    print(f"\nDownloading results from {output_s3}")

    # List files
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    files = response.get('Contents', [])

    rankings = defaultdict(dict)

    for file_obj in files:
        key = file_obj['Key']
        if key.endswith('/'):
            continue

        print(f"  Reading: {Path(key).name}")

        # Download and parse
        obj = s3.get_object(Bucket=bucket, Key=key)
        content = obj['Body'].read().decode('utf-8')

        for line in content.strip().split('\n'):
            if not line:
                continue
            try:
                result = json.loads(line)
                user_id = result.get('userId') or result.get('input', {}).get('userId')
                if not user_id:
                    continue

                # Extract rankings
                output = result.get('output', {})
                ranked_items = output.get('itemList', [])

                for rank, item in enumerate(ranked_items, 1):
                    item_id = item.get('itemId')
                    score = float(item.get('score', 0))
                    rankings[user_id][item_id] = score

            except json.JSONDecodeError:
                pass

    print(f"✓ Parsed {len(rankings)} users with rankings")
    return rankings


def calculate_engagement_scores(rankings: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    """Calculate overall engagement score from rankings."""
    scores = {}

    for user_id, item_rankings in rankings.items():
        if not item_rankings:
            scores[user_id] = 0.0
            continue

        values = list(item_rankings.values())
        avg = sum(values) / len(values)
        peak = max(values)
        breadth = min(len(values) / 5, 1.0)

        composite = (avg * 0.4) + (peak * 0.4) + (breadth * 0.2)
        scores[user_id] = round(composite * 100, 1)

    return scores


def segment_donors(scores: Dict[str, float]) -> Dict[str, List[str]]:
    """Segment by engagement level."""
    segments = {'high': [], 'medium': [], 'low': []}

    for user_id, score in scores.items():
        if score >= 80:
            segments['high'].append(user_id)
        elif score >= 50:
            segments['medium'].append(user_id)
        else:
            segments['low'].append(user_id)

    return segments


def save_results(rankings: Dict, scores: Dict, segments: Dict) -> None:
    """Save results to CSV."""
    # Engagement scores
    with open("phase1_engagement_scores.csv", 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['USER_ID', 'ENGAGEMENT_SCORE', 'SEGMENT'])
        for user_id in sorted(scores.keys()):
            score = scores[user_id]
            segment = 'HIGH' if score >= 80 else ('MEDIUM' if score >= 50 else 'LOW')
            writer.writerow([user_id, f"{score:.1f}", segment])
    print(f"✓ Saved: phase1_engagement_scores.csv")

    # Cause rankings
    with open("phase1_cause_recommendations.csv", 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['USER_ID', 'CAUSE_RANK', 'CAUSE', 'SCORE'])
        for user_id in sorted(rankings.keys()):
            # Sort by score descending
            sorted_items = sorted(
                rankings[user_id].items(),
                key=lambda x: x[1],
                reverse=True
            )
            for rank, (cause, score) in enumerate(sorted_items, 1):
                writer.writerow([user_id, rank, cause, f"{score:.3f}"])
    print(f"✓ Saved: phase1_cause_recommendations.csv")

    # Segments
    with open("phase1_segments.csv", 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['SEGMENT', 'COUNT', 'DONOR_IDS'])
        for seg_name, label in [('high', 'HIGH'), ('medium', 'MEDIUM'), ('low', 'LOW')]:
            users = segments[seg_name]
            writer.writerow([label, len(users), '; '.join(users)])
    print(f"✓ Saved: phase1_segments.csv")


def print_results(scores: Dict, segments: Dict) -> None:
    """Print summary."""
    print("\n" + "=" * 70)
    print("PHASE 1 RESULTS: DONOR ENGAGEMENT SEGMENTS")
    print("=" * 70)

    all_scores = list(scores.values())
    print(f"\nOverall Statistics:")
    print(f"  Total Donors: {len(scores)}")
    print(f"  Avg Engagement Score: {sum(all_scores)/len(all_scores):.1f}")
    print(f"  Min Score: {min(all_scores):.1f}")
    print(f"  Max Score: {max(all_scores):.1f}")

    print(f"\nSegment Breakdown:")
    for seg_name, label in [('high', 'HIGH (80+)'), ('medium', 'MEDIUM (50-79)'), ('low', 'LOW (<50)')]:
        users = segments[seg_name]
        pct = (len(users) / len(scores) * 100) if scores else 0
        print(f"  {label}: {len(users)} donors ({pct:.1f}%)")

    print("\n✓ Options implemented:")
    print("  A: Overall engagement score (0-100)")
    print("  B: Cause-specific rankings")
    print("  C: Donor segmentation (High/Medium/Low)")
    print("=" * 70)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 phase1_batch_ranking.py <solution-version-arn>")
        sys.exit(1)

    solution_version_arn = sys.argv[1]

    print("=" * 70)
    print("PHASE 1: BATCH RANKING INFERENCE")
    print("=" * 70)
    print(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Step 1: Prepare input
    print("[1/5] Preparing ranking input...")
    batch_input_file, causes = prepare_ranking_input()

    # Step 2: Upload to S3
    print("\n[2/5] Uploading to S3...")
    input_s3 = upload_to_s3(batch_input_file)

    # Step 3: Create batch job
    print("\n[3/5] Creating batch job...")
    job_arn, output_s3 = create_batch_job(solution_version_arn, input_s3)

    # Step 4: Wait for completion
    print("\n[4/5] Monitoring batch job...")
    if not wait_for_batch_job(job_arn):
        print("✗ Batch job failed or timed out")
        return

    # Step 5: Parse results
    print("\n[5/5] Processing results...")
    rankings = download_and_parse_results(output_s3, causes)

    if not rankings:
        print("✗ No results downloaded")
        return

    scores = calculate_engagement_scores(rankings)
    segments = segment_donors(scores)

    print_results(scores, segments)
    save_results(rankings, scores, segments)

    print(f"\n✓ Phase 1 complete!")
    print(f"End: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
