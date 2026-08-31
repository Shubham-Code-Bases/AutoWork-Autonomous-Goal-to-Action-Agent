#!/usr/bin/env bash
# Copyright 2026 AutoWork Authors
#
# Sets up Google Cloud resources: APIs, Firestore, Pub/Sub topic & subscription, and IAM.

set -euo pipefail

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project)}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
TOPIC_NAME="${PUBSUB_TOPIC:-autowork-executions}"
SUBSCRIPTION_NAME="${PUBSUB_SUBSCRIPTION:-autowork-worker-subscription}"

echo "============================================================"
echo "Initializing Google Cloud Infrastructure for AutoWork"
echo "Project: $PROJECT_ID | Region: $REGION"
echo "============================================================"

# 1. Enable Required Google Cloud APIs
echo "--> Enabling required APIs..."
gcloud services enable \
  run.googleapis.com \
  pubsub.googleapis.com \
  firestore.googleapis.com \
  aiplatform.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  logging.googleapis.com \
  --project="$PROJECT_ID"

# 2. Create Artifact Registry repository if not present
echo "--> Setting up Artifact Registry..."
if ! gcloud artifacts repositories describe autowork-repo --location="$REGION" --project="$PROJECT_ID" &>/dev/null; then
  gcloud artifacts repositories create autowork-repo \
    --repository-format=docker \
    --location="$REGION" \
    --description="AutoWork container repository" \
    --project="$PROJECT_ID"
fi

# 3. Create Firestore Database (Default Native Mode)
echo "--> Setting up Cloud Firestore..."
if ! gcloud firestore databases describe --project="$PROJECT_ID" &>/dev/null; then
  gcloud firestore databases create \
    --location="$REGION" \
    --type=firestore-native \
    --project="$PROJECT_ID"
fi

# 4. Create Pub/Sub Topic
echo "--> Setting up Pub/Sub Topic '$TOPIC_NAME'..."
if ! gcloud pubsub topics describe "$TOPIC_NAME" --project="$PROJECT_ID" &>/dev/null; then
  gcloud pubsub topics create "$TOPIC_NAME" --project="$PROJECT_ID"
fi

# 5. Create Dedicated Service Accounts
echo "--> Configuring IAM Service Accounts..."
for SA_NAME in "autowork-api-sa" "autowork-worker-sa"; do
  if ! gcloud iam service-accounts describe "${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" --project="$PROJECT_ID" &>/dev/null; then
    gcloud iam service-accounts create "$SA_NAME" \
      --display-name="AutoWork Service Account ($SA_NAME)" \
      --project="$PROJECT_ID"
  fi
done

# 6. Assign Minimum Required IAM Permissions
echo "--> Assigning IAM Roles..."
# API Service Account
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:autowork-api-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/pubsub.publisher" >/dev/null

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:autowork-api-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/datastore.user" >/dev/null

# Worker Service Account
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:autowork-worker-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/datastore.user" >/dev/null

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:autowork-worker-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user" >/dev/null

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:autowork-worker-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/logging.logWriter" >/dev/null

echo "============================================================"
echo "✓ Google Cloud infrastructure successfully configured!"
echo "============================================================"
