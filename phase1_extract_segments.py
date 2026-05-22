#!/usr/bin/env python3
"""
Phase 1 Step 3: Extract Donor Engagement Segments

This script:
1. Downloads batch inference results from S3
2. Parses personalization scores per donor
3. Segments donors into: High (80+), Medium (50-79), Low (<50)
4. Generates actionable segment reports

Usage:
    python3 phase1_extract_segments.py <output-s3-path>

Example:
    python3 phase1_extract_segments.py s3://bucket/personalize/batch_output/phase1_xxx/
"""

import boto3
import os
import sys
import json
import csv
from pathlib import Path
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

s3 = boto3.client(
    "s3",
    region_name=REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)


def parse_s3_path(s3_path: str) -> Tuple[str, str]:
    """Parse S3 path into bucket and prefix."""
    # Remove s3:// prefix and trailing slash
    path = s3_path.replace("s3://", "").rstrip("/")
    parts = path.split("/", 1)
    bucket = parts[0]
    prefix = parts[1] if len(parts) > 1 else ""
    return bucket, prefix


def download_batch_results(s3_path: str) -> List[Dict]:
    """Download and parse batch inference results from S3."""
    bucket, prefix = parse_s3_path(s3_path)

    print(f"  Downloading from: s3://{bucket}/{prefix}")

    # List files in the output prefix
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    files = response.get('Contents', [])

    if not files:
        print(f"  ⚠ No files found in output directory")
        return []

    results = []

    # Download and parse each result file
    for file_obj in files:
        key = file_obj['Key']

        # Skip directories (keys ending with /)
        if key.endswith('/'):
            continue

        print(f"  Reading: {Path(key).name}")

        # Download file
        obj = s3.get_object(Bucket=bucket, Key=key)
        content = obj['Body'].read().decode('utf-8')

        # Parse JSON lines format (one recommendation per line)
        for line in content.strip().split('\n'):
            if line:
                try:
                    result = json.loads(line)
                    results.append(result)
                except json.JSONDecodeError:
                    pass

    print(f"  ✓ Downloaded {len(results)} records")
    return results


