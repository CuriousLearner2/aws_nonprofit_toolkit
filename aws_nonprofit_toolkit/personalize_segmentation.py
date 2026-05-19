import boto3
import json
import logging
import argparse
import os
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("personalize_segmentation")

# Load configuration
load_dotenv()

class PersonalizeInference:
    """Interface with Amazon Personalize to get donor recommendations."""
    
    def __init__(self, campaign_arn: str):
        self.client = boto3.client(
            'personalize-runtime',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION", "us-east-1")
        )
        self.campaign_arn = campaign_arn

    def get_donor_recommendations(self, user_id: str, num_results: int = 5):
        """Query Personalize for the next best items for a given user."""
        try:
            response = self.client.get_recommendations(
                campaignArn=self.campaign_arn,
                userId=user_id,
                numResults=num_results
            )
            return response.get('itemList', [])
        except ClientError as e:
            logger.error(f"Personalize API Error: {e}")
            return []

    def get_donor_archetype(self, user_id: str):
        """Maps recommendations to a donor archetype."""
        recommendations = self.get_donor_recommendations(user_id)
        if not recommendations:
            return "General"
        
        # Simple archetype mapping logic based on top recommended ITEM_ID
        top_item = recommendations[0]['itemId']
        
        mapping = {
            "ENVIRONMENT": "Eco-Conscious",
            "CLEAN_WATER": "Health Advocate",
            "DISASTER_RELIEF": "Emergency Responder"
        }
        
        return mapping.get(top_item, "Supporter")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get donor archetypes from Personalize.")
    parser.add_argument("--user-id", type=str, required=True, help="User ID to segment")
    parser.add_argument("--campaign-arn", type=str, required=True, help="Personalize Campaign ARN")
    
    args = parser.parse_args()
    
    inference = PersonalizeInference(args.campaign_arn)
    archetype = inference.get_donor_archetype(args.user_id)
    
    logger.info(f"Donor {args.user_id} archetype identified: {archetype}")
