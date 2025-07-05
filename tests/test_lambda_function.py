import pandas as pd

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


def test_write_s3_data():
    # The function body is currently empty, so we can pass None for the client.
    df = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
    lambda_function.write_s3_data(None, df, "bucket", "key")


def test_merge_data():
    df1 = pd.DataFrame({"col1": [1, 2]})
    df2 = pd.DataFrame({"col1": [3, 4]})
    lambda_function.merge_data(df1, df2)


def test_lambda_handler():
    lambda_function.lambda_handler(None, None)
