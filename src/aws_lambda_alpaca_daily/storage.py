import os
import boto3
import pandas as pd
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def _get_local_file_path(key):
    local_dir = "local_bucket"
    os.makedirs(local_dir, exist_ok=True)
    return os.path.join(local_dir, key)


def read_data(s3_client, bucket_name, key):
    """Reads CSV data from S3 or local file."""
    if s3_client is None:
        # Local testing
        local_file_path = _get_local_file_path(key)
        if os.path.exists(local_file_path):
            try:
                df = pd.read_csv(local_file_path, index_col="timestamp", parse_dates=True)
                logger.info(f"Local: Data read from {local_file_path}")
                return df
            except Exception as e:
                logger.error(f"Local: Error reading data from {local_file_path}: {e}")
        logger.info("Local: No existing data found. Returning empty DataFrame.")
        return pd.DataFrame(
            columns=["open", "high", "low", "close", "volume"],
            index=pd.Index([], name="timestamp"),
        )

    try:
        obj = s3_client.get_object(Bucket=bucket_name, Key=key)
        df = pd.read_csv(obj["Body"], index_col="timestamp", parse_dates=True)
        logger.info(f"Successfully read data from s3://{bucket_name}/{key}")
        return df
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            logger.info(f"No existing data found for {key} in {bucket_name}. Starting fresh.")
            return pd.DataFrame()
        logger.error(f"Error reading S3 data for {key}: {e}")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error reading S3 data for {key}: {e}")
        return pd.DataFrame()


def write_data(s3_client, df, bucket_name, key):
    """Writes DataFrame to S3 or local file."""
    if s3_client is None:
        # Local testing
        local_file_path = _get_local_file_path(key)
        try:
            df.to_csv(local_file_path, float_format="%.4f", index_label="timestamp")
            logger.info(f"Local: Data written to {local_file_path}")
        except Exception as e:
            logger.error(f"Local: Error writing data to {local_file_path}: {e}")

        logger.info(f"Local: Wrote {key} - {len(df)} rows, {len(df.columns)} columns")
        return

    try:
        csv_buffer = pd.io.common.StringIO()
        df.to_csv(csv_buffer, float_format="%.4f", index_label="timestamp")
        s3_client.put_object(Bucket=bucket_name, Key=key, Body=csv_buffer.getvalue())
        logger.info(f"S3: Wrote {key} - {len(df)} rows, {len(df.columns)} columns")
    except Exception as e:
        logger.error(f"Error writing data for {key} to S3: {e}")
        raise


def get_s3_client():
    """Returns S3 client for AWS Lambda or None for local testing."""
    return None if os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is None else boto3.client("s3")