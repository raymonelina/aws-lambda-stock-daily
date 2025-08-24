import pytest
import pandas as pd
import boto3
import os
from moto import mock_aws
from aws_lambda_alpaca_daily.storage import read_data, write_data, get_s3_client


TEST_S3_BUCKET = "test-storage-bucket"


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


def test_read_data_existing(s3_client):
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
    write_data(s3_client, test_df, TEST_S3_BUCKET, "AAPL.csv")

    read_df = read_data(s3_client, TEST_S3_BUCKET, "AAPL.csv")
    pd.testing.assert_frame_equal(read_df, test_df)


def test_read_data_non_existent(s3_client):
    df = read_data(s3_client, TEST_S3_BUCKET, "NONEXISTENT.csv")
    assert df.empty


def test_write_data(s3_client):
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

    write_data(s3_client, test_df, TEST_S3_BUCKET, "TEST.csv")

    # Verify by reading it back
    obj = s3_client.get_object(Bucket=TEST_S3_BUCKET, Key="TEST.csv")
    read_df = pd.read_csv(obj["Body"], index_col="timestamp", parse_dates=True)
    pd.testing.assert_frame_equal(read_df, test_df)


def test_get_s3_client_lambda_environment(monkeypatch):
    """Test get_s3_client returns boto3 client in Lambda environment."""
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", "test-function")
    client = get_s3_client()
    assert client is not None


def test_get_s3_client_local_environment(monkeypatch):
    """Test get_s3_client returns None in local environment."""
    monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)
    client = get_s3_client()
    assert client is None