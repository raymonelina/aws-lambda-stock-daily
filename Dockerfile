# ------------------------------------------------------------------------------
# Base Image
# ------------------------------------------------------------------------------
# Use the official AWS Lambda Python 3.11 image as the foundation.
# This image includes the Lambda Runtime Interface Client (RIC) and other essentials
# for running Python functions on AWS Lambda.
FROM public.ecr.aws/lambda/python:3.11

# Set the working directory within the container. ${LAMBDA_TASK_ROOT} is a
# standard environment variable in AWS Lambda execution environments.
WORKDIR ${LAMBDA_TASK_ROOT}

# ------------------------------------------------------------------------------
# System-Level Dependencies
# ------------------------------------------------------------------------------
# Install build tools and libraries required for compiling Python packages from
# source. This is necessary for packages like NumPy that have C extensions.
RUN yum update -y && \
    yum install -y \
      gcc \
      gcc-c++ \
      make \
      git \
      openblas \
      openblas-devel \
      blas \
      blas-devel \
      cmake \
      pkgconf-pkg-config

# Configure the environment to ensure that build tools can locate the OpenBLAS
# libraries, which provide optimized linear algebra computations.
ENV PKG_CONFIG_PATH=/usr/lib64/pkgconfig

# ------------------------------------------------------------------------------
# Python Application Dependencies
# ------------------------------------------------------------------------------
# Install 'uv', a fast Python package installer, to speed up dependency installation.
RUN pip install uv

# Copy the requirements file first to leverage Docker's layer caching.
# The following dependency installation step will only be re-run if this file changes.
COPY requirements.txt .

# Install dependencies into the directory AWS Lambda uses at runtime
RUN pip install --upgrade pip && \
    pip install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

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