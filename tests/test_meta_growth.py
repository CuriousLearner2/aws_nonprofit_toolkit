import pytest
import responses
import json
import os
from aws_nonprofit_toolkit.meta_growth_engine import hash_data, create_custom_audience, MetaConfig

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
    
    aud_id = create_custom_audience("Test Audience")
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
    
    # create_custom_audience has retry logic, so this might take a few seconds
    with pytest.raises(Exception):
        create_custom_audience("Test Audience")

def test_config_validation_error(monkeypatch):
    """Verify that missing config raises ValueError."""
    monkeypatch.setattr(MetaConfig, "ACCESS_TOKEN", None)
    with pytest.raises(ValueError, match="Missing META_ACCESS_TOKEN"):
        create_custom_audience()
