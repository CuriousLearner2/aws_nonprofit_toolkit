from antigravity import Agent
import logging
from aws_nonprofit_toolkit.agents.acquisition_agent import AcquisitionAgent
from aws_nonprofit_toolkit.agents.personalization_agent import PersonalizationAgent

class NonprofitOrchestrator(Agent):
    """
    Central orchestrator for the nonprofit growth flywheel.
    Manages the handoff between acquisition and retention tracks.
    """
    def __init__(self, name: str):
        super().__init__(name=name)
        self.logger = logging.getLogger("NonprofitOrchestrator")
        self.acquisition = AcquisitionAgent("AcquisitionTrack")
        self.retention = PersonalizationAgent("RetentionTrack")

    async def execute_full_flywheel(self, config: dict):
        self.logger.info("Starting Full Nonprofit Growth Flywheel...")

        # 1. Acquisition Track (Meta)
        sync_result = await self.acquisition.sync_donors(
            audience_name=config["audience_name"],
            file_path=config["donor_file"]
        )
        
        if sync_result["status"] == "success":
            self.logger.info("Acquisition successful. Transitioning to Retention.")
            
            # 2. Personalization Track (Personalize)
            await self.retention.run_personalization_flow(
                dataset_path=config["interactions_file"],
                bucket=config["bucket"],
                role_arn=config["role_arn"],
                solution_version_arn=config["solution_version_arn"]
            )
            return {"status": "complete", "acquisition": sync_result}
        else:
            self.logger.error("Acquisition failed. Aborting flywheel.")
            return {"status": "failed", "error": sync_result.get("error")}
