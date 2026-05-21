from antigravity import Agent
import logging
import os
from aws_nonprofit_toolkit.personalize_sync import PersonalizeSync
from aws_nonprofit_toolkit.personalize_batch_inference import trigger_batch_inference_job
from aws_nonprofit_toolkit.personalize_segmentation import PersonalizeInference

class PersonalizationAgent(Agent):
    """
    Agentic wrapper for the Amazon Personalize Track 2 Pipeline.
    Manages data sync, model inference, and archetype segmentation.
    """
    def __init__(self, name: str):
        super().__init__(name=name)
        self.logger = logging.getLogger("PersonalizationAgent")
        self.sync = PersonalizeSync()

    async def run_personalization_flow(self, dataset_path: str, bucket: str, role_arn: str, solution_version_arn: str):
        self.logger.info("Starting Personalization flow...")

        # 1. Sync data to S3
        self.sync.upload_to_s3(dataset_path, bucket)

        # 2. Trigger Batch Inference
        output_s3 = f"s3://{bucket}/results/"
        input_s3 = f"s3://{bucket}/{os.path.basename(dataset_path)}"
        
        job_arn = trigger_batch_inference_job(
            solution_version_arn=solution_version_arn,
            input_s3_path=input_s3,
            output_s3_path=output_s3,
            role_arn=role_arn
        )
        
        self.logger.info(f"Batch inference job started: {job_arn}")
        return {"status": "started", "job_arn": job_arn}

    async def get_donor_segment(self, user_id: str, campaign_arn: str):
        """Perform ad-hoc segmentation for a specific donor."""
        inference = PersonalizeInference(campaign_arn)
        return inference.get_donor_archetype(user_id)
