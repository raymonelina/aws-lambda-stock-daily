#!/bin/bash

IMAGE_NAME="aws-lambda-stock-daily"
TAG="latest"

echo "Building Docker image: ${IMAGE_NAME}:${TAG}"

docker build -t ${IMAGE_NAME}:${TAG} .

if [ $? -eq 0 ]; then
  echo "Docker image built successfully: ${IMAGE_NAME}:${TAG}"
  echo "You can run it using: docker run -it ${IMAGE_NAME}:${TAG}"
else
  echo "Error: Docker image build failed."
  exit 1
fi
