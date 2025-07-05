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


# --- Test read_s3_data ---
def test_read_s3_data_existing(s3_client):
    test_df = pd.DataFrame(
        {
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.5],
            "volume": [1000],
        },
        index=pd.to_datetime(["2023-01-01"]),
    )
    test_df.index.name = "timestamp"
    lambda_function.write_s3_data(s3_client, test_df, TEST_S3_BUCKET, "AAPL.csv")

    read_df = lambda_function.read_s3_data(s3_client, TEST_S3_BUCKET, "AAPL.csv")
    pd.testing.assert_frame_equal(read_df, test_df)


def test_read_s3_data_non_existent(s3_client):
    df = lambda_function.read_s3_data(s3_client, TEST_S3_BUCKET, "NONEXISTENT.csv")
    assert df.empty


# --- Test write_s3_data ---
def test_write_s3_data(s3_client):
    test_df = pd.DataFrame(
        {
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.5],
            "volume": [1000],
        },
        index=pd.to_datetime(["2023-01-01"]),
    )
    test_df.index.name = "timestamp"

    lambda_function.write_s3_data(s3_client, test_df, TEST_S3_BUCKET, "TEST.csv")

    # Verify by reading it back
    obj = s3_client.get_object(Bucket=TEST_S3_BUCKET, Key="TEST.csv")
    read_df = pd.read_csv(obj["Body"], index_col="timestamp", parse_dates=True)
    pd.testing.assert_frame_equal(read_df, test_df)


# --- Test merge_data ---
def test_merge_data_new_empty_existing_full():
    existing_df = pd.DataFrame(
        {
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.5],
            "volume": [1000],
        },
        index=pd.to_datetime(["2023-01-01"]),
    )
    existing_df.index.name = "timestamp"
    new_df = pd.DataFrame()
    merged_df = lambda_function.merge_data(existing_df, new_df)
    pd.testing.assert_frame_equal(merged_df, existing_df)


def test_merge_data_existing_empty_new_full():
    existing_df = pd.DataFrame()
    new_df = pd.DataFrame(
        {
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.5],
            "volume": [1000],
        },
        index=pd.to_datetime(["2023-01-01"]),
    )
    new_df.index.name = "timestamp"
    merged_df = lambda_function.merge_data(existing_df, new_df)
    pd.testing.assert_frame_equal(merged_df, new_df)


def test_merge_data_with_overlap():
    existing_df = pd.DataFrame(
        {
            "open": [100.0, 102.0],
            "high": [101.0, 103.0],
            "low": [99.0, 101.5],
            "close": [100.5, 102.5],
            "volume": [1000, 1100],
        },
        index=pd.to_datetime(["2023-01-01", "2023-01-02"]),
    )
    existing_df.index.name = "timestamp"

    new_df = pd.DataFrame(
        {
            "open": [102.0, 104.0],
            "high": [103.0, 105.0],
            "low": [101.5, 103.5],
            "close": [102.5, 104.5],
            "volume": [1100, 1200],
        },
        index=pd.to_datetime(["2023-01-02", "2023-01-03"]),
    )
    new_df.index.name = "timestamp"

    expected_df = pd.DataFrame(
        {
            "open": [100.0, 102.0, 104.0],
            "high": [101.0, 103.0, 105.0],
            "low": [99.0, 101.5, 103.5],
            "close": [100.5, 102.5, 104.5],
            "volume": [1000, 1100, 1200],
        },
        index=pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"]),
    )
    expected_df.index.name = "timestamp"

    merged_df = lambda_function.merge_data(existing_df, new_df)
    pd.testing.assert_frame_equal(merged_df, expected_df)


def test_merge_data_no_overlap():
    existing_df = pd.DataFrame(
        {
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.5],
            "volume": [1000],
        },
        index=pd.to_datetime(["2023-01-01"]),
    )
    existing_df.index.name = "timestamp"

    new_df = pd.DataFrame(
        {
            "open": [102.0],
            "high": [103.0],
            "low": [101.5],
            "close": [102.5],
            "volume": [1100],
        },
        index=pd.to_datetime(["2023-01-02"]),
    )
    new_df.index.name = "timestamp"

    expected_df = pd.DataFrame(
        {
            "open": [100.0, 102.0],
            "high": [101.0, 103.0],
            "low": [99.0, 101.5],
            "close": [100.5, 102.5],
            "volume": [1000, 1100],
        },
        index=pd.to_datetime(["2023-01-01", "2023-01-02"]),
    )
    expected_df.index.name = "timestamp"

    merged_df = lambda_function.merge_data(existing_df, new_df)
    pd.testing.assert_frame_equal(merged_df, expected_df)
