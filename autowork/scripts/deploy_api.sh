#!/usr/bin/env bash
# Copyright 2026 AutoWork Authors
#
# Builds and deploys the AutoWork API service to Google Cloud Run.

set -euo pipefail

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project)}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/autowork-repo/autowork-api:latest"

echo "============================================================"
echo "Deploying AutoWork API to Google Cloud Run"
echo "Project: $PROJECT_ID | Region: $REGION"
echo "============================================================"

# Build and Push Image via Cloud Build
gcloud builds submit --tag "$IMAGE_URI" .

# Deploy to Cloud Run
gcloud run deploy autowork-api \
  --image "$IMAGE_URI" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --service-account "autowork-api-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},AUTOWORK_CLOUD_MODE=true" \
  --min-instances 0 \
  --max-instances 5 \
  --memory 1Gi \
  --cpu 1

echo "============================================================"
echo "✓ AutoWork API successfully deployed!"
echo "URL: $(gcloud run services describe autowork-api --region="$REGION" --format='value(status.url)')"
echo "============================================================"
