import pytest
import pandas as pd
import boto3
import json
import os
from moto import mock_aws

from aws_lambda_alpaca_daily import lambda_function




# Mock configuration for testing
TEST_S3_BUCKET = "aws-lambda-stock-daily"
TEST_SECRET_NAME = "alpaca-api-credentials"
TEST_CONFIG_CONTENT = {
    "s3_bucket_name": TEST_S3_BUCKET,
    "stocks": ["AAPL", "GOOGL"],
    "days_to_fetch": 5,
    "alpaca_secret_name": TEST_SECRET_NAME,
}

# Mock Alpaca API credentials
MOCK_ALPACA_API_KEY = "mock_api_key"
MOCK_ALPACA_SECRET_KEY = "mock_secret_key"


@pytest.fixture(scope="function")
def secretsmanager_client(aws_credentials):
    with mock_aws():
        client = boto3.client("secretsmanager", region_name="us-east-1")
        client.create_secret(
            Name=TEST_SECRET_NAME,
            SecretString=json.dumps(
                {
                    "ALPACA_API_KEY_ID": MOCK_ALPACA_API_KEY,
                    "ALPACA_API_SECRET_KEY": MOCK_ALPACA_SECRET_KEY,
                }
            ),
        )
        yield client


@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["AWS_LAMBDA_FUNCTION_NAME"] = "testing"
    os.environ["AWS_REGION"] = "us-east-1"


@pytest.fixture(scope="function")
def s3_client(aws_credentials):
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=TEST_S3_BUCKET)
        yield client


# --- Test get_secret ---
def test_get_secret(secretsmanager_client):
    secret = lambda_function.get_secret(TEST_SECRET_NAME)
    assert secret["ALPACA_API_KEY_ID"] == MOCK_ALPACA_API_KEY
    assert secret["ALPACA_API_SECRET_KEY"] == MOCK_ALPACA_SECRET_KEY


def test_get_secret_not_found(secretsmanager_client):
    with pytest.raises(Exception, match=".*ResourceNotFoundException.*"):
        lambda_function.get_secret("non-existent-secret")


# --- Test load_config ---
def test_load_config():
    config = lambda_function.load_config()
    assert "s3_bucket_name" in config
    assert "stocks" in config
    assert "days_to_fetch" in config
    assert "alpaca_secret_name" in config




