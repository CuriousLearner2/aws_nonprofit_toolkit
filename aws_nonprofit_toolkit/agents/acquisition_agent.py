from antigravity import Agent
from aws_nonprofit_toolkit.meta_growth_engine import (
    create_custom_audience,
    upload_donors_to_audience,
    wait_for_audience_ready,
    MetaConfig
)
import logging

class AcquisitionAgent(Agent):
    """
    An agentic wrapper for the Meta Acquisition Pipeline.
    Manages synchronization state and ensures all safety guards are met.
    """
    def __init__(self, name: str):
        super().__init__(name=name)
        self.logger = logging.getLogger("AcquisitionAgent")

    async def sync_donors(self, audience_name: str, file_path: str, is_sandbox: bool = True):
        self.logger.info(f"Starting donor sync for {audience_name}...")
        
        target_account_id = MetaConfig.validate(use_sandbox=is_sandbox)
        
        # 1. Audience Creation
        aud_id = create_custom_audience(audience_name, target_account_id)
        if not aud_id:
            return {"status": "failed", "error": "Audience creation failed"}

        # 2. Upload with dynamic VIP count
        vip_count = upload_donors_to_audience(aud_id, file_path)
        self.logger.info(f"Uploaded {vip_count} VIP donors.")
        
        # 3. Polling and Readiness
        ready = wait_for_audience_ready(aud_id, vip_count, use_sandbox=is_sandbox)
        
        if ready:
            return {"status": "success", "audience_id": aud_id, "vip_count": vip_count}
        else:
            return {"status": "failed", "error": "Audience failed readiness check"}
