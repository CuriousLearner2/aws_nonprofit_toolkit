#!/usr/bin/env python3
"""
Phase 1: Campaign API Real-Time Inference with Cost Control

This script:
1. Creates a Campaign from trained solution (cost starts here)
2. Calls GetRecommendations for 200 donors
3. Extracts engagement scores and segments
4. Immediately deletes Campaign (cost stops)

IMPORTANT: Tracks runtime carefully to minimize billing.
Campaign charges minimum 1 TPS even idle (~$0.0556/1000 requests/hour).
Target: Complete in <10 minutes = <$0.03 cost.
"""

import boto3
import os
import csv
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List

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
SOLUTION_VERSION_ARN = "arn:aws:personalize:us-east-1:684039303576:solution/donor-engagement-1779412135/96e1a58c"
USERS_CSV = "datasets/small_nonprofit_users.csv"

personalize = boto3.client(
    "personalize",
    region_name=REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)

personalize_runtime = boto3.client(
    "personalize-runtime",
    region_name=REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)


def create_campaign(solution_version_arn: str, min_tps: int = 1) -> str:
    """Create Campaign from trained solution."""
    campaign_name = f"phase1-campaign-{int(time.time())}"

    print(f"Creating Campaign: {campaign_name}")
    print(f"  minProvisionedTPS: {min_tps} (billing starts now)")

    response = personalize.create_campaign(
        name=campaign_name,
        solutionVersionArn=solution_version_arn,
        minProvisionedTPS=min_tps
    )

    campaign_arn = response['campaignArn']
    print(f"✓ Campaign ARN: {campaign_arn}")
    return campaign_arn


def wait_for_campaign_active(campaign_arn: str, timeout_minutes: int = 15) -> bool:
    """Wait for Campaign to be ACTIVE."""
    start_time = time.time()
    timeout_seconds = timeout_minutes * 60

    print(f"\n⏳ Waiting for Campaign to be ACTIVE (billing running)...")

    while True:
        response = personalize.describe_campaign(campaignArn=campaign_arn)
        status = response['campaign']['status']
        elapsed = int((time.time() - start_time) / 60)

        if status == "ACTIVE":
            print(f"✓ Campaign ACTIVE ({elapsed} min)")
            return True
        elif status == "CREATE_FAILED":
            print(f"✗ Campaign creation FAILED")
            return False
        else:
            print(f"  [{elapsed} min] Status: {status}")
            time.sleep(5)

            if time.time() - start_time > timeout_seconds:
                print(f"⚠ Timeout after {timeout_minutes} minutes")
                return False


def load_user_ids(csv_path: str) -> List[str]:
    """Load user IDs from CSV."""
    user_ids = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            user_ids.append(row['USER_ID'])
    print(f"Loaded {len(user_ids)} users from {csv_path}")
    return user_ids


def get_recommendations_for_users(campaign_arn: str, user_ids: List[str]) -> Dict[str, List]:
    """Get recommendations for all users via Campaign API."""
    print(f"\n📊 Getting recommendations for {len(user_ids)} users (billing running)...")

    recommendations = {}
    start_time = time.time()

    for idx, user_id in enumerate(user_ids):
        if idx > 0 and idx % 50 == 0:
            elapsed = int((time.time() - start_time) / 60)
            print(f"  [{elapsed} min] Processed {idx}/{len(user_ids)} users")

        try:
            response = personalize_runtime.get_recommendations(
                campaignArn=campaign_arn,
                userId=user_id,
                numResults=10  # Get top 10 cause recommendations
            )

            recommendations[user_id] = response.get('itemList', [])
        except Exception as e:
            print(f"  ⚠ Error getting recommendations for {user_id}: {e}")
            recommendations[user_id] = []

    elapsed = int((time.time() - start_time) / 60)
    print(f"✓ Got recommendations for {len(recommendations)} users ({elapsed} min)")
    return recommendations


def calculate_engagement_scores(recommendations: Dict[str, List]) -> Dict[str, float]:
    """Calculate overall engagement score from recommendations."""
    scores = {}

    for user_id, items in recommendations.items():
        if not items:
            scores[user_id] = 0.0
            continue

        # Score based on recommendation count and strength
        # Items are ranked, so use position-weighted scoring
        item_scores = []
        for idx, item in enumerate(items):
            # item has: 'itemId', 'score', 'metadata'
            score = float(item.get('score', 0))
            item_scores.append(score)

        if item_scores:
            # Composite: average + peak + breadth
            avg = sum(item_scores) / len(item_scores)
            peak = max(item_scores)
            breadth = min(len(item_scores) / 5, 1.0)  # Normalize
            composite = (avg * 0.4) + (peak * 0.4) + (breadth * 0.2)
            scores[user_id] = round(composite * 100, 1)
        else:
            scores[user_id] = 0.0

    return scores


