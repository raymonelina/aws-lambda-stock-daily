import json
import logging
import os
import boto3
import pandas as pd

from datetime import datetime, timedelta
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.historical import StockHistoricalDataClient

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_secret(aws_secret_name):
    if os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is None:
        """Local execution"""
        try:
            with open("config/alpaca.secrets", "r") as f:
                secrets = json.load(f)
            logger.info("Successfully loaded secrets from config/alpaca.secrets")
            return secrets
        except FileNotFoundError:
            logger.error("Alpaca secrets file not found at config/alpaca.secrets")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from config/alpaca.secrets: {e}")
            raise
    else:
        """Retrieves a secret from AWS Secrets Manage"""
        try:
            client = boto3.client("secretsmanager")
            get_secret_value_response = client.get_secret_value(
                SecretId=aws_secret_name
            )
            if "SecretString" in get_secret_value_response:
                return json.loads(get_secret_value_response["SecretString"])
            else:
                # For binary secrets, you'd handle SecretBinary
                raise ValueError("Secret does not contain a SecretString.")
        except Exception as e:
            logger.error(f"Error retrieving secret '{aws_secret_name}': {e}")
            raise


def load_config(config_path="config/config.json"):
    """Loads configuration from a JSON file."""
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Configuration file not found at {config_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {config_path}: {e}")
        raise


def fetch_alpaca_data(api_key, secret_key, symbol, start_date, end_date):
    """Fetches historical stock data from Alpaca API."""
    try:
        data_client = StockHistoricalDataClient(api_key, secret_key)
        request_params = StockBarsRequest(
            symbol_or_symbols=[symbol],
            timeframe=TimeFrame.Day,
            start=start_date,
            end=end_date,
        )
        bars = data_client.get_stock_bars(request_params)

        if bars and bars.data and symbol in bars.data:
            df = bars.df.loc[symbol]
            # Alpaca returns data with timezone, convert to naive datetime for consistency
            df.index = df.index.tz_localize(None)
            df = df[["open", "high", "low", "close", "volume"]]
            df.index.name = "timestamp"
            return df
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error fetching Alpaca data for {symbol}: {e}")
        return pd.DataFrame()


def read_s3_data(s3_client, bucket_name, key):
    """Reads existing CSV data from S3. If s3_client is None, it's a local test, so return an empty DataFrame."""
    if s3_client is None:
        # Local testing: return an empty DataFrame with expected columns
        logger.info("Running locally, returning empty DataFrame for S3 data.")
        return pd.DataFrame(
            columns=["open", "high", "low", "close", "volume"],
            index=pd.Index([], name="timestamp"),
        )

    try:
        obj = s3_client.get_object(Bucket=bucket_name, Key=key)
        df = pd.read_csv(obj["Body"], index_col="timestamp", parse_dates=True)
        return df
    except s3_client.exceptions.NoSuchKey:
        logger.info(
            f"No existing data found for {key} in {bucket_name}. Starting fresh."
        )
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error reading S3 data for {key}: {e}")
        return pd.DataFrame()


def write_s3_data(s3_client, df, bucket_name, key):
    """Writes DataFrame to S3 or prints to console if s3_client is None."""
    if s3_client is None:
        # Local testing: print DataFrame, bucket_name, and key to console
        logger.info(
            f"Running locally, simulating S3 write for s3://{bucket_name}/{key}. Data:"
        )
        print(f"Bucket: {bucket_name}")
        print(f"Key: {key}")
        print("DataFrame Content:")
        print(df.to_csv(index=False))  # Print as CSV for readability
        return

    try:
        # AWS Lambda execution: write to S3
        csv_buffer = pd.io.common.StringIO()
        df.to_csv(csv_buffer, float_format="%.4f", index_label="timestamp")
        s3_client.put_object(Bucket=bucket_name, Key=key, Body=csv_buffer.getvalue())
        logger.info(f"Successfully wrote data to s3://{bucket_name}/{key}")
    except Exception as e:
        logger.error(f"Error writing data for {key} to S3: {e}")
        raise


def merge_data(existing_df, new_df):
    """Merges new data with existing data, deduplicates, and sorts."""
    if existing_df.empty:
        return new_df.sort_index()
    if new_df.empty:
        return existing_df.sort_index()

    combined_df = pd.concat([existing_df, new_df])
    combined_df = combined_df[~combined_df.index.duplicated(keep="last")]
    return combined_df.sort_index()


def lambda_handler(event, context):
    logger.info("lambda_handler started.")

    # Load configuration
    config = load_config()
    s3_bucket_name = config["s3_bucket_name"]
    stocks_to_fetch = config["stocks"]
    days_to_fetch = config["days_to_fetch"]
    alpaca_secret_name = config["alpaca_secret_name"]

    # Fetch Alpaca API credentials
    try:
        alpaca_secrets = get_secret(alpaca_secret_name)
        alpaca_api_key = alpaca_secrets["ALPACA_API_KEY_ID"]
        alpaca_secret_key = alpaca_secrets["ALPACA_API_SECRET_KEY"]
    except Exception as e:
        logger.critical(f"Failed to retrieve Alpaca API credentials: {e}")
        return {"statusCode": 500, "body": "Failed to retrieve API credentials."}

    s3_client = (
        None
        if os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is None
        else boto3.client("s3")
    )

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days_to_fetch)

    for symbol in stocks_to_fetch:
        logger.info(f"Processing stock: {symbol}")
        s3_key = f"{symbol}.csv"

        # 1. Read existing data from S3
        existing_data = read_s3_data(s3_client, s3_bucket_name, s3_key)

        # 2. Fetch new data from Alpaca
        new_data = fetch_alpaca_data(
            alpaca_api_key, alpaca_secret_key, symbol, start_date, end_date
        )

        if new_data.empty:
            logger.warning(
                f"No new data fetched for {symbol}. Skipping merge and write."
            )
            continue

        # 3. Merge, deduplicate, and sort
        print(existing_data)
        print(new_data)
        merged_data = merge_data(existing_data, new_data)

    logger.info("Lambda function finished.")
    return {"statusCode": 200, "body": "Stock data processing complete."}


if __name__ == "__main__":
    # This block is for local testing.

    # It configures a handler to print logs to the console (stdout).
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    logger.addHandler(stream_handler)

    # It simulates a Lambda invocation by calling the handler directly.
    # We pass None for event and context as they are not used in this simple case.
    logger.info("--- Starting local execution ---")
    lambda_handler(None, None)
    logger.info("--- Finished local execution ---")
