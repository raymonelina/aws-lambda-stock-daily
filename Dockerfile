# ------------------------------------------------------------------------------
# Base Image
# ------------------------------------------------------------------------------
# Use the official AWS Lambda Python 3.11 base image, which includes the
# Lambda Runtime Interface Client (RIC).
FROM public.ecr.aws/lambda/python:3.11

# ------------------------------------------------------------------------------
# System Dependencies & Build Tools
# ------------------------------------------------------------------------------
# Install tools required for building Python packages (like NumPy) from source.
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

# Set environment variable to help build tools find the OpenBLAS libraries.
# This is often required for scientific computing packages.
ENV PKG_CONFIG_PATH=/usr/lib64/pkgconfig

# ------------------------------------------------------------------------------
# Application Setup
# ------------------------------------------------------------------------------
# Set the working directory inside the container.
WORKDIR /app

# Install uv, a fast Python package installer.
RUN pip install uv

# Copy dependency definition files.
# This is done separately to leverage Docker's layer caching. The dependencies
# layer will only be rebuilt if these files change.
COPY pyproject.toml uv.lock ./

# Copy the application source code into the container.
COPY src/ ./src/

# Install Python dependencies using uv.
RUN uv sync

# ------------------------------------------------------------------------------
# Lambda Execution
# ------------------------------------------------------------------------------
# Set the default command to run the Lambda handler.
# The base image's entrypoint will execute this handler.
CMD ["src.aws_lambda_alpaca_daily.lambda_function.lambda_handler"]