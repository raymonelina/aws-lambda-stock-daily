# AWS Lambda Stock Daily

This project contains an AWS Lambda function for fetching daily stock data.

## Running Tests

To run the unit tests, first ensure you have the project dependencies installed by synchronizing your virtual environment:

```bash
uv sync
```

Then, run pytest from the root directory:

```bash
uv run pytest
```

## Running Locally

To execute the `main()` function within the Lambda handler for local testing, run the following command:

```bash
uv run python src/aws_lambda_alpaca_daily/lambda_function.py
```

## Building Docker Image

To build the Docker image, run the `build_docker_image.sh` script:

```bash
./build_docker_image.sh
```