def parse_recommendations(results: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Parse batch results into donor recommendations.

    AWS Personalize item-affinity recipe returns format like:
    {
        "userID": "user_123",
        "output": {
            "recommendations": [
                {"itemId": "ENVIRONMENT", "score": 0.85},
                {"itemId": "EDUCATION", "score": 0.72}
            ]
        }
    }
    """
    donor_recommendations = defaultdict(list)

    for result in results:
        user_id = result.get('userID') or result.get('input', {}).get('userID')
        if not user_id:
            continue

        # Extract recommendations
        output = result.get('output', {})
        recommendations = output.get('recommendations', [])

        # Store as list of dicts with score
        donor_recommendations[user_id] = [
            {
                'cause': rec.get('itemId'),
                'score': float(rec.get('score', 0))
            }
            for rec in recommendations
        ]

    return donor_recommendations


def calculate_engagement_scores(donor_recommendations: Dict[str, List[Dict]]) -> Dict[str, float]:
    """
    Calculate Option A: Overall engagement score per donor.

    Score based on:
    - Number of causes they're engaged with
    - Average engagement score across causes
    - Peak score (strongest engagement)

    Result: 0-100 scale
    """
    engagement_scores = {}

    for user_id, causes in donor_recommendations.items():
        if not causes:
            engagement_scores[user_id] = 0.0
            continue

        # Extract scores
        scores = [c['score'] for c in causes if isinstance(c['score'], (int, float))]

        if not scores:
            engagement_scores[user_id] = 0.0
            continue

        # Composite score:
        # - Average of all scores (40%)
        # - Peak score (40%)
        # - Number of causes engaged with (20%)
        avg_score = sum(scores) / len(scores)
        peak_score = max(scores)
        engagement_count = min(len(scores) / 5, 1.0)  # Normalize to 0-1 (assuming 5+ causes available)

        composite = (avg_score * 0.4) + (peak_score * 0.4) + (engagement_count * 0.2)
        engagement_scores[user_id] = round(composite * 100, 1)  # Scale to 0-100

    return engagement_scores


def segment_donors(engagement_scores: Dict[str, float]) -> Dict[str, List[str]]:
    """
    Option C: Segment donors into engagement tiers.

    - High (80+): "Likely Responders"
    - Medium (50-79): "Warm Leads"
    - Low (<50): "Cold Prospects"
    """
    segments = {
        'high': [],
        'medium': [],
        'low': []
    }

    for user_id, score in engagement_scores.items():
        if score >= 80:
            segments['high'].append(user_id)
        elif score >= 50:
            segments['medium'].append(user_id)
        else:
            segments['low'].append(user_id)

    return segments


def generate_segment_report(
    engagement_scores: Dict[str, float],
    donor_recommendations: Dict[str, List[Dict]],
    segments: Dict[str, List[str]]
) -> str:
    """Generate human-readable segment analysis report."""
    report = []

    report.append("\n" + "=" * 70)
    report.append("PHASE 1: DONOR ENGAGEMENT SEGMENTS")
    report.append("=" * 70)

    # Overall statistics
    all_scores = list(engagement_scores.values())
    report.append(f"\nOverall Statistics:")
    report.append(f"  Total Donors: {len(engagement_scores)}")
    report.append(f"  Avg Engagement Score: {sum(all_scores)/len(all_scores):.1f}")
    report.append(f"  Min Score: {min(all_scores):.1f}")
    report.append(f"  Max Score: {max(all_scores):.1f}")

    # Segment breakdown
    report.append(f"\nSegment Breakdown:")

    for segment_name, label, icon in [
        ('high', 'HIGH ENGAGEMENT (80+)', '⭐'),
        ('medium', 'MEDIUM ENGAGEMENT (50-79)', '📊'),
        ('low', 'LOW ENGAGEMENT (<50)', '❄️')
    ]:
        users = segments[segment_name]
        pct = (len(users) / len(engagement_scores) * 100) if engagement_scores else 0
        report.append(f"\n  {icon} {label}: {len(users)} donors ({pct:.1f}%)")

        if users:
            # Top 3 donors in segment
            top_3 = sorted(users, key=lambda u: engagement_scores[u], reverse=True)[:3]
            for user_id in top_3:
                score = engagement_scores[user_id]
                causes = donor_recommendations.get(user_id, [])
                top_cause = causes[0]['cause'] if causes else 'N/A'
                report.append(f"    • {user_id}: {score:.1f} (top cause: {top_cause})")

    # Options summary
    report.append(f"\nImplemented Options:")
    report.append(f"  ✓ Option A: Overall Engagement Score (0-100)")
    report.append(f"  ✓ Option B: Cause-Specific Rankings (per donor)")
    report.append(f"  ✓ Option C: Donor Segmentation (High/Medium/Low)")

    report.append("\n" + "=" * 70)

    return "\n".join(report)


def save_results(
    engagement_scores: Dict[str, float],
    donor_recommendations: Dict[str, List[Dict]],
    segments: Dict[str, List[str]]
) -> None:
    """Save results to local CSV files for analysis."""
    timestamp = Path("batch_input.json").stat().st_mtime if Path("batch_input.json").exists() else 0

    # Save engagement scores
    with open("phase1_engagement_scores.csv", 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['USER_ID', 'ENGAGEMENT_SCORE', 'SEGMENT'])
        for user_id in sorted(engagement_scores.keys()):
            score = engagement_scores[user_id]
            if score >= 80:
                segment = 'HIGH'
            elif score >= 50:
                segment = 'MEDIUM'
            else:
                segment = 'LOW'
            writer.writerow([user_id, f"{score:.1f}", segment])

    print(f"✓ Saved: phase1_engagement_scores.csv")

    # Save cause recommendations
    with open("phase1_cause_recommendations.csv", 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['USER_ID', 'CAUSE_RANK', 'CAUSE', 'SCORE'])
        for user_id in sorted(donor_recommendations.keys()):
            for rank, rec in enumerate(donor_recommendations[user_id], 1):
                writer.writerow([user_id, rank, rec['cause'], f"{rec['score']:.3f}"])

    print(f"✓ Saved: phase1_cause_recommendations.csv")

    # Save segment assignments
    with open("phase1_segments.csv", 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['SEGMENT', 'COUNT', 'DONOR_IDS'])
        for segment_name, label in [('high', 'HIGH'), ('medium', 'MEDIUM'), ('low', 'LOW')]:
            users = segments[segment_name]
            writer.writerow([label, len(users), '; '.join(users)])

    print(f"✓ Saved: phase1_segments.csv")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 phase1_extract_segments.py <output-s3-path>")
        print("\nExample:")
        print("  python3 phase1_extract_segments.py s3://bucket/personalize/batch_output/phase1_xxx/")
        sys.exit(1)

    output_s3 = sys.argv[1]

    print("=" * 70)
    print("PHASE 1 STEP 3: EXTRACT SEGMENTS")
    print("=" * 70)

    # Step 1: Download results
    print(f"\n[1/4] Downloading batch results...")
    results = download_batch_results(output_s3)

    if not results:
        print("✗ No results found. Check S3 path and batch job status.")
        sys.exit(1)

    # Step 2: Parse recommendations
    print(f"\n[2/4] Parsing recommendations...")
    donor_recommendations = parse_recommendations(results)
    print(f"✓ Parsed {len(donor_recommendations)} donors")

    # Step 3: Calculate scores
    print(f"\n[3/4] Calculating engagement scores...")
    engagement_scores = calculate_engagement_scores(donor_recommendations)
    segments = segment_donors(engagement_scores)
    print(f"✓ Scored {len(engagement_scores)} donors")

    # Step 4: Generate report
    print(f"\n[4/4] Generating report...")
    report = generate_segment_report(engagement_scores, donor_recommendations, segments)
    print(report)

    # Save results
    save_results(engagement_scores, donor_recommendations, segments)

    print("=" * 70)
    print(f"\n✓ Phase 1 complete! Results saved locally.")


if __name__ == "__main__":
    main()
