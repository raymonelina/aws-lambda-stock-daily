import pandas as pd

from aws_lambda_alpaca_daily import lambda_function


def test_get_secret():
    lambda_function.get_secret("test_secret")


def test_load_config():
    lambda_function.load_config()


def test_fetch_alpaca_data():
    lambda_function.fetch_alpaca_data("key", "secret", "symbol", "start", "end")


def test_read_s3_data():
    # The function body is currently empty, so we can pass None for the client.
    lambda_function.read_s3_data(None, "bucket", "key")


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
