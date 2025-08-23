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
uv sync                # Install main dependencies
uv sync --group test   # Install test dependencies (includes pytest)
uv sync --group dev    # Install development dependencies (includes black)
```

#### Generating requirements.txt for Docker

The Docker build requires `requirements.txt`. Generate it from `pyproject.toml`:

```bash
uv pip compile pyproject.toml -o requirements.txt
```

This creates a `requirements.txt` with only main dependencies (excludes test/dev groups) and pinned versions for reproducible Docker builds.

### Running the Function Locally

For local testing, the function simulates AWS services using local files:
- **Secrets**: Uses `config/alpaca.secrets` file instead of AWS Secrets Manager
- **Storage**: Uses `local_bucket/` directory instead of S3

**Required Setup:**
1. Create `config/alpaca.secrets` file with your Alpaca API credentials
2. The function will automatically create the `local_bucket/` directory during execution

#### Local Secrets Configuration

**Create `config/alpaca.secrets`:**
```json
{
    "ALPACA_API_KEY_ID": "your_key_id",
    "ALPACA_API_SECRET_KEY": "your_secret_key"
}
```

*Note: This file is listed in `.gitignore` and should not be committed to version control. Replace the example values with your actual Alpaca API credentials.*

#### Execute Locally
```bash
uv run python src/aws_lambda_alpaca_daily/lambda_function.py
```

During execution, the function will:
- Read credentials from `config/alpaca.secrets`
- Create `local_bucket/` directory automatically
- Save CSV files locally (e.g., `local_bucket/AAPL.csv`)
- Print data summaries to console for verification

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

### Step 6: Build and Push the Docker Image
The `build_docker_image.sh` script supports two build modes:
1.  **Local-only build**: Creates a local testing image without pushing to ECR
2.  **Push-only build**: Builds and pushes to ECR for Lambda deployment

**Prerequisites:** Ensure Docker Desktop is running before executing any build commands.

1.  **For local testing only:**
    ```bash
    ./build_docker_image.sh
    ```
    This creates `local-aws-lambda-stock-daily:debug` for local Docker testing.

2.  **For ECR deployment:**
    First, authenticate Docker to your ECR registry:
    ```bash
    aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 140023403573.dkr.ecr.us-west-2.amazonaws.com
    ```
    *(Update the region if necessary.)*
    
    Then build and push:
    ```bash
    ./build_docker_image.sh --push
    ```
    This builds and pushes a production-ready image tagged with the current date (e.g., `2025-07-08`).

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

### Monitoring and Logs
When deployed to AWS, the Lambda function logs are automatically sent to **AWS CloudWatch Logs**:
- **Log group**: `/aws/lambda/aws-lambda-stock-daily` (matches your function name)
- **Access**: AWS Console → CloudWatch → Log groups
- **CLI access**: `aws logs describe-log-streams --log-group-name /aws/lambda/aws-lambda-stock-daily`

## Advanced: Testing with a Local Docker Container

This section explains how to test the function in a local Docker container that connects to your live AWS account for secrets and S3 storage. First, build the local testing image using `./build_docker_image.sh` (without `--push` flag) to create the `local-aws-lambda-stock-daily:debug` image.

**Prerequisites:** Ensure Docker Desktop is running.

### 1. Run the Docker Container
Run the container, mounting your local AWS credentials as a read-only volume. This allows the function inside the container to securely interact with your AWS resources (like S3 and Secrets Manager).
```bash
docker run --rm -p 9000:8080 -v ~/.aws:/root/.aws:ro local-aws-lambda-stock-daily:debug
```
- `--rm`: Automatically removes the container when it exits.
- `-p 9000:8080`: Maps port 9000 on your host to port 8080 in the container.
- `-v ~/.aws:/root/.aws:ro`: Mounts your AWS credentials read-only.

### 2. Invoke the Function
With the container running, open a new terminal and send a test invocation request using `curl`:
```bash
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{}'
```
If successful, the function will execute, fetch data from Alpaca, and store it in your S3 bucket. Check the container logs and your S3 bucket to verify the results.

### 3. Stop the Container
To gracefully stop the Docker container, press `Ctrl+C` in the terminal where the container is running. The `--rm` flag will automatically remove the container when it exits.
