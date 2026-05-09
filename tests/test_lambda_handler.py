import pytest
import json
import requests
from unittest.mock import patch, MagicMock
from pathlib import Path
from botocore.exceptions import ClientError
from aws_nonprofit_toolkit.lambda_handler import handler

@patch('aws_nonprofit_toolkit.lambda_handler.generate_small_nonprofit')
@patch('aws_nonprofit_toolkit.lambda_handler.generate_large_nonprofit')
@patch('aws_nonprofit_toolkit.lambda_handler.analyze_bias')
@patch('aws_nonprofit_toolkit.lambda_handler.create_custom_audience')
@patch('aws_nonprofit_toolkit.lambda_handler.upload_donors_to_audience')
@patch('aws_nonprofit_toolkit.lambda_handler.upload_to_s3')
@patch('os.getenv')
def test_lambda_handler_success(mock_getenv, mock_s3, mock_upload_meta, mock_create_meta, mock_analyze, mock_gen_large, mock_gen_small, tmp_path):
    def getenv_side_effect(key, default=None):
        if key == "DONOR_COUNT":
            return "2000"
        elif key == "BIAS_RATIO":
            return "0.25"
        elif key == "AWS_PERSONALIZE_BUCKET":
            return "test-bucket"
        return default

    mock_getenv.side_effect = getenv_side_effect
    mock_create_meta.return_value = "aud_123"
    mock_analyze.return_value = True

    event = {}
    context = MagicMock()

    with patch('pathlib.Path.mkdir'):
        response = handler(event, context)

    assert response['statusCode'] == 200
    assert "successful" in response['body']

    # Verify both datasets generated (Dual-Track)
    mock_gen_small.assert_called_once()
    mock_gen_large.assert_called_once()
    # Verify threshold is 20.0 as requested
    mock_analyze.assert_called_once()
    assert mock_analyze.call_args[1]['threshold'] == 20.0

@patch('aws_nonprofit_toolkit.lambda_handler.generate_small_nonprofit')
@patch('aws_nonprofit_toolkit.lambda_handler.generate_large_nonprofit')
@patch('aws_nonprofit_toolkit.lambda_handler.analyze_bias')
def test_lambda_handler_weak_signal(mock_analyze, mock_gen_large, mock_gen_small):
    mock_analyze.return_value = False
    
    with pytest.raises(ValueError) as excinfo:
        with patch('pathlib.Path.mkdir'):
            handler({}, MagicMock())
    
    assert "Signal too weak (< 20%)" in str(excinfo.value)
