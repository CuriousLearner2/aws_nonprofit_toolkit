import pytest
import json
import requests
from unittest.mock import patch, MagicMock
from pathlib import Path
from botocore.exceptions import ClientError
from lambda_handler import handler

@patch('lambda_handler.generate_large_nonprofit')
@patch('lambda_handler.analyze_bias')
@patch('lambda_handler.create_custom_audience')
@patch('lambda_handler.upload_donors_to_audience')
@patch('lambda_handler.upload_to_s3')
@patch('os.getenv')
def test_lambda_handler_success(mock_getenv, mock_s3, mock_upload_meta, mock_create_meta, mock_analyze, mock_gen, tmp_path):
    mock_getenv.return_value = "test-bucket"
    mock_create_meta.return_value = "aud_123"
    mock_analyze.return_value = True
    
    event = {}
    context = MagicMock()
    
    with patch('pathlib.Path.mkdir'):
        response = handler(event, context)
    
    assert response['statusCode'] == 200
    assert "successful" in response['body']
    mock_gen.assert_called_once()
    mock_analyze.assert_called_once()

@patch('lambda_handler.generate_large_nonprofit')
@patch('lambda_handler.analyze_bias')
def test_lambda_handler_weak_signal(mock_analyze, mock_gen):
    mock_analyze.return_value = False
    
    with pytest.raises(ValueError) as excinfo:
        with patch('pathlib.Path.mkdir'):
            handler({}, MagicMock())
    
    assert "Signal too weak" in str(excinfo.value)

@patch('lambda_handler.generate_large_nonprofit')
@patch('lambda_handler.analyze_bias')
def test_lambda_handler_aws_error(mock_analyze, mock_gen):
    mock_analyze.return_value = True
    error_response = {'Error': {'Code': 'AccessDenied', 'Message': 'Forbidden'}}
    mock_gen.side_effect = ClientError(error_response, 'PutObject')
    
    with pytest.raises(ClientError):
        with patch('pathlib.Path.mkdir'):
            handler({}, MagicMock())
