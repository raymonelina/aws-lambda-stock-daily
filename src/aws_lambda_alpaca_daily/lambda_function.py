import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_secret(secret_name):
    logger.info("get_secret started.")


def load_config(config_path="config/config.json"):
    logger.info("load_config started.")


def fetch_alpaca_data(api_key, secret_key, symbol, start_date, end_date):
    logger.info("fetch_alpaca_data started.")


def read_s3_data(s3_client, bucket_name, key):
    logger.info("read_s3_data started.")


def write_s3_data(s3_client, df, bucket_name, key):
    logger.info("write_s3_data started.")


def merge_data(existing_df, new_df):
    logger.info("merge_data started.")


def lambda_handler(event, context):
    logger.info("lambda_handler started.")


if __name__ == "__main__":
    # This block is for local testing.
    # It simulates a Lambda invocation by calling the handler directly.
    # We pass None for event and context as they are not used in this simple case.
    logger.info("--- Starting local execution ---")
    lambda_handler(None, None)
    logger.info("--- Finished local execution ---")
