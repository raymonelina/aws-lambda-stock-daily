# Base image
FROM amazonlinux:2023

# Install Python 3.11, build tools, OpenBLAS, and pkg-config
RUN yum update -y && \
    yum install -y \
      python3.11 python3.11-devel \
      gcc gcc-c++ make git \
      openblas openblas-devel blas blas-devel \
      cmake pkgconf-pkg-config && \
    alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 && \
    python3 -m ensurepip && \
    pip3 install --upgrade pip uv

# Ensure meson can find OpenBLAS
ENV PKG_CONFIG_PATH=/usr/lib64/pkgconfig

# Set working directory
WORKDIR /app

# Copy dependency files first (use Docker layer cache)
COPY pyproject.toml uv.lock ./

# Install deps with uv (NumPy builds with OpenBLAS)
RUN uv sync

# Copy the rest of your code
COPY src/ ./src/

# Default command
CMD ["python3", "src/aws_lambda_alpaca_daily/lambda_function.py"]
