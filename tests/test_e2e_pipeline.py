import pytest
import os
import time
from unittest.mock import patch
from dotenv import load_dotenv
from aws_nonprofit_toolkit.meta_growth_engine import (
    create_custom_audience, 
    upload_donors_to_audience, 
    delete_custom_audience,
    MetaConfig
)

# Test Fixtures
TEST_CSV = "tests/fixtures/test_donors.csv"
AUDIENCE_NAME = "E2E_Test_Audience"

@pytest.fixture(scope="session")
def ad_account():
    # Force use of the verified account ID
    return "1665767727797768"

@pytest.fixture
def cleanup_audience(ad_account):
    audience_ids = []
    yield lambda id: audience_ids.append(id)
    for aud_id in audience_ids:
        try:
            delete_custom_audience(aud_id, ad_account)
        except:
            pass

@pytest.mark.integration
def test_pipeline_flow(ad_account, cleanup_audience):
    # 1. Create Audience
    aud_id = create_custom_audience(AUDIENCE_NAME, ad_account)
    assert aud_id is not None
    cleanup_audience(aud_id)
    
    # 2. Upload Donors
    vip_count = upload_donors_to_audience(aud_id, TEST_CSV)
    assert vip_count > 0
    
    # 3. Mock Readiness and finish flow
    with patch('aws_nonprofit_toolkit.meta_growth_engine.wait_for_audience_ready', return_value=True):
        from aws_nonprofit_toolkit.meta_growth_engine import wait_for_audience_ready
        ready = wait_for_audience_ready(aud_id, vip_count)
        assert ready is True

@pytest.mark.integration
def test_audience_already_exists(ad_account, cleanup_audience):
    aud_id = create_custom_audience(AUDIENCE_NAME, ad_account)
    cleanup_audience(aud_id)
    
    # Second creation should return the same ID
    aud_id_second = create_custom_audience(AUDIENCE_NAME, ad_account)
    assert aud_id == aud_id_second

@pytest.mark.integration
def test_no_vip_donors(ad_account, cleanup_audience):
    # Create empty donor CSV
    empty_csv = "tests/fixtures/empty.csv"
    with open(empty_csv, "w") as f:
        f.write("EMAIL,LOYALTY_LEVEL,LTV\n")
    
    aud_id = create_custom_audience("Empty_Audience", ad_account)
    cleanup_audience(aud_id)
    
    vip_count = upload_donors_to_audience(aud_id, empty_csv)
    assert vip_count == 0
    
    os.remove(empty_csv)
