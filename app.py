from flask import Flask, request, render_template, flash, redirect, url_for
import os
from google.cloud import storage
from werkzeug.utils import secure_filename # For added security with filenames
from rag_engine import perform_rag_generation # Import the RAG engine function

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24)) # Important for flash messages, use a default if not set

# --- Configuration ---
# Google Cloud Project ID - Set this as an environment variable or hardcode
PROJECT_ID = os.environ.get('PROJECT_ID', 'your-gcp-project-id')
# Google Cloud Storage Bucket Name - Set this as an environment variable or hardcode
GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME', 'your-gcs-bucket-name')
# Destination folder within the GCS bucket
GCS_DESTINATION_FOLDER = 'my_files_dir/'

# Ensure the upload folder exists (for temporary local storage if needed, though not used in direct GCS upload)
# UPLOAD_FOLDER = 'uploads'
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Initialize Google Cloud Storage Client ---
# The client will use Application Default Credentials by default.
# Ensure you have authenticated by running:
# `gcloud auth application-default login`
# Or set the GOOGLE_APPLICATION_CREDENTIALS environment variable:
# `export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/keyfile.json"`
storage_client = storage.Client(project=PROJECT_ID)

@app.route('/')
def index():
    return render_template('index.html',
                           project_id_env=PROJECT_ID,
                           gcs_bucket_env=GCS_BUCKET_NAME,
                           response_text=None,
                           model_type_selected='gemini', # Default selection
                           prompt_input_value='')

