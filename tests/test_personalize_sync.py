import pytest
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError
from aws_nonprofit_toolkit.personalize_sync import upload_to_s3, trigger_personalize_import, AWSConfig

@patch('boto3.client')
def test_upload_to_s3_success(mock_boto, monkeypatch):
    """Verify successful S3 upload call."""
    monkeypatch.setattr(AWSConfig, "ACCESS_KEY", "fake")
    monkeypatch.setattr(AWSConfig, "SECRET_KEY", "fake")
    monkeypatch.setattr(AWSConfig, "S3_BUCKET", "test-bucket")
    
    mock_s3 = MagicMock()
    mock_boto.return_value = mock_s3
    
    upload_to_s3("dummy.csv", "test-bucket", object_name="remote.csv")
    mock_s3.upload_file.assert_called_once_with("dummy.csv", "test-bucket", "remote.csv")

@patch('boto3.client')
def test_upload_to_s3_retry_logic(mock_boto, monkeypatch):
    """Verify that S3 upload retries on ClientError."""
    monkeypatch.setattr(AWSConfig, "ACCESS_KEY", "fake")
    monkeypatch.setattr(AWSConfig, "SECRET_KEY", "fake")
    monkeypatch.setattr(AWSConfig, "S3_BUCKET", "test-bucket")
    
    mock_s3 = MagicMock()
    # Fail twice, then succeed
    mock_s3.upload_file.side_effect = [
        ClientError({"Error": {"Code": "500", "Message": "Net error"}}, "upload_file"),
        ClientError({"Error": {"Code": "500", "Message": "Net error"}}, "upload_file"),
        None
    ]
    mock_boto.return_value = mock_s3
    
    upload_to_s3("dummy.csv", "test-bucket")
    assert mock_s3.upload_file.call_count == 3

@patch('boto3.client')
def test_upload_to_s3_final_failure(mock_boto, monkeypatch):
    """Verify that S3 upload raises error after max retries."""
    monkeypatch.setattr(AWSConfig, "ACCESS_KEY", "fake")
    monkeypatch.setattr(AWSConfig, "SECRET_KEY", "fake")
    monkeypatch.setattr(AWSConfig, "S3_BUCKET", "test-bucket")
    
    mock_s3 = MagicMock()
    mock_s3.upload_file.side_effect = ClientError({"Error": {"Code": "500", "Message": "Net error"}}, "upload_file")
    mock_boto.return_value = mock_s3
    
    with pytest.raises(ClientError):
        upload_to_s3("dummy.csv", "test-bucket")
    assert mock_s3.upload_file.call_count == 3

@patch('boto3.client')
def test_trigger_personalize_import_success(mock_boto, monkeypatch):
    """Verify successful Personalize import trigger."""
    monkeypatch.setattr(AWSConfig, "ACCESS_KEY", "fake")
    monkeypatch.setattr(AWSConfig, "SECRET_KEY", "fake")
    monkeypatch.setattr(AWSConfig, "S3_BUCKET", "test-bucket")
    
    mock_personalize = MagicMock()
    mock_personalize.create_dataset_import_job.return_value = {'datasetImportJobArn': 'arn:123'}
    mock_boto.return_value = mock_personalize
    
    arn = trigger_personalize_import("dataset-arn", "data.csv", "role-arn")
    assert arn == "arn:123"
    mock_personalize.create_dataset_import_job.assert_called_once()

@patch('boto3.client')
def test_trigger_personalize_import_failure(mock_boto, monkeypatch):
    """Verify error handling for Personalize API failure."""
    monkeypatch.setattr(AWSConfig, "ACCESS_KEY", "fake")
    monkeypatch.setattr(AWSConfig, "SECRET_KEY", "fake")
    
    mock_personalize = MagicMock()
    mock_personalize.create_dataset_import_job.side_effect = ClientError({"Error": {"Code": "400", "Message": "Bad ARN"}}, "create_dataset_import_job")
    mock_boto.return_value = mock_personalize
    
    with pytest.raises(ClientError):
        trigger_personalize_import("bad-arn", "data.csv", "role-arn")

def test_aws_config_validation_missing_key(monkeypatch):
    """Verify error on missing AWS credentials."""
    monkeypatch.setattr(AWSConfig, "ACCESS_KEY", None)
    with pytest.raises(ValueError, match="Missing AWS credentials"):
        AWSConfig.validate()

def test_aws_config_validation_missing_bucket(monkeypatch):
    """Verify error on missing S3 bucket."""
    monkeypatch.setattr(AWSConfig, "ACCESS_KEY", "fake")
    monkeypatch.setattr(AWSConfig, "SECRET_KEY", "fake")
    monkeypatch.setattr(AWSConfig, "S3_BUCKET", None)
    with pytest.raises(ValueError, match="Missing AWS credentials or S3 bucket"):
        AWSConfig.validate()

@patch('boto3.client')
def test_upload_to_s3_default_object_name(mock_boto, monkeypatch):
    """Verify object name defaults to filename."""
    monkeypatch.setattr(AWSConfig, "ACCESS_KEY", "fake")
    monkeypatch.setattr(AWSConfig, "SECRET_KEY", "fake")
    
    mock_s3 = MagicMock()
    mock_boto.return_value = mock_s3
    
    upload_to_s3("path/to/mydata.csv", "test-bucket")
    mock_s3.upload_file.assert_called_once_with("path/to/mydata.csv", "test-bucket", "mydata.csv")

def test_aws_config_override_bucket(monkeypatch):
    """Verify bucket override in validation."""
    monkeypatch.setattr(AWSConfig, "ACCESS_KEY", "fake")
    monkeypatch.setattr(AWSConfig, "SECRET_KEY", "fake")
    monkeypatch.setattr(AWSConfig, "S3_BUCKET", None)
    
    # Should not raise because we provide override
    AWSConfig.validate(bucket_override="custom-bucket")

@patch('boto3.client')
def test_trigger_personalize_import_params(mock_boto, monkeypatch):
    """Verify all parameters are passed correctly to Personalize."""
    monkeypatch.setattr(AWSConfig, "ACCESS_KEY", "fake")
    monkeypatch.setattr(AWSConfig, "SECRET_KEY", "fake")
    monkeypatch.setattr(AWSConfig, "S3_BUCKET", "my-bucket")
    
    mock_personalize = MagicMock()
    mock_personalize.create_dataset_import_job.return_value = {'datasetImportJobArn': 'arn:123'}
    mock_boto.return_value = mock_personalize
    
    trigger_personalize_import("ds-arn", "file.csv", "role-arn")
    
    args, kwargs = mock_personalize.create_dataset_import_job.call_args
    assert kwargs['datasetArn'] == "ds-arn"
    assert kwargs['roleArn'] == "role-arn"
    assert kwargs['dataSource']['dataLocation'] == "s3://my-bucket/file.csv"
