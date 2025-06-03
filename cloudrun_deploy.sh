#!/bin/bash

# Script to automate the deployment of the Vertex AI RAG Demo application to Google Cloud Run.
# Before running, ensure you have:
# 1. Google Cloud SDK (gcloud) installed and configured.
# 2. Authenticated with gcloud (`gcloud auth login` and `gcloud auth application-default login`).
# 3. Docker installed locally (or run this from Cloud Shell).
# 4. The necessary permissions in your GCP project to manage Cloud Build, Cloud Run, IAM, etc.

set -e # Exit immediately if a command exits with a non-zero status.

# ------------------------------------------------------
# USER CONFIGURATION: Please update these variables
# ------------------------------------------------------
PROJECT_ID="your-gcp-project-id"
REGION="us-central1" # e.g., us-central1, europe-west1, etc.
APP_NAME="rag-flask-app" # Name for your Cloud Run service and container image

GCS_BUCKET_NAME="your-gcs-bucket-name-for-rag"
GCS_DESTINATION_FOLDER="rag_uploads/" # Folder within the GCS bucket for uploads

# Generate a strong secret key for production. You can use 'openssl rand -hex 32' to generate one.
FLASK_SECRET_KEY="change-this-to-a-very-strong-and-unique-secret-key"

# Optional: Specify a custom service account for Cloud Run.
# If empty, the script will use the default Compute Engine service account and grant it permissions.
# Example: CLOUD_RUN_SA_EMAIL="my-custom-sa@${PROJECT_ID}.iam.gserviceaccount.com"
CLOUD_RUN_SA_EMAIL=""
# ------------------------------------------------------

echo "-------------------------------------------------------------------"
echo "Vertex AI RAG Demo - Google Cloud Run Deployment Script"
echo "-------------------------------------------------------------------"
echo ""
echo "Project ID:           ${PROJECT_ID}"
echo "Region:               ${REGION}"
echo "App Name:             ${APP_NAME}"
echo "GCS Bucket:           ${GCS_BUCKET_NAME}"
echo "GCS Dest. Folder:     ${GCS_DESTINATION_FOLDER}"
if [ -n "${CLOUD_RUN_SA_EMAIL}" ]; then
  echo "Cloud Run SA:         ${CLOUD_RUN_SA_EMAIL}"
else
  echo "Cloud Run SA:         Will use default Compute Engine SA and grant permissions."
fi
echo ""

# Verify placeholders have been changed
if [[ "${PROJECT_ID}" == "your-gcp-project-id" ]] || \
   [[ "${GCS_BUCKET_NAME}" == "your-gcs-bucket-name-for-rag" ]] || \
   [[ "${FLASK_SECRET_KEY}" == "change-this-to-a-very-strong-and-unique-secret-key" ]]; then
  echo "ERROR: Please update the placeholder values in the USER CONFIGURATION section of this script."
  exit 1
fi

read -p "Press Enter to continue with the deployment, or Ctrl+C to exit..."

# Step 1: Enable required Google Cloud APIs
echo ""
echo "Step 1: Enabling Google Cloud APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  aiplatform.googleapis.com \
  storage.googleapis.com \
  iam.googleapis.com \
  --project="${PROJECT_ID}"
echo "APIs enabled successfully."
echo ""

# Step 2: Build the Docker image using Google Cloud Build
echo "Step 2: Building Docker image with Google Cloud Build..."
IMAGE_URI="gcr.io/${PROJECT_ID}/${APP_NAME}"
gcloud builds submit --tag "${IMAGE_URI}" --project="${PROJECT_ID}"
echo "Docker image built and pushed successfully: ${IMAGE_URI}"
echo ""

# Step 3: Deploy to Google Cloud Run
echo "Step 3: Deploying to Google Cloud Run..."
ENV_VARS="GOOGLE_CLOUD_PROJECT=${PROJECT_ID}"
ENV_VARS+=",GCS_BUCKET_NAME=${GCS_BUCKET_NAME}"
ENV_VARS+=",GCS_DESTINATION_FOLDER=${GCS_DESTINATION_FOLDER}"
ENV_VARS+=",FLASK_SECRET_KEY=${FLASK_SECRET_KEY}"
ENV_VARS+=",PYTHONUNBUFFERED=True" # Recommended for Python logging in containers

# Add other environment variables as needed by your application, for example:
# ENV_VARS+=",VERTEX_AI_PROJECT_FOR_RAG=${PROJECT_ID}" # If RAG engine needs a specific project

DEPLOY_COMMAND="gcloud run deploy \"${APP_NAME}\" \
  --image \"${IMAGE_URI}\" \
  --platform managed \
  --region \"${REGION}\" \
  --allow-unauthenticated \
  --project=\"${PROJECT_ID}\" \
  --set-env-vars \"${ENV_VARS}\""

if [ -n "${CLOUD_RUN_SA_EMAIL}" ]; then
  DEPLOY_COMMAND+=" --service-account=\"${CLOUD_RUN_SA_EMAIL}\""
fi

echo "Running deployment command:"
echo "${DEPLOY_COMMAND}"
eval "${DEPLOY_COMMAND}" # Using eval to correctly interpret the command string with quotes and variables
SERVICE_URL=$(gcloud run services describe "${APP_NAME}" --platform managed --region "${REGION}" --project "${PROJECT_ID}" --format 'value(status.url)')
echo "Application deployed successfully to Cloud Run."
echo ""

# Step 4: Configure Service Account Permissions
echo "Step 4: Configuring Service Account Permissions..."
if [ -z "${CLOUD_RUN_SA_EMAIL}" ]; then
  echo "Using default Compute Engine service account."
  PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')
  SERVICE_ACCOUNT_TO_PERMISSION="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
else
  echo "Using custom service account: ${CLOUD_RUN_SA_EMAIL}"
  SERVICE_ACCOUNT_TO_PERMISSION="${CLOUD_RUN_SA_EMAIL}"
fi
echo "Service Account to grant permissions: ${SERVICE_ACCOUNT_TO_PERMISSION}"

echo "Granting 'Vertex AI User' role to the service account on project ${PROJECT_ID}..."
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SERVICE_ACCOUNT_TO_PERMISSION}" \
  --role="roles/aiplatform.user" \
  --condition=None # Explicitly set no condition
echo "'Vertex AI User' role granted."

echo "Granting 'Storage Object Admin' role to the service account on bucket gs://${GCS_BUCKET_NAME}..."
gcloud storage buckets add-iam-policy-binding "gs://${GCS_BUCKET_NAME}" \
  --member="serviceAccount:${SERVICE_ACCOUNT_TO_PERMISSION}" \
  --role="roles/storage.objectAdmin" # Consider roles/storage.objectCreator for more restrictive permissions if appropriate
echo "'Storage Object Admin' role granted."
echo ""

# Step 5: Output Deployed URL
echo "Step 5: Deployment Information"
echo "-------------------------------------------------------------------"
echo "Cloud Run Service Name: ${APP_NAME}"
echo "Deployed URL: ${SERVICE_URL}"
echo "Remember to check the Cloud Run service logs in the Google Cloud Console if you encounter any issues."
echo "-------------------------------------------------------------------"
echo "Deployment script finished."

exit 0