@app.route('/process', methods=['POST'])
def process_request():
    gcs_file_uri = None
    actual_response_text = None
    form_repopulate_values = {
        "model_type_selected": request.form.get('model_type', 'gemini'),
        "prompt_input_value": request.form.get('prompt_input', ''),
        "sd_project_id": request.form.get('project_id', ''),
        "sd_location": request.form.get('location', ''),
        "sd_endpoint_id": request.form.get('endpoint_id', '')
    }

    # --- 1. File Upload Logic ---
    if 'file' not in request.files:
        flash('No file part in the request. Please select a file to upload.', 'error')
        return render_template('index.html', project_id_env=PROJECT_ID, gcs_bucket_env=GCS_BUCKET_NAME, **form_repopulate_values)

    file = request.files['file']

    if file.filename == '':
        flash('No file selected for upload. Please select a file.', 'error')
        return render_template('index.html', project_id_env=PROJECT_ID, gcs_bucket_env=GCS_BUCKET_NAME, **form_repopulate_values)

    if file:
        filename = secure_filename(file.filename)
        destination_blob_name = f"{GCS_DESTINATION_FOLDER}{filename}"

        try:
            # Check if GCS bucket and project are configured
            if GCS_BUCKET_NAME == 'your-gcs-bucket-name' or PROJECT_ID == 'your-gcp-project-id':
                flash('GCS_BUCKET_NAME or PROJECT_ID is not configured in the application. File cannot be uploaded.', 'error')
                return render_template('index.html', project_id_env=PROJECT_ID, gcs_bucket_env=GCS_BUCKET_NAME, **form_repopulate_values)

            bucket = storage_client.bucket(GCS_BUCKET_NAME)
            blob = bucket.blob(destination_blob_name)
            blob.upload_from_file(file.stream, content_type=file.content_type)
            gcs_file_uri = f"gs://{GCS_BUCKET_NAME}/{destination_blob_name}"
            flash(f'File "{filename}" uploaded successfully to GCS: {gcs_file_uri}', 'success')
            print(f"Uploaded {filename} to {gcs_file_uri}")
        except Exception as e:
            flash(f'An error occurred during GCS upload: {e}', 'error')
            print(f"GCS Upload Error: {e}")
            return render_template('index.html', project_id_env=PROJECT_ID, gcs_bucket_env=GCS_BUCKET_NAME, **form_repopulate_values)
    else: # Should not happen if checks above are done, but as a safeguard
        flash('File object was not available after checks.', 'error')
        return render_template('index.html', project_id_env=PROJECT_ID, gcs_bucket_env=GCS_BUCKET_NAME, **form_repopulate_values)

    # --- 2. Model Selection & Parameter Preparation ---
    model_choice = request.form.get('model_type')
    form_repopulate_values["model_type_selected"] = model_choice

    self_deployed_params_dict = None
    if model_choice == 'self-deployed':
        rag_project_id = request.form.get('project_id')
        rag_location = request.form.get('location')
        rag_endpoint_id = request.form.get('endpoint_id')

        form_repopulate_values["sd_project_id"] = rag_project_id
        form_repopulate_values["sd_location"] = rag_location
        form_repopulate_values["sd_endpoint_id"] = rag_endpoint_id

        if not all([rag_project_id, rag_location, rag_endpoint_id]):
            flash('Project ID, Location, and Endpoint ID are required for self-deployed models.', 'error')
            return render_template('index.html', project_id_env=PROJECT_ID, gcs_bucket_env=GCS_BUCKET_NAME, response_text=None, **form_repopulate_values)

        self_deployed_params_dict = {
            'PROJECT_ID': rag_project_id,
            'LOCATION': rag_location,
            'ENDPOINT_ID': rag_endpoint_id
        }
        flash(f"Using Self-Deployed model: Project ID={rag_project_id}, Location={rag_location}, Endpoint ID={rag_endpoint_id}", "info")

    elif model_choice == 'gemini':
        flash("Using Gemini (Vertex AI) model.", "info")
    else:
        flash('Invalid model type selected.', 'error')
        return render_template('index.html', project_id_env=PROJECT_ID, gcs_bucket_env=GCS_BUCKET_NAME, response_text=None, **form_repopulate_values)

    # --- 3. Prompt Input ---
    user_prompt = request.form.get('prompt_input')
    form_repopulate_values["prompt_input_value"] = user_prompt
    if not user_prompt:
        flash('Prompt input is empty. Please enter a prompt.', 'error') # Changed to error as prompt is essential for RAG
        return render_template('index.html', project_id_env=PROJECT_ID, gcs_bucket_env=GCS_BUCKET_NAME, response_text=None, **form_repopulate_values)

    flash(f"Prompt received: '{user_prompt[:50]}...'", "info")

    # --- 4. Call RAG Engine ---
    if not gcs_file_uri: # Should have been set if file upload succeeded
        flash('GCS file URI is missing, cannot proceed with RAG.', 'error')
        return render_template('index.html', project_id_env=PROJECT_ID, gcs_bucket_env=GCS_BUCKET_NAME, response_text=None, **form_repopulate_values)

    corpus_name = f"rag_corpus_{os.path.splitext(filename)[0]}" # Create a somewhat unique corpus name based on filename

    try:
        print(f"Calling RAG Engine with: GCS Paths=['{gcs_file_uri}'], Model='{model_choice}', Prompt='{user_prompt[:30]}...'")
        response_text, error_message = perform_rag_generation(
            gcs_document_paths=[gcs_file_uri], # Pass as a list
            model_choice=model_choice,
            prompt_text=user_prompt,
            corpus_display_name=corpus_name, # Using the filename-based corpus name
            self_deployed_params=self_deployed_params_dict
        )

        if error_message:
            flash(f"RAG Engine processing failed: {error_message}", 'error')
            actual_response_text = f"Error from RAG Engine: {error_message}" # Display in response area as well
            print(f"RAG Engine returned error: {error_message}")
        else:
            flash("RAG Engine processing successful!", 'success')
            actual_response_text = response_text
            print("RAG Engine returned success.")

    except Exception as e: # Catch any unexpected errors from the call itself
        error_msg_unexpected = f"An unexpected error occurred while calling the RAG engine: {e}"
        flash(error_msg_unexpected, 'error')
        print(f"RAG Engine Call Exception: {e}")
        actual_response_text = error_msg_unexpected # Display error in response area

    # --- 5. Render page with response ---
    return render_template('index.html',
                           project_id_env=PROJECT_ID,
                           gcs_bucket_env=GCS_BUCKET_NAME,
                           response_text=actual_response_text, # This will now show errors too if they occurred
                           **form_repopulate_values)

if __name__ == '__main__':
    # For local development, ensure PROJECT_ID and GCS_BUCKET_NAME are set.
    # If running in an environment where these are not set, the app might not function correctly.
    print(f"Attempting to use PROJECT_ID: {PROJECT_ID}")
    print(f"Attempting to use GCS_BUCKET_NAME: {GCS_BUCKET_NAME}")
    if PROJECT_ID == 'your-gcp-project-id' or GCS_BUCKET_NAME == 'your-gcs-bucket-name':
        print("WARNING: PROJECT_ID or GCS_BUCKET_NAME are not set. GCS operations will likely fail.")
        print("Please set them as environment variables or update the script.")
    app.run(debug=True, host='0.0.0.0', port=8080)
