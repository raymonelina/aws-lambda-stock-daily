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

This section covers running the function and tests on your local machine without Docker.

### Dependency Management

This project uses `uv` for dependency management. Dependencies are defined in `pyproject.toml`.

To install dependencies for local development and testing:

```bash
uv sync
```

### Running the Function Locally

For local testing, you can execute the `lambda_function.py` script directly. This simulates the Lambda environment and uses local files for secrets and data storage.

Before running, you must create a `config/alpaca.secrets` file with your Alpaca API credentials:

```json
{
    "ALPACA_API_KEY_ID": "YOUR_API_KEY_ID",
    "ALPACA_API_SECRET_KEY": "YOUR_SECRET_KEY"
}
```
*Note: This file is listed in `.gitignore` and should not be committed to version control.*

Then, execute the script:
```bash
uv run python src/aws_lambda_alpaca_daily/lambda_function.py
```

### Running Tests

Unit and integration tests are located in the `tests/` directory. `pytest` is used as the test runner.

To run the tests:

```bash
uv run pytest
```

## AWS Deployment Guide

This section provides a step-by-step guide to deploying the Lambda function to your AWS account.

### Prerequisites
- You have an AWS account.
- You have the [AWS CLI](https://aws.amazon.com/cli/) installed.
- You have [Docker](https://www.docker.com/get-started) installed.

### Step 1: Configure Local AWS CLI
First, configure your local AWS CLI with credentials that have permissions to manage IAM, S3, ECR, Lambda, and EventBridge.

```bash
aws configure
```
Follow the prompts to enter your AWS Access Key ID, Secret Access Key, default region, and output format.

### Step 2: Create an S3 Bucket
The Lambda function needs an S3 bucket to store the stock data. Create one using the AWS CLI:

```bash
aws s3api create-bucket --bucket your-unique-bucket-name --region your-aws-region
```
*Replace `your-unique-bucket-name` and `your-aws-region`.*
**Action:** Update `config/config.json` with your bucket name.

### Step 3: Store Alpaca Credentials in AWS Secrets Manager
Create a secret to securely store your Alpaca API keys.

1.  Create a JSON file named `alpaca-secret.json` with your credentials:
    ```json
    {
      "ALPACA_API_KEY_ID": "your_key_id",
      "ALPACA_API_SECRET_KEY": "your_secret_key"
    }
    ```
2.  Create the secret in AWS Secrets Manager:
    ```bash
    aws secretsmanager create-secret --name alpaca-api-credentials --secret-string file://alpaca-secret.json
    ```
**Action:** Ensure the secret name (`alpaca-api-credentials`) matches the `alpaca_secret_name` in `config/config.json`.

### Step 4: Create an IAM Role for the Lambda Function
The Lambda function needs permissions to access other AWS services.

**Action:** Create an IAM role named `lambda-stock-daily-role` with, at minimum, the following permissions:
- `s3:GetObject`, `s3:PutObject`, `s3:ListBucket` on the target S3 bucket.
- `secretsmanager:GetSecretValue` on the Alpaca credentials secret.
- `ecr:GetDownloadUrlForLayer`, `ecr:BatchGetImage`, `ecr:BatchCheckLayerAvailability`.
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`.

*(Detailed policy JSON and `create-role` commands would be provided here in a real-world scenario. For brevity, we'll summarize.)*

### Step 5: Create an Amazon ECR Repository
Create a private ECR repository to host your Docker image.

```bash
aws ecr create-repository --repository-name zdomain --image-scanning-configuration scanOnPush=true
```

### Step 6: Build and Push the Docker Image to ECR
The `build_docker_image.sh` script automates building the Docker image and pushing it to the pre-configured Amazon ECR repository.

1.  **Authenticate Docker to your ECR registry:**
    Before running the script, ensure Docker is authenticated with Amazon ECR.
    ```bash
    aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 140023403573.dkr.ecr.us-west-2.amazonaws.com
    ```
    *(This command assumes your ECR repository is in `us-west-2`. Update the region if necessary.)*

2.  **Execute the build and push script:**
    This script tags the image with the current date (e.g., `2025-07-07`) and pushes it to ECR.
    ```bash
    ./build_docker_image.sh
    ```
    Upon success, the script will inspect the pushed image in ECR to confirm the push.

### Step 7: Create the Lambda Function
Create the Lambda function from the container image in ECR.

**Action:** In the AWS Lambda console or using the AWS CLI:
- Choose "Create function" and select "Container image".
- **Function name:** `aws-lambda-stock-daily`
- **Container image URI:** Browse for the ECR image you pushed from the `zdomain` repository.
- **Execution role:** Attach the `lambda-stock-daily-role` you created in Step 4.
- Adjust **Timeout** and **Memory** settings as needed (e.g., 30 seconds, 256 MB).

### Step 8: Schedule the Function with Amazon EventBridge
Finally, create a rule to trigger your function on a schedule.

**Action:** In the Amazon EventBridge console:
- Create a new rule with a **Schedule** pattern.
- For the schedule, you could use a cron expression like `cron(0 18 * * ? *)` to run at 6 PM UTC daily.
- For the **Target**, select your `aws-lambda-stock-daily` Lambda function.

## Advanced: Testing with a Local Docker Container

This section explains how to test the function in a local Docker container that connects to your live AWS account for secrets and S3 storage. This is useful for verifying the function's behavior before deploying it.

### 1. Build the Local Docker Image
First, build a local version of the Docker image. This image will not be pushed to ECR.
```bash
docker build -t aws-lambda-stock-daily:latest .
```

### 2. Run the Docker Container
Run the container, mounting your local AWS credentials as a read-only volume. This allows the function inside the container to securely interact with your AWS resources (like S3 and Secrets Manager).
```bash
docker run --rm -p 9000:8080 -v ~/.aws:/root/.aws:ro local-aws-lambda-stock-daily:debug
```
- `--rm`: Automatically removes the container when it exits.
- `-p 9000:8080`: Maps port 9000 on your host to port 8080 in the container.
- `-v ~/.aws:/root/.aws:ro`: Mounts your AWS credentials read-only.

### 3. Invoke the Function
With the container running, open a new terminal and send a test invocation request using `curl`:
```bash
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{}'
```
If successful, the function will execute, fetch data from Alpaca, and store it in your S3 bucket. Check the container logs and your S3 bucket to verify the results.