import pytest
import responses
import json
import os
from aws_nonprofit_toolkit.meta_growth_engine import (
    hash_data, 
    create_custom_audience, 
    upload_donors_to_audience, 
    create_lookalike_audience,
    MetaConfig
)

def test_hash_data():
    """Verify that hashing is consistent and lowercase-normalized."""
    email = " Test@Example.Com "
    expected = "973dfe463ec85785f5f95af5ba3906eedb2d931c24e69824a89ea65dba4e813b"
    assert hash_data(email) == expected

@responses.activate
def test_create_custom_audience_success(monkeypatch):
    """Verify successful audience creation with mocked API."""
    monkeypatch.setattr(MetaConfig, "ACCESS_TOKEN", "fake_token")
    monkeypatch.setattr(MetaConfig, "AD_ACCOUNT_ID", "12345")
    
    responses.add(
        responses.POST,
        "https://graph.facebook.com/v21.0/act_12345/customaudiences",
        json={"id": "audience_99"},
        status=200
    )
    
    aud_id = create_custom_audience("Test Audience", "12345")
    assert aud_id == "audience_99"

@responses.activate
def test_create_custom_audience_failure(monkeypatch):
    """Verify error handling on API failure."""
    monkeypatch.setattr(MetaConfig, "ACCESS_TOKEN", "fake_token")
    monkeypatch.setattr(MetaConfig, "AD_ACCOUNT_ID", "12345")
    
    responses.add(
        responses.POST,
        "https://graph.facebook.com/v21.0/act_12345/customaudiences",
        json={"error": {"message": "Invalid token"}},
        status=401
    )
    
    # create_custom_audience has retry logic
    with pytest.raises(Exception):
        create_custom_audience("Test Audience", "12345")

def test_config_validation_error(monkeypatch):
    """Verify that missing config raises ValueError."""
    monkeypatch.setattr(MetaConfig, "ACCESS_TOKEN", None)
    with pytest.raises(ValueError, match="Missing META_ACCESS_TOKEN"):
        create_custom_audience("Test Audience", "12345")

@responses.activate
def test_upload_donors_batching(tmp_path, monkeypatch):
    """Verify that donors are uploaded in multiple batches if they exceed batch_size."""
    monkeypatch.setattr(MetaConfig, "ACCESS_TOKEN", "fake_token")
    monkeypatch.setattr(MetaConfig, "AD_ACCOUNT_ID", "12345")
    monkeypatch.setattr(MetaConfig, "API_VERSION", "v21.0")
    
    # Create a mock CSV with 5 VIPs
    csv_file = tmp_path / "test_users.csv"
    with open(csv_file, "w") as f:
        f.write("USER_ID,EMAIL,LOYALTY_LEVEL\n")
        for i in range(5):
            f.write(f"user_{i},donor_{i}@example.com,VIP\n")
    
    # Mock the API to expect 3 batches (batch size of 2: [0,1], [2,3], [4])
    audience_id = "aud_123"
    url = f"https://graph.facebook.com/v21.0/{audience_id}/users"
    
    responses.add(responses.POST, url, status=200)
    responses.add(responses.POST, url, status=200)
    responses.add(responses.POST, url, status=200)
    
    # Run with small batch size to trigger multiple calls
    upload_donors_to_audience(audience_id, str(csv_file), batch_size=2)
    
    # Verify 3 calls were made
    assert len(responses.calls) == 3
    
    # Verify the third call only had 1 record
    from urllib.parse import parse_qs
    body_str = responses.calls[2].request.body
    parsed_body = parse_qs(body_str)
    payload_json = parsed_body['payload'][0]
    payload_data = json.loads(payload_json)
    assert len(payload_data['data']) == 1

@responses.activate
def test_create_lookalike_audience_success(monkeypatch):
    """Verify successful 1% lookalike audience creation."""
    monkeypatch.setattr(MetaConfig, "ACCESS_TOKEN", "fake_token")
    monkeypatch.setattr(MetaConfig, "AD_ACCOUNT_ID", "12345")
    
    seed_id = "aud_seed_123"
    responses.add(
        responses.POST,
        "https://graph.facebook.com/v21.0/act_12345/customaudiences",
        json={"id": "lookalike_456"},
        status=200
    )
    
    # Ad account ID is act_12345 in URL but 12345 in param
    lla_id = create_lookalike_audience(seed_id, "12345", "Test LLA")
    assert lla_id == "lookalike_456"
    
    # Verify lookalike_spec was passed correctly
    body = responses.calls[0].request.body
    if isinstance(body, bytes):
        body = body.decode()
    assert "LOOKALIKES" in body
    assert "lookalike_spec" in body
    assert "similarity" in body
    assert "0.01" in body
