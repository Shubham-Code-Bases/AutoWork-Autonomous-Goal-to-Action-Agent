#!/usr/bin/env bash
# Copyright 2026 AutoWork Authors
#
# Builds and deploys the AutoWork Background Worker service to Cloud Run and wires Pub/Sub push.

set -euo pipefail

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project)}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
TOPIC_NAME="${PUBSUB_TOPIC:-autowork-executions}"
SUBSCRIPTION_NAME="${PUBSUB_SUBSCRIPTION:-autowork-worker-subscription}"
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/autowork-repo/autowork-worker:latest"

echo "============================================================"
echo "Deploying AutoWork Background Worker to Google Cloud Run"
echo "Project: $PROJECT_ID | Region: $REGION"
echo "============================================================"

# Build and Push Image via Cloud Build
gcloud builds submit --tag "$IMAGE_URI" .

# Deploy Worker to Cloud Run
gcloud run deploy autowork-worker \
  --image "$IMAGE_URI" \
  --command python \
  --args worker/main.py \
  --region "$REGION" \
  --platform managed \
  --no-allow-unauthenticated \
  --service-account "autowork-worker-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},AUTOWORK_CLOUD_MODE=true" \
  --min-instances 0 \
  --max-instances 10 \
  --memory 2Gi \
  --cpu 2 \
  --timeout 900

WORKER_URL=$(gcloud run services describe autowork-worker --region="$REGION" --format='value(status.url)')

# Create or Update Pub/Sub Push Subscription to the Worker endpoint
echo "--> Configuring Pub/Sub Push Subscription to '$WORKER_URL/pubsub/push'..."
if ! gcloud pubsub subscriptions describe "$SUBSCRIPTION_NAME" --project="$PROJECT_ID" &>/dev/null; then
  gcloud pubsub subscriptions create "$SUBSCRIPTION_NAME" \
    --topic="$TOPIC_NAME" \
    --push-endpoint="$WORKER_URL/pubsub/push" \
    --push-auth-service-account="autowork-api-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --ack-deadline=600 \
    --project="$PROJECT_ID"
else
  gcloud pubsub subscriptions update "$SUBSCRIPTION_NAME" \
    --push-endpoint="$WORKER_URL/pubsub/push" \
    --project="$PROJECT_ID"
fi

echo "============================================================"
echo "✓ AutoWork Background Worker successfully deployed & wired!"
echo "Worker URL: $WORKER_URL"
echo "============================================================"