def segment_donors(scores: Dict[str, float]) -> Dict[str, List[str]]:
    """Segment donors by engagement level."""
    segments = {'high': [], 'medium': [], 'low': []}

    for user_id, score in scores.items():
        if score >= 80:
            segments['high'].append(user_id)
        elif score >= 50:
            segments['medium'].append(user_id)
        else:
            segments['low'].append(user_id)

    return segments


def delete_campaign(campaign_arn: str) -> None:
    """Delete Campaign to stop billing."""
    print(f"\n🛑 Deleting Campaign (billing stops)...")
    personalize.delete_campaign(campaignArn=campaign_arn)
    print(f"✓ Campaign deleted")


def save_results(recommendations: Dict, scores: Dict, segments: Dict) -> None:
    """Save results to local files."""
    # Engagement scores
    with open("phase1_engagement_scores.csv", 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['USER_ID', 'ENGAGEMENT_SCORE', 'SEGMENT'])
        for user_id in sorted(scores.keys()):
            score = scores[user_id]
            segment = 'HIGH' if score >= 80 else ('MEDIUM' if score >= 50 else 'LOW')
            writer.writerow([user_id, f"{score:.1f}", segment])
    print(f"✓ Saved: phase1_engagement_scores.csv")

    # Cause recommendations
    with open("phase1_cause_recommendations.csv", 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['USER_ID', 'CAUSE_RANK', 'CAUSE', 'SCORE'])
        for user_id in sorted(recommendations.keys()):
            for rank, item in enumerate(recommendations[user_id], 1):
                cause = item.get('itemId')
                score = item.get('score', 0)
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
    """Print summary of results."""
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
    overall_start = time.time()

    print("=" * 70)
    print("PHASE 1: CAMPAIGN API INFERENCE (COST-CONTROLLED)")
    print("=" * 70)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target: Complete in <10 minutes")
    print()

    campaign_arn = None

    try:
        # Step 1: Create Campaign
        print("[1/6] Creating Campaign...")
        campaign_arn = create_campaign(SOLUTION_VERSION_ARN, min_tps=1)
        campaign_start = time.time()

        # Step 2: Wait for Campaign
        print("\n[2/6] Waiting for Campaign activation...")
        if not wait_for_campaign_active(campaign_arn, timeout_minutes=15):
            print("✗ Campaign failed to activate. Cleaning up...")
            if campaign_arn:
                delete_campaign(campaign_arn)
            return

        campaign_active_time = time.time()

        # Step 3: Load users
        print("\n[3/6] Loading user IDs...")
        user_ids = load_user_ids(USERS_CSV)

        # Step 4: Get recommendations
        print("\n[4/6] Getting recommendations via Campaign API...")
        recommendations = get_recommendations_for_users(campaign_arn, user_ids)

        # Step 5: Calculate scores
        print("\n[5/6] Calculating engagement scores...")
        scores = calculate_engagement_scores(recommendations)
        segments = segment_donors(scores)
        print(f"✓ Calculated scores for {len(scores)} donors")

        # Step 6: Delete Campaign (CRITICAL - stops billing)
        print("\n[6/6] Cleaning up...")
        delete_campaign(campaign_arn)
        campaign_end = time.time()

    except Exception as e:
        print(f"\n✗ Error: {e}")
        if campaign_arn:
            print("Cleaning up Campaign...")
            delete_campaign(campaign_arn)
        return

    # Calculate timing
    total_time = (time.time() - overall_start) / 60
    campaign_billing_time = (campaign_end - campaign_start) / 60

    print("\n" + "=" * 70)
    print("COST SUMMARY")
    print("=" * 70)
    print(f"Campaign active for: {campaign_billing_time:.2f} minutes")
    print(f"Estimated cost: ${campaign_billing_time * 0.0556 / 60:.2f}")
    print(f"Total script time: {total_time:.2f} minutes")
    print("=" * 70)

    # Print results
    print_results(scores, segments)

    # Save results
    print("\nSaving results to CSV files...")
    save_results(recommendations, scores, segments)

    print(f"\n✓ Phase 1 complete!")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
