import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from aws_nonprofit_toolkit.generate_datasets import generate_small_nonprofit, generate_large_nonprofit
from aws_nonprofit_toolkit.config import SimulationConfig
from aws_nonprofit_toolkit.uncover_signal_no_pandas import analyze_bias
from aws_nonprofit_toolkit.meta_growth_engine import create_custom_audience, upload_donors_to_audience, MetaConfig
from aws_nonprofit_toolkit.personalize_sync import upload_to_s3, AWSConfig

@patch('requests.post')
@patch('boto3.client')
def test_e2e_toolkit_flow(mock_boto, mock_post, tmp_path, monkeypatch, capsys):
    """
    Test the full sequence:
    1. Generate Data
    2. Validate Signal (Bulge)
    3. Mock Sync to Meta
    4. Mock Sync to S3
    """
    # Setup mocks and paths
    monkeypatch.setattr(MetaConfig, "ACCESS_TOKEN", "fake")
    monkeypatch.setattr(MetaConfig, "AD_ACCOUNT_ID", "123")
    monkeypatch.setattr(AWSConfig, "ACCESS_KEY", "fake")
    monkeypatch.setattr(AWSConfig, "SECRET_KEY", "fake")
    monkeypatch.setattr(AWSConfig, "S3_BUCKET", "fake-bucket")
    
    # 1. Generate (Force a small count with high VIP chance for test reliability)
    monkeypatch.setattr(SimulationConfig, "SMALL_USER_COUNT", 10)
    monkeypatch.setattr(SimulationConfig, "LOYALTY_DISTRIBUTION", {"VIP": 1.0})
    
    generate_small_nonprofit(tmp_path, 10)
    generate_large_nonprofit(tmp_path, 1000, 0.50) # 0.25 is now bias_ratio
    
    interactions_path = tmp_path / "large_nonprofit_interactions.csv"
    users_path = tmp_path / "small_nonprofit_users.csv"
    
    # 2. Validate Signal (capture output to ensure it runs)
    analyze_bias(str(interactions_path))
    captured = capsys.readouterr()
    assert "SIGNAL DETECTED" in captured.out
    
    # 3. Sync to Meta (Mocked)
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"id": "aud_123"}
    
    aud_id = create_custom_audience("E2E Test")
    upload_donors_to_audience(aud_id, str(users_path))
    
    assert mock_post.call_count >= 2 # 1 for create, 1 for upload
    
    # 4. Sync to S3 (Mocked)
    mock_s3 = MagicMock()
    mock_boto.return_value = mock_s3
    
    upload_to_s3(str(interactions_path), "fake-bucket")
    mock_s3.upload_file.assert_called_once()
