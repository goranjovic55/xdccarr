#!/bin/bash
# Build and push multi-arch Docker image
# Requires: docker buildx

IMAGE_NAME="${1:-xdccarr}"
TAG="${2:-latest}"
REGISTRY="${3:-ghcr.io/gfrancini}"

# Create buildx builder if not exists
docker buildx create --name multiarch --use 2>/dev/null || docker buildx use multiarch

# Build for multiple architectures
docker buildx build \
  --platform linux/amd64,linux/arm64,linux/arm/v7 \
  --tag "${REGISTRY}/${IMAGE_NAME}:${TAG}" \
  --tag "${REGISTRY}/${IMAGE_NAME}:latest" \
  -f docker/Dockerfile \
  --push \
  .

echo "Built and pushed: ${REGISTRY}/${IMAGE_NAME}:${TAG}"
