import pytest
import os
from dotenv import load_dotenv
from aws_nonprofit_toolkit.meta_growth_engine import (
    create_custom_audience, 
    upload_donors_to_audience, 
    wait_for_audience_ready, 
    delete_custom_audience,
    MetaConfig
)

# Test Fixtures
TEST_CSV = "tests/fixtures/test_donors.csv"
AUDIENCE_NAME = "E2E_Test_Audience"

@pytest.fixture
def ad_account():
    load_dotenv(override=True)
    # Using the verified ID directly if MetaConfig fails to pick it up, 
    # but MetaConfig.validate(use_sandbox=True) should be updated to point here.
    return "1665767727797768"

@pytest.fixture
def cleanup_audience(ad_account):
    audience_id = None
    yield lambda id: (setattr(cleanup_audience, 'id', id))
    if hasattr(cleanup_audience, 'id'):
        delete_custom_audience(cleanup_audience.id, ad_account)

def test_pipeline_flow(ad_account, cleanup_audience):
    # 1. Create Audience
    aud_id = create_custom_audience(AUDIENCE_NAME, ad_account)
    assert aud_id is not None
    cleanup_audience(aud_id)
    
    # 2. Upload Donors
    vip_count = upload_donors_to_audience(aud_id, TEST_CSV)
    assert vip_count > 0
    
    # 3. Wait for Ready
    ready = wait_for_audience_ready(aud_id, vip_count, use_sandbox=True, max_wait_seconds=600, poll_interval=30)
    assert ready is True
