# Deployment Instructions

This document provides instructions on how to deploy and run this Vertex AI RAG application.

## Local Deployment Instructions

These instructions will guide you through setting up and running the application on your local machine for development or testing.

### Prerequisites

Before you begin, ensure you have the following installed:

*   **Python**: Version 3.8 or higher is recommended (as used by the development environment for `google-cloud-aiplatform` and `vertexai` libraries).
*   **pip**: The Python package installer (usually comes with Python).
*   **virtualenv**: Recommended for creating isolated Python environments. You can install it using `pip install virtualenv`.
*   **Google Cloud SDK**: Installed and initialized. This provides the `gcloud` command-line tool needed for authentication. You can download it from [here](https://cloud.google.com/sdk/docs/install).

### Setup Steps

1.  **Clone the Repository**:
    If you haven't already, clone the repository to your local machine:
    ```bash
    git clone <your-repository-url>
    cd <project-directory-name>
    ```

2.  **Create and Activate a Virtual Environment**:
    It's highly recommended to use a virtual environment to manage project dependencies.
    ```bash
    python3 -m venv venv
    ```
    Activate the virtual environment:
    *   On macOS and Linux:
        ```bash
        source venv/bin/activate
        ```
    *   On Windows:
        ```bash
        .\venv\Scripts\activate
        ```
    Your command prompt should change to indicate you are now in the virtual environment.

3.  **Install Dependencies**:
    Install all the required Python packages listed in the `requirements.txt` file:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Authenticate for Google Cloud Services**:
    To allow the application to access Google Cloud Storage (GCS) and Vertex AI services from your local machine, you need to authenticate using Application Default Credentials (ADC):
    ```bash
    gcloud auth application-default login
    ```
    This command will open a browser window for you to log in with your Google account that has permissions for the target GCP project and services.

5.  **Set Environment Variables**:
    The application requires several environment variables to be set to function correctly.

    *   `GOOGLE_CLOUD_PROJECT`: Your Google Cloud Project ID where Vertex AI services will be used and (potentially) where the GCS bucket resides.
    *   `VERTEX_AI_LOCATION`: The Google Cloud region for Vertex AI services (e.g., `us-central1`). The application defaults to `us-central1` if this is not set, but explicitly setting it is good practice.
    *   `GCS_BUCKET_NAME`: The name of the Google Cloud Storage bucket that the application will use to upload documents for the RAG corpus. **You must create this bucket manually in your GCP project if it doesn't exist.**
    *   `GCS_DESTINATION_FOLDER`: The folder path within your GCS bucket where uploaded files will be stored (e.g., `rag_uploads/`). The `app.py` uses `my_files_dir/` as a default if this is not set, but explicitly setting it is recommended.
    *   `FLASK_SECRET_KEY`: (Optional for local, but recommended) A secret key for Flask session management. `app.py` generates one using `os.urandom(24)` if not set, which is fine for local ephemeral use. For any shared or persistent deployment, you should set a strong, unique key.

    **How to set environment variables:**

    *   On macOS and Linux (bash/zsh):
        ```bash
        export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
        export VERTEX_AI_LOCATION="us-central1" # Or your preferred region
        export GCS_BUCKET_NAME="your-unique-gcs-bucket-name"
        export GCS_DESTINATION_FOLDER="rag_uploads/"
        # export FLASK_SECRET_KEY="your-very-secret-flask-key" # Optional for local
        ```
        To make these permanent for your current shell session, you can add them to your shell's profile file (e.g., `~/.bashrc`, `~/.zshrc`).

    *   On Windows (Command Prompt):
        ```cmd
        set GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
        set VERTEX_AI_LOCATION="us-central1"
        set GCS_BUCKET_NAME="your-unique-gcs-bucket-name"
        set GCS_DESTINATION_FOLDER="rag_uploads/"
        REM set FLASK_SECRET_KEY="your-very-secret-flask-key" # Optional for local
        ```
    *   On Windows (PowerShell):
        ```powershell
        $env:GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
        $env:VERTEX_AI_LOCATION="us-central1"
        $env:GCS_BUCKET_NAME="your-unique-gcs-bucket-name"
        $env:GCS_DESTINATION_FOLDER="rag_uploads/"
        # $env:FLASK_SECRET_KEY="your-very-secret-flask-key" # Optional for local
        ```
    Replace placeholder values with your actual project ID and bucket name.

6.  **Run the Flask Application**:
    Once the dependencies are installed and environment variables are set, you can run the Flask development server:
    ```bash
    python app.py
    ```
    (The `app.py` is configured to run on `0.0.0.0:8080` in debug mode).

7.  **Access the Application**:
    Open your web browser and navigate to:
    ```
    http://127.0.0.1:8080
    ```
    You should see the Vertex AI RAG Engine interface.

### Using the `local_install.sh` script (Recommended for Linux/macOS)

For convenience, a shell script `local_install.sh` is provided to automate many of the setup steps above on Linux and macOS systems.

1.  **Make the script executable**:
    ```bash
    chmod +x local_install.sh
    ```
2.  **Review the script (Optional but Recommended)**:
    Open `local_install.sh` in a text editor to understand the commands it will run.
3.  **Run the script**:
    ```bash
    ./local_install.sh
    ```
The script will guide you through creating a virtual environment, installing dependencies, and remind you to set necessary environment variables and run `gcloud auth application-default login`. It does not set environment variables globally or run the Flask app directly, allowing you to do so in your current shell session.

## Google Cloud Run Deployment Instructions

This section describes how to deploy the application to Google Cloud Run, a serverless platform.

**Note**: A shell script `cloudrun_deploy.sh` is provided to automate the Cloud Build and Cloud Run deployment steps. If using the script, ensure you first make it executable (`chmod +x cloudrun_deploy.sh`) and **edit the user configuration variables at the top of the script** (`PROJECT_ID`, `REGION`, `APP_NAME`, `GCS_BUCKET_NAME`, etc.) before running it with `./cloudrun_deploy.sh`. The manual steps below are what the script automates.

### Prerequisites for Cloud Run Deployment

*   **Google Cloud Project**: A Google Cloud Project with Billing enabled.
*   **`gcloud` CLI**: The Google Cloud SDK (gcloud CLI) installed, configured, and authenticated with an account that has permissions to manage Cloud Run, Cloud Build, IAM, Vertex AI, and Cloud Storage in your project.
*   **Required Google Cloud APIs Enabled**: Ensure the following APIs are enabled in your project:
    *   Cloud Run API (`run.googleapis.com`)
    *   Cloud Build API (`cloudbuild.googleapis.com`)
    *   Vertex AI API (`aiplatform.googleapis.com`)
    *   Cloud Storage API (`storage.googleapis.com`)
    *   Identity and Access Management (IAM) API (`iam.googleapis.com`)
    You can enable them with the following command:
    ```bash
    gcloud services enable run.googleapis.com cloudbuild.googleapis.com aiplatform.googleapis.com storage.googleapis.com iam.googleapis.com
    ```
*   **Docker**: Docker installed locally if you are building the container image locally. If you are using Google Cloud Shell, Docker is pre-installed.

### Deployment Steps

1.  **Ensure `app.py` is Cloud Run Ready**:
    The Flask development server (`app.run()`) is not suitable for production. The application should be served by a production-grade WSGI server like Gunicorn.
    *   The `app.py` in this repository is structured with `if __name__ == '__main__': app.run(...)`, which means Gunicorn can directly import the `app` object.
    *   The provided `Dockerfile` uses Gunicorn.

2.  **Containerize the Application (Create `Dockerfile`)**:
    A `Dockerfile` is required to package your application into a container image. A `Dockerfile` has been provided in the root of this repository. It:
    *   Uses an official Python base image.
    *   Installs `gunicorn` and other dependencies from `requirements.txt`.
    *   Copies the application code into the container.
    *   Sets the command to run the application using Gunicorn, binding to the port specified by the `PORT` environment variable (which Cloud Run provides).

3.  **Add Gunicorn to `requirements.txt`**:
    Ensure `gunicorn` is listed in your `requirements.txt` file. If not, add the line:
    ```
    gunicorn>=20.0.0
    ```
    (This step should already be complete for this repository).

4.  **Build the Docker Image using Google Cloud Build**:
    Use Google Cloud Build to build your Docker image and push it to Google Container Registry (gcr.io) or Artifact Registry.
    Replace `YOUR_PROJECT_ID` with your actual Google Cloud Project ID.
    ```bash
    gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/rag-flask-app
    ```
    This command builds the image using the `Dockerfile` in the current directory and tags it with a name that includes your project ID.

5.  **Deploy to Google Cloud Run**:
    Deploy the container image to Cloud Run. Replace placeholders like `YOUR_PROJECT_ID`, `YOUR_REGION`, `your-gcs-bucket-name`, `your-gcs-folder`, and `your-flask-secret-key` with your actual values.

    ```bash
    gcloud run deploy rag-flask-app \
      --image gcr.io/YOUR_PROJECT_ID/rag-flask-app \
      --platform managed \
      --region YOUR_REGION \
      --allow-unauthenticated \
      --set-env-vars GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID" \
      --set-env-vars VERTEX_AI_LOCATION="YOUR_REGION" \
      --set-env-vars GCS_BUCKET_NAME="your-gcs-bucket-name" \
      --set-env-vars GCS_DESTINATION_FOLDER="your-gcs-folder" \
      --set-env-vars FLASK_SECRET_KEY="your-very-strong-and-unique-secret-key-for-production" \
      --set-env-vars PYTHONUNBUFFERED="True" \
      --set-env-vars RAG_CORPUS_DISPLAY_NAME="your-corpus-name" # Optional: if you want to override the app's default
      # Add any other environment variables required by rag_engine.py for Vertex AI.
    ```
    *   `--image`: Specifies the image you just built.
    *   `--platform managed`: Uses the fully managed Cloud Run platform.
    *   `--region YOUR_REGION`: Choose a region where Cloud Run and Vertex AI are available (e.g., `us-central1`, `europe-west1`).
    *   `--allow-unauthenticated`: Makes the service publicly accessible. For restricted access, you'll need to configure IAM or other authentication methods.
    *   `--set-env-vars`: Sets the necessary environment variables for the application. **Ensure these are correctly set for your environment.** `FLASK_SECRET_KEY` should be a strong, unique value for production.

6.  **Service Account Permissions**:
    Cloud Run services execute with the permissions of a service account. By default, this is the project's "Compute Engine default service account" (`PROJECT_NUMBER-compute@developer.gserviceaccount.com`). This service account needs appropriate IAM permissions to access Vertex AI and Google Cloud Storage.

    *   **Vertex AI**: The service account needs permissions to interact with Vertex AI RAG services (e.g., create/read corpora, import files, make predictions). The "Vertex AI User" role (`roles/aiplatform.user`) is often sufficient for this.
    *   **Google Cloud Storage**: The service account needs permissions to read from and write to the GCS bucket specified by `GCS_BUCKET_NAME`. The "Storage Object Admin" (`roles/storage.objectAdmin`) or "Storage Object Creator" (`roles/storage.objectCreator`) role on the specific bucket is required.

    **To grant permissions to the default Compute Engine service account:**

    First, get your Project Number:
    ```bash
    PROJECT_ID="YOUR_PROJECT_ID" # Set your Project ID here
    PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
    CLOUD_RUN_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
    ```

    Grant Vertex AI User role:
    ```bash
    gcloud projects add-iam-policy-binding $PROJECT_ID \
      --member="serviceAccount:${CLOUD_RUN_SA}" \
      --role="roles/aiplatform.user"
    ```

    Grant Storage Object Admin role on your specific GCS bucket:
    ```bash
    GCS_BUCKET="your-gcs-bucket-name" # Set your GCS bucket name here
    gcloud storage buckets add-iam-policy-binding gs://${GCS_BUCKET} \
      --member="serviceAccount:${CLOUD_RUN_SA}" \
      --role="roles/storage.objectAdmin"
    ```
    (Replace `YOUR_PROJECT_ID` and `your-gcs-bucket-name` with your actual values.)

    If you use a custom service account for Cloud Run (specified with the `--service-account` flag during deployment), grant these permissions to your custom service account instead.

7.  **Accessing the Deployed Application**:
    After successful deployment, the `gcloud run deploy` command will output the URL of your deployed service. You can use this URL to access your application.

    The RAG processes, especially file import and initial corpus creation, can be time-consuming. Cloud Run services have a request timeout (default is 5 minutes, configurable up to 60 minutes for HTTP requests). For long-running RAG operations initiated by a user request, consider:
    *   Increasing the Cloud Run service request timeout if appropriate (via the `--timeout` flag in `gcloud run deploy` or in the Cloud Console). The Dockerfile CMD for Gunicorn uses `--timeout 0` (infinite for the worker), but Cloud Run's service-level timeout will still apply and terminate the request if it exceeds the service's configured timeout.
    *   Implementing asynchronous processing using background tasks (e.g., Cloud Tasks, Pub/Sub with a separate worker service) for operations like `rag.import_files` if they frequently exceed reasonable request timeouts. The current implementation is synchronous and processes RAG operations within the HTTP request lifecycle.

## Troubleshooting / Common Issues

*   **IAM Permissions Errors**:
    *   If you see errors related to "permission denied", ensure the service account used by your local environment (ADC) or Cloud Run has the correct IAM roles (`Vertex AI User`, `Storage Object Admin`/`Creator`) as detailed in the setup instructions for each deployment type.
    *   Double-check that permissions are granted on the correct project and/or GCS bucket.

*   **Environment Variables Not Set**:
    *   The application heavily relies on environment variables (`GOOGLE_CLOUD_PROJECT`, `GCS_BUCKET_NAME`, etc.). If these are not set correctly, the application may fail to start or operate properly. Verify they are set in your local shell or in the Cloud Run service configuration.
    *   `app.py` includes print statements on startup indicating if `PROJECT_ID` or `GCS_BUCKET_NAME` appear to be using default placeholder values, which is a common sign they are not set.

*   **File Upload Failures (GCS)**:
    *   Ensure the `GCS_BUCKET_NAME` exists and is correctly spelled.
    *   Check IAM permissions for GCS bucket access.
    *   If uploading large files, you might encounter timeouts depending on your connection speed or client-side limitations (though the backend is designed to handle streams).

*   **RAG Engine Errors in `rag_engine.py`**:
    *   The `rag_engine.py` script itself has error handling. Messages from this engine will typically be prefixed with "Error from RAG Engine:" or "RAG Engine processing failed:" in the UI. These can indicate issues with corpus creation, file import (e.g., unsupported file types by Vertex RAG, GCS path issues), or model generation.
    *   Check the application logs (console for local, Cloud Logging for Cloud Run) for more detailed error messages from `rag_engine.py`.

*   **Cloud Run Request Timeouts**:
    *   As mentioned, RAG file import can be slow. If requests to your Cloud Run service are timing out during processing, you may need to increase the Cloud Run service's request timeout setting or re-architect for asynchronous processing for the import step.

*   **Dockerfile or Cloud Build Issues**:
    *   If `gcloud builds submit` fails, check the build logs in Google Cloud Build for errors. Common issues include syntax errors in the `Dockerfile`, missing dependencies, or network issues during package installation.

*   **Self-Deployed Endpoint Issues**:
    *   If using the "Self-Deployed (Vertex AI Endpoint)" option, ensure the Project ID, Location, and Endpoint ID are correct and that the endpoint is active and accessible by the service account.

**(Further sections on advanced Cloud Run configurations or other deployment methods can be added below.)**
