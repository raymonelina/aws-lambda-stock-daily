# AWS Lambda Stock Daily Data Fetcher

This project provides an AWS Lambda function that automatically fetches daily historical stock price data from the Alpaca API and stores it in a designated Amazon S3 bucket. The function is designed to be triggered on a schedule by Amazon EventBridge. It reads a JSON configuration file to determine which stock symbols to track, how many days of historical data to retrieve, and the S3 bucket for storage.

A key feature of this function is its ability to merge new data with existing historical data in S3. This ensures a continuous, deduplicated, and sorted dataset for each stock symbol, preventing data gaps and redundant entries.

## Project Structure

```
.
├── src/
│   └── aws_lambda_alpaca_daily/
│       └── lambda_function.py
├── config/
│   └── config.json
├── tests/
│   └── test_lambda_function.py
├── pyproject.toml
├── Dockerfile
├── build_docker_image.sh
└── README.md
```

## Configuration

Create a `config/config.json` file with the following structure:

```json
{
  "s3_bucket_name": "your-s3-bucket-name",
  "stocks": ["AAPL", "GOOGL"],
  "days_to_fetch": 1000,
  "alpaca_secret_name": "alpaca-api-credentials"
}
```

### Alpaca Secret Format in AWS Secrets Manager

Your Alpaca API credentials should be stored in AWS Secrets Manager with the following JSON format:

```json
{
  "ALPACA_API_KEY_ID": "your_key_id",
  "ALPACA_API_SECRET_KEY": "your_secret_key"
}
```

## Local Development

### Dependency Management

This project uses `uv` for dependency management. Dependencies are defined in `pyproject.toml`.

To install dependencies for local development and testing:

```bash
uv sync
```

### Running the Function Locally

For local testing, you can execute the `lambda_function.py` script directly. This will simulate the Lambda environment and use local files for secrets and data storage.

```bash
uv run python src/aws_lambda_alpaca_daily/lambda_function.py
```

### Running Tests

Unit and integration tests are located in the `tests/` directory. `pytest` is used as the test runner.

To run the tests:

```bash
uv run pytest
```

## Building and Testing the Docker Image Locally

This section describes how to build the Docker image and test it on your local machine.

### 1. Build the Docker Image

The `build_docker_image.sh` script automates the process of building the Docker image.

```bash
./build_docker_image.sh
```

### 2. Run the Docker Container

Once the image is built, run the container with the following command:

```bash
docker run -p 9000:8080 -v ~/.aws:/root/.aws aws-lambda-stock-daily:latest
```
This command does the following:
- Runs the `aws-lambda-stock-daily:latest` image.
- Maps port 9000 on your local machine to port 8080 inside the container (the default port for the Lambda Runtime Interface Emulator).
- Mounts your local AWS credentials (`~/.aws`) into the container at `/root/.aws`. This allows the Lambda function inside the container to use your local AWS credentials to access services like S3 and Secrets Manager.

### 3. Invoke the Function

With the container running, open a new terminal and send a request to invoke the function:

```bash
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '''{}'''
```

## AWS Deployment

This section covers deploying the containerized Lambda function to AWS.

### Prerequisites

*   AWS CLI configured with appropriate permissions.
*   Docker installed.
*   An Amazon ECR repository created to store your Docker image.

### IAM Role Requirements

The Lambda function's IAM role will require the following permissions:

*   Read/Write access to the specified S3 bucket (`s3:GetObject`, `s3:PutObject`, `s3:ListBucket`)
*   Read access to the specified secret in AWS Secrets Manager (`secretsmanager:GetSecretValue`)
*   Permissions to pull images from Amazon ECR (`ecr:GetDownloadUrlForLayer`, `ecr:BatchGetImage`, `ecr:BatchCheckLayerAvailability`)
*   Logging permissions for CloudWatch Logs (`logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`)

### Push Container Image to ECR

After building the image locally, you will need to tag it and push it to your Amazon ECR repository.

1.  **Authenticate Docker to your ECR registry:**
    ```bash
    aws ecr get-login-password --region <your-region> | docker login --username AWS --password-stdin <your-aws-account-id>.dkr.ecr.<your-region>.amazonaws.com
    ```

2.  **Tag the image:**
    ```bash
    docker tag aws-lambda-stock-daily:latest <your-aws-account-id>.dkr.ecr.<your-region>.amazonaws.com/<your-ecr-repo-name>:latest
    ```

3.  **Push the image to ECR:**
    ```bash
    docker push <your-aws-account-id>.dkr.ecr.<your-region>.amazonaws.com/<your-ecr-repo-name>:latest
    ```
    *(Replace `<your-aws-account-id>`, `<your-region>`, and `<your-ecr-repo-name>` with your specific values.)*

### Lambda Configuration

After pushing the image to ECR, you can create or update your Lambda function in the AWS Management Console or via AWS CLI/CloudFormation:

*   **Runtime**: Container Image
*   **Image URI**: Specify the ECR image URI (e.g., `your_aws_account_id.dkr.ecr.your_region.amazonaws.com/your-repo-name:latest`)
*   **Timeout**: Adjust based on the number of stocks and `days_to_fetch` (e.g., 30 seconds or more).
*   **Memory**: Start with 256 MB and adjust based on performance.
*   **Execution Role**: Assign the IAM role with the necessary permissions as described above.

### EventBridge Rule

To trigger the Lambda function on a daily schedule, create an Amazon EventBridge (CloudWatch Events) rule:

*   **Rule type**: Schedule
*   **Target**: Your Lambda function.

## AWS Setup Checklist

1.  Create and configure an S3 bucket for storing stock data.
2.  Create a secret in AWS Secrets Manager for your Alpaca API credentials.
3.  Create an IAM role for the Lambda function with the necessary least-privilege permissions.
4.  Create an Amazon ECR repository.
5.  Build and push the Docker image to Amazon ECR.
6.  Create and configure the AWS Lambda function using the container image.
7.  Create an Amazon EventBridge rule to schedule the Lambda function's execution.
