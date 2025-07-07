# ------------------------------------------------------------------------------
# Base Image
# ------------------------------------------------------------------------------
# Use the official AWS Lambda Python 3.11 image as the foundation.
# This image includes the Lambda Runtime Interface Client (RIC) and other essentials
# for running Python functions on AWS Lambda.
FROM public.ecr.aws/lambda/python:3.11

# Install dependencies into the directory AWS Lambda uses at runtime
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt -t "${LAMBDA_TASK_ROOT}"

# ------------------------------------------------------------------------------
# Application Code
# ------------------------------------------------------------------------------
# Copy application source code into Lambda's working directory
COPY src/ ${LAMBDA_TASK_ROOT}/

# Copy configuration file (ensure path matches runtime expectations)
COPY config/config.json ${LAMBDA_TASK_ROOT}/config/config.json

# ------------------------------------------------------------------------------
# Lambda Execution Configuration
# ------------------------------------------------------------------------------
# Specify the default command to execute the Lambda function handler.
# The base image's entrypoint will invoke this handler when the Lambda is triggered.
CMD ["aws_lambda_alpaca_daily.lambda_function.lambda_handler"]