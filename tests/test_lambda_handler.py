import pytest
import json
from unittest.mock import patch, MagicMock
from pathlib import Path
from lambda_handler import handler

@patch('lambda_handler.generate_large_nonprofit')
@patch('lambda_handler.create_custom_audience')
@patch('lambda_handler.upload_donors_to_audience')
@patch('lambda_handler.upload_to_s3')
@patch('os.getenv')
def test_lambda_handler_success(mock_getenv, mock_s3, mock_upload_meta, mock_create_meta, mock_gen, tmp_path):
    """
    Verifies that the lambda_handler correctly orchestrates the 
    generation and synchronization steps.
    """
    # Setup mocks
    mock_getenv.return_value = "test-bucket"
    mock_create_meta.return_value = "aud_123"
    
    # Mock event and context
    event = {}
    context = MagicMock()
    
    # Execute handler
    # We patch Path.mkdir to avoid actual filesystem issues in /tmp if restricted
    with patch('pathlib.Path.mkdir'):
        response = handler(event, context)
    
    # Assertions
    assert response['statusCode'] == 200
    assert "successful" in response['body']
    
    # Verify orchestration order/calls
    mock_gen.assert_called_once()
    mock_create_meta.assert_called_once_with("Daily VIP Sync")
    mock_upload_meta.assert_called_once()
    mock_s3.assert_called_once_with(
        str(Path("/tmp/datasets/large_nonprofit_interactions.csv")), 
        "test-bucket"
    )

@patch('lambda_handler.generate_large_nonprofit')
def test_lambda_handler_failure(mock_gen):
    """
    Verifies that the lambda_handler raises an exception if a step fails.
    """
    mock_gen.side_effect = Exception("Generation Failed")
    
    event = {}
    context = MagicMock()
    
    with pytest.raises(Exception) as excinfo:
        with patch('pathlib.Path.mkdir'):
            handler(event, context)
    
    assert "Generation Failed" in str(excinfo.value)
