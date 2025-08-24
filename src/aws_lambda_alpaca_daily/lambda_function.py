import json
import logging
import os
import boto3
from datetime import datetime, timedelta

try:
    from .storage import get_s3_client, read_data, write_data
    from .csv_utils import merge_data
    from .data_sources import AlpacaDataSource
    from .feature_extractors import FeatureExtractor
    from .email_utils import send_status_email
except ImportError:
    from storage import get_s3_client, read_data, write_data
    from csv_utils import merge_data
    from data_sources import AlpacaDataSource
    from feature_extractors import FeatureExtractor
    from email_utils import send_status_email

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
                logger.info(
                    f"Successfully retrieved secret '{aws_secret_name}' from AWS Secrets Manager."
                )

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





def lambda_handler(event, context):
    logger.info("lambda_handler started.")
    
    # Detect trigger source
    if event and event.get("source") == "aws.events":
        logger.info("Triggered by EventBridge (scheduled)")
    elif not event:
        logger.info("Triggered manually (test)")
    else:
        logger.info(f"Triggered by: {event.get('source', 'unknown') if event else 'unknown'}")

    # Load configuration
    config = load_config()
    s3_bucket_name = config["s3_bucket_name"]
    stocks_to_fetch = config["stocks"]
    days_to_fetch = config["days_to_fetch"]
    alpaca_secret_name = config["alpaca_secret_name"]

    # Initialize data source and storage
    try:
        alpaca_secrets = get_secret(alpaca_secret_name)
        data_source = AlpacaDataSource(
            alpaca_secrets["ALPACA_API_KEY_ID"],
            alpaca_secrets["ALPACA_API_SECRET_KEY"]
        )
    except Exception as e:
        logger.critical(f"Failed to retrieve Alpaca API credentials: {e}")
        return {"statusCode": 500, "body": "Failed to retrieve API credentials."}

    s3_client = get_s3_client()
    if s3_client is None:
        logger.info("Running in local testing mode.")
    else:
        logger.info("Running in AWS Lambda environment.")

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days_to_fetch)

    for symbol in stocks_to_fetch:
        logger.info(f"Processing stock: {symbol}")
        s3_key = f"{symbol}.csv"

        # 1. Read existing data
        existing_data = read_data(s3_client, s3_bucket_name, s3_key)

        # 2. Fetch new data from data source
        new_data = data_source.fetch_data(symbol, start_date, end_date)

        if new_data.empty:
            logger.warning(f"No new data fetched for {symbol}. Skipping merge and write.")
            continue

        # 3. Merge, deduplicate, and sort
        merged_data = merge_data(existing_data, new_data)

        # 4. Write updated data back
        try:
            write_data(s3_client, merged_data, s3_bucket_name, s3_key)
            logger.info(f"Successfully updated data for {symbol}.")
        except Exception as e:
            logger.error(f"Failed to write updated data for {symbol}: {e}")
    
    # 5. Extract features
    try:
        input_files = [f"{symbol}.csv" for symbol in stocks_to_fetch]
        
        # Extract all features using single extractor
        extractor = FeatureExtractor(['moving_averages', 'technical_indicators', 'price_changes'])
        extractor.extract_features(input_files, "features_all.csv", s3_client, s3_bucket_name)
        
        logger.info("Feature extraction completed")
    except Exception as e:
        logger.error(f"Feature extraction failed: {e}")

    # Send status email
    is_eventbridge = event and event.get("source") == "aws.events"
    send_status_email(
        is_eventbridge,
        "AWS Lambda Stock Daily - Processing Complete",
        f"Stock data processing completed successfully for symbols: {', '.join(stocks_to_fetch)}"
    )
    
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
