#!/bin/bash

set -e

IMAGE_NAME="140023403573.dkr.ecr.us-west-2.amazonaws.com/aws-lambda-stock-daily"
TAG=$(date +%Y-%m-%d)
LOCAL_TAG="local-aws-lambda-stock-daily:debug"

echo "🔨 Building and pushing Docker image for Lambda: ${IMAGE_NAME}:${TAG}"

# Step 1: Push-only build (Lambda-safe)
docker buildx build \
  --platform linux/arm64 \
  --no-cache \
  --provenance=false \
  --push \
  -t "${IMAGE_NAME}:${TAG}" \
  .

echo "✅ Image pushed to ECR: ${IMAGE_NAME}:${TAG}"
echo "🔍 Inspecting manifest..."
docker buildx imagetools inspect "${IMAGE_NAME}:${TAG}"

# Step 2: Local-only build for testing (loaded into Docker)
echo "🐳 Building local image for testing: ${LOCAL_TAG}"

docker buildx build \
  --platform linux/arm64 \
  --load \
  -t "${LOCAL_TAG}" \
  .

echo "✅ Local image built: ${LOCAL_TAG}"
docker images | grep "${LOCAL_TAG}"
