import boto3
import json
import logging
import argparse
import os
from typing import Dict, List, Optional
from botocore.exceptions import ClientError
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("personalize_segmentation")

load_dotenv()

def load_archetype_config(config_path: Optional[str] = None) -> Dict[str, str]:
  """Load archetype mappings from config file. Falls back to defaults."""
  if config_path and os.path.exists(config_path):
    try:
      with open(config_path, 'r') as f:
        return json.load(f)
    except Exception as e:
      logger.warning(f"Failed to load config from {config_path}: {e}. Using defaults.")

  return {
    "ENVIRONMENT": "Eco-Conscious",
    "CLEAN_WATER": "Health Advocate",
    "DISASTER_RELIEF": "Emergency Responder",
    "EDUCATION": "Knowledge Seeker",
    "COMMUNITY_HEALTH": "Health Advocate"
  }

class PersonalizeInference:
  """Interface with Amazon Personalize to get donor recommendations and segment donors."""

  def __init__(self, campaign_arn: str, archetypes: Optional[Dict[str, str]] = None):
    try:
      self.client = boto3.client(
        'personalize-runtime',
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION", "us-east-1")
      )
    except Exception as e:
      logger.error(f"Failed to initialize Personalize client: {e}")
      raise

    self.campaign_arn = campaign_arn
    self.archetypes = archetypes or load_archetype_config()

  def get_donor_recommendations(self, user_id: str, num_results: int = 10) -> List[Dict]:
    """Fetch donor recommendations from Personalize. Returns sorted by score."""
    try:
      response = self.client.get_recommendations(
        campaignArn=self.campaign_arn,
        userId=user_id,
        numResults=num_results
      )
      return response.get('itemList', [])
    except ClientError as e:
      logger.error(f"Personalize API error for user {user_id}: {e}")
      return []

  def get_donor_archetype(self, user_id: str) -> Dict:
    """Score donor across recommendations and identify primary archetype."""
    recommendations = self.get_donor_recommendations(user_id)

    if not recommendations:
      logger.warning(f"No recommendations found for user {user_id}")
      return {
        "user_id": user_id,
        "archetype": "General",
        "confidence": 0.0,
        "recommendations": [],
        "status": "no_data"
      }

    # Weight recommendations by position (earlier = higher weight)
    archetype_scores = {}
    for i, rec in enumerate(recommendations):
      item_id = rec.get('itemId', 'UNKNOWN')
      score = rec.get('score', 0)

      # Position weight: top recommendation gets 100%, then decreases
      position_weight = (len(recommendations) - i) / len(recommendations)
      weighted_score = score * position_weight if score else position_weight

      # Map item to archetype, default to "Supporter"
      archetype = self.archetypes.get(item_id, "Supporter")
      archetype_scores[archetype] = archetype_scores.get(archetype, 0) + weighted_score

    # Identify top archetype
    primary_archetype = max(archetype_scores, key=archetype_scores.get)
    total_score = sum(archetype_scores.values())
    confidence = archetype_scores[primary_archetype] / total_score if total_score > 0 else 0

    return {
      "user_id": user_id,
      "archetype": primary_archetype,
      "confidence": round(confidence, 2),
      "archetype_scores": {k: round(v, 2) for k, v in archetype_scores.items()},
      "top_recommendations": [
        {"item": rec.get('itemId'), "score": round(rec.get('score', 0), 3)}
        for rec in recommendations[:3]
      ],
      "status": "success"
    }

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Segment donors by archetype using Personalize.")
  parser.add_argument("--user-id", type=str, required=True, help="Donor user ID to segment")
  parser.add_argument("--campaign-arn", type=str, default=os.getenv("PERSONALIZE_CAMPAIGN_ARN"),
                      help="Personalize Campaign ARN (defaults to PERSONALIZE_CAMPAIGN_ARN env var)")
  parser.add_argument("--archetypes-config", type=str, default=None,
                      help="Path to custom archetypes JSON config")
  parser.add_argument("--json", action="store_true", help="Output as JSON")

  args = parser.parse_args()

  if not args.campaign_arn:
    logger.error("Campaign ARN required. Set PERSONALIZE_CAMPAIGN_ARN env var or use --campaign-arn")
    exit(1)

  archetypes = load_archetype_config(args.archetypes_config)
  inference = PersonalizeInference(args.campaign_arn, archetypes)
  result = inference.get_donor_archetype(args.user_id)

  if args.json:
    print(json.dumps(result, indent=2))
  else:
    print(f"\n✅ Donor Segmentation Result")
    print(f"   User ID: {result['user_id']}")
    print(f"   Primary Archetype: {result['archetype']} (confidence: {result['confidence']:.0%})")
    if result.get('archetype_scores'):
      print(f"   All Archetypes: {result['archetype_scores']}")
    if result.get('top_recommendations'):
      print(f"   Top Interests: {[r['item'] for r in result['top_recommendations']]}")
    print()
