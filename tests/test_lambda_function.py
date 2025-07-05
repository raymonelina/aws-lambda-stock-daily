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


# --- Test get_secret ---
def test_get_secret(secretsmanager_client):
    secret = lambda_function.get_secret(TEST_SECRET_NAME)
    assert secret["ALPACA_API_KEY_ID"] == MOCK_ALPACA_API_KEY
    assert secret["ALPACA_API_SECRET_KEY"] == MOCK_ALPACA_SECRET_KEY


def test_get_secret_not_found(secretsmanager_client):
    with pytest.raises(Exception, match=".*ResourceNotFoundException.*"):
        lambda_function.get_secret("non-existent-secret")


@pytest.fixture(scope="function")
def s3_client(aws_credentials):
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=TEST_S3_BUCKET)
        yield client


def test_load_config():
    config = lambda_function.load_config()
    assert "s3_bucket_name" in config
    assert "stocks" in config
    assert "days_to_fetch" in config
    assert "alpaca_secret_name" in config


def test_fetch_alpaca_data():
    lambda_function.fetch_alpaca_data("key", "secret", "symbol", "start", "end")


def test_read_s3_data_local_case():
    # Test case when s3_client is None (local execution)
    df = lambda_function.read_s3_data(None, "test_bucket", "test_key")
    assert isinstance(df, pd.DataFrame)
    assert df.empty
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert df.index.name == "timestamp"


@mock_aws
def test_write_s3_data_aws_case():
    # Test case when s3_client is provided (AWS execution) using moto
    s3_client = boto3.client("s3", region_name="us-east-1")
    bucket_name = "test_bucket"
    key = "test_key.csv"

    # Create the mock S3 bucket
    s3_client.create_bucket(Bucket=bucket_name)

    # Create a DataFrame with a timestamp index and float values to test formatting
    data = {
        "open": [100.12345, 101.56789],
        "high": [102.98765, 103.43210],
        "low": [99.00001, 100.11111],
        "close": [101.23456, 102.34567],
        "volume": [1000, 2000],
    }
    index = pd.to_datetime(["2023-01-01", "2023-01-02"])
    df = pd.DataFrame(data, index=index)
    df.index.name = "timestamp"

    lambda_function.write_s3_data(s3_client, df, bucket_name, key)

    # Verify the content of the object in the mocked S3 bucket
    response = s3_client.get_object(Bucket=bucket_name, Key=key)
    body = response["Body"].read().decode("utf-8")

    # Generate the expected CSV content using the same parameters as in lambda_function
    expected_csv_buffer = pd.io.common.StringIO()
    df.to_csv(expected_csv_buffer, float_format="%.4f", index_label="timestamp")
    expected_csv = expected_csv_buffer.getvalue()

    assert body == expected_csv


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


def test_lambda_handler():
    lambda_function.lambda_handler(None, None)
