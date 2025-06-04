#!/bin/bash

# Script to help with local setup and installation of the Vertex AI RAG Demo application.

echo "-------------------------------------------------------------------"
echo "Vertex AI RAG Demo - Local Installation Helper"
echo "-------------------------------------------------------------------"
echo ""
echo "This script will guide you through the basic setup."
echo "Please ensure you have the following prerequisites installed:"
echo "1. Python (3.8+ recommended)"
echo "2. pip (Python package installer)"
echo "3. virtualenv (Python virtual environment tool - install with 'pip install virtualenv')"
echo "4. Google Cloud SDK (gcloud command-line tool - https://cloud.google.com/sdk/docs/install)"
echo ""
read -p "Press Enter to continue if you have these prerequisites, or Ctrl+C to exit..."

# Step 1: Create a Python virtual environment
echo ""
echo "Step 1: Creating Python virtual environment named 'venv'..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "Error: Failed to create virtual environment. Please ensure Python 3 and virtualenv are correctly installed."
    exit 1
fi
echo "Virtual environment 'venv' created successfully."
echo ""

# Step 2: Activate the virtual environment
echo "Step 2: Activating virtual environment..."
echo "To activate, run: source venv/bin/activate"
echo "For Windows users, in Command Prompt run: .\\venv\\Scripts\\activate"
echo "For Windows users, in PowerShell run: .\\venv\\Scripts\\Activate.ps1"
echo ""
echo "This script will try to activate it now for the current session (Linux/macOS bash)..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "Note: Automatic activation might not work in all shell environments or if not run directly."
    echo "Please activate it manually in your terminal if the prompt hasn't changed."
fi
echo ""


# Step 3: Install dependencies
echo "Step 3: Installing dependencies from requirements.txt..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install dependencies from requirements.txt. Check the file and pip output."
        exit 1
    fi
    echo "Dependencies installed successfully."
else
    echo "Warning: requirements.txt not found. Skipping dependency installation."
fi
echo ""

# Step 4: Authenticate for Google Cloud Services
echo "Step 4: Authenticate for Google Cloud Services..."
echo "This will open a browser window for you to log in."
gcloud auth application-default login
if [ $? -ne 0 ]; then
    echo "Error: 'gcloud auth application-default login' failed. Ensure Google Cloud SDK is installed and configured correctly."
    exit 1
fi
echo "Google Cloud authentication successful."
echo ""

# Step 5: Set Environment Variables
echo "Step 5: Set Required Environment Variables."
echo "The application needs the following environment variables to be set in your shell:"
echo ""
echo "  - GOOGLE_CLOUD_PROJECT: Your Google Cloud Project ID."
echo "    Example: export GOOGLE_CLOUD_PROJECT=\"your-gcp-project-id\""
echo "  - VERTEX_AI_LOCATION: Your Google Cloud region for Vertex AI (e.g., us-central1)."
echo "    Example: export VERTEX_AI_LOCATION=\"us-central1\" (Defaults to us-central1 in the app if not set)"
echo "  - GCS_BUCKET_NAME: Name of your Google Cloud Storage bucket for uploads."
echo "    Example: export GCS_BUCKET_NAME=\"your-unique-gcs-bucket-name\""
echo "  - GCS_DESTINATION_FOLDER: Folder within GCS bucket for uploads (e.g., rag_uploads/)."
echo "    Example: export GCS_DESTINATION_FOLDER=\"rag_uploads/\""
echo "  - FLASK_SECRET_KEY: A secret key for Flask session management (recommended)."
echo "    Example: export FLASK_SECRET_KEY=\"your-very-secret-and-unique-key\""
echo ""
echo "Please set these in your current terminal session or add them to your shell's profile"
echo "(e.g., ~/.bashrc, ~/.zshrc) for them to persist."
echo "For Windows, use 'set VARIABLE_NAME=\"value\"' in Command Prompt or '\$env:VARIABLE_NAME=\"value\"' in PowerShell."
echo ""
echo "IMPORTANT: The application will not function correctly without GOOGLE_CLOUD_PROJECT and GCS_BUCKET_NAME."
echo ""

# Step 6: Run the Flask Application
echo "Step 6: Run the Flask Application."
echo "Once the environment variables are set, you can run the application using:"
echo ""
echo "  python app.py"
echo ""
echo "Then, open your web browser and go to http://127.0.0.1:8080 (or the address shown in the output)."
echo ""
echo "-------------------------------------------------------------------"
echo "Local setup steps are complete."
echo "Remember to activate the virtual environment ('source venv/bin/activate') in any new terminal session."
echo "And ensure your environment variables are set before running 'python app.py'."
echo "-------------------------------------------------------------------"

# Note: This script does not run the Flask app directly to allow users to set env vars first.
# It also cannot permanently set environment variables for the parent shell.

exit 0
