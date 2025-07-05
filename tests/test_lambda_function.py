import pandas as pd
import boto3
from moto import mock_aws

from aws_lambda_alpaca_daily import lambda_function


def test_get_secret():
    secrets = lambda_function.get_secret("test_secret")
    assert "ALPACA_API_KEY_ID" in secrets
    assert "ALPACA_API_SECRET_KEY" in secrets


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


def test_merge_data():
    df1 = pd.DataFrame({"col1": [1, 2]})
    df2 = pd.DataFrame({"col1": [3, 4]})
    lambda_function.merge_data(df1, df2)


def test_lambda_handler():
    lambda_function.lambda_handler(None, None)
