from flask import Flask, request, render_template, flash, redirect, url_for, session
import os
from google.cloud import storage
from werkzeug.utils import secure_filename
import rag_engine # Using placeholder functions for now

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

# --- Configuration ---
# Project ID for GCS operations and default for Vertex AI
PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT', 'your-gcp-project-id')
# Location for Vertex AI services
VERTEX_AI_LOCATION = os.environ.get('VERTEX_AI_LOCATION', 'us-central1')

GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME', 'your-gcs-bucket-name')
GCS_DESTINATION_FOLDER = os.environ.get('GCS_DESTINATION_FOLDER', 'my_files_dir/')

# Global RAG Corpus Display Name
RAG_CORPUS_DISPLAY_NAME = os.environ.get('RAG_CORPUS_DISPLAY_NAME', "my_rag_application_corpus")

storage_client = None
# Initialize storage client only if PROJECT_ID is properly set
if PROJECT_ID and PROJECT_ID != 'your-gcp-project-id':
    try:
        storage_client = storage.Client(project=PROJECT_ID)
        print(f"GCS storage client initialized for project: {PROJECT_ID}")
    except Exception as e:
        print(f"Error initializing GCS client for project {PROJECT_ID}: {e}. GCS operations will likely fail.")
else:
    print("Warning: GOOGLE_CLOUD_PROJECT environment variable is not set to a valid ID. GCS client not initialized.")


@app.route('/')
def index():
    # Retrieve any relevant state from session to repopulate form and display results
    return render_template('index.html',
                           project_id_env=PROJECT_ID,
                           gcs_bucket_env=GCS_BUCKET_NAME,
                           rag_corpus_display_name=RAG_CORPUS_DISPLAY_NAME,
                           vertex_ai_location_env=VERTEX_AI_LOCATION,
                           response_text=session.pop('response_text_value', None), # Use response_text_value
                           model_type_selected=session.get('model_type_selected', 'gemini'),
                           prompt_input_value=session.get('prompt_input_value', ''),
                           sd_project_id=session.get('sd_project_id', ''),
                           sd_location=session.get('sd_location', ''),
                           sd_endpoint_id=session.get('sd_endpoint_id', ''),
                           uploaded_gcs_uri=session.get('uploaded_gcs_uri'))


@app.route('/upload_and_import', methods=['POST'])
def upload_and_import():
    gcs_file_uri = None
    filename = None
    # Persist form selections in session for repopulation on redirect
    session['model_type_selected'] = request.form.get('model_type', session.get('model_type_selected', 'gemini')) # Keep existing if not in this form
    session['prompt_input_value'] = request.form.get('prompt_input', session.get('prompt_input_value', '')) # Keep existing
    session['sd_project_id'] = request.form.get('project_id', session.get('sd_project_id', ''))
    session['sd_location'] = request.form.get('location', session.get('sd_location', ''))
    session['sd_endpoint_id'] = request.form.get('endpoint_id', session.get('sd_endpoint_id', ''))


    if 'file' not in request.files:
        flash('No file part in the request. Please select a file to upload.', 'error')
        return redirect(url_for('index'))

    file = request.files['file']

    if file.filename == '':
        flash('No file selected for upload. Please select a file.', 'error')
        return redirect(url_for('index'))

    if file:
        filename = secure_filename(file.filename)
        destination_blob_name = f"{GCS_DESTINATION_FOLDER}{filename}"

        if not storage_client:
            flash('GCS client not initialized. Is GOOGLE_CLOUD_PROJECT environment variable set correctly?', 'error')
            return redirect(url_for('index'))

        if GCS_BUCKET_NAME == 'your-gcs-bucket-name' or PROJECT_ID == 'your-gcp-project-id':
            flash('GCS_BUCKET_NAME or GOOGLE_CLOUD_PROJECT is not configured correctly. File cannot be uploaded.', 'error')
            return redirect(url_for('index'))

        try:
            bucket = storage_client.bucket(GCS_BUCKET_NAME)
            blob = bucket.blob(destination_blob_name)
            blob.upload_from_file(file.stream, content_type=file.content_type)
            gcs_file_uri = f"gs://{GCS_BUCKET_NAME}/{destination_blob_name}"
            flash(f'File "{filename}" uploaded successfully to GCS: {gcs_file_uri}', 'success')
            print(f"Uploaded {filename} to {gcs_file_uri}")
            session['uploaded_gcs_uri'] = gcs_file_uri # Store in session for display
        except Exception as e:
            flash(f'An error occurred during GCS upload: {e}', 'error')
            print(f"GCS Upload Error: {e}")
            session.pop('uploaded_gcs_uri', None) # Clear if upload failed
            return redirect(url_for('index'))

    if gcs_file_uri:
        try:
            # Ensure PROJECT_ID and VERTEX_AI_LOCATION are valid before calling rag_engine
            if PROJECT_ID == 'your-gcp-project-id':
                flash("GOOGLE_CLOUD_PROJECT is not set. Cannot proceed with RAG import.", "error")
                return redirect(url_for('index'))

            print(f"Calling RAG Engine to import: GCS Path='{gcs_file_uri}', Corpus='{RAG_CORPUS_DISPLAY_NAME}', Project='{PROJECT_ID}', Location='{VERTEX_AI_LOCATION}'")

            success, message = rag_engine.import_documents_to_corpus(
                gcs_document_paths=[gcs_file_uri],
                corpus_display_name=RAG_CORPUS_DISPLAY_NAME,
                project_id=PROJECT_ID,
                location=VERTEX_AI_LOCATION
            )

            if success:
                flash(message, 'success')
            else:
                flash(message, 'error') # Message from rag_engine should be user-friendly
        except Exception as e:
            flash(f"An unexpected error occurred while initiating RAG import: {e}", 'error')
            print(f"RAG Import Call Error: {e}")

    return redirect(url_for('index'))


@app.route('/submit_prompt', methods=['POST'])
def submit_prompt():
    # Store form values in session to repopulate
    session['model_type_selected'] = request.form.get('model_type', 'gemini')
    session['prompt_input_value'] = request.form.get('prompt_input', '')
    session['sd_project_id'] = request.form.get('project_id', '')      # For self-deployed model
    session['sd_location'] = request.form.get('location', '')          # For self-deployed model
    session['sd_endpoint_id'] = request.form.get('endpoint_id', '')    # For self-deployed model
    session['sd_domain_value'] = request.form.get('sd_domain', '').strip() # New dedicated domain field

    model_choice = session['model_type_selected']
    user_prompt = session['prompt_input_value']

    # Clear previous response from session before new query
    session.pop('response_text_value', None)

    self_deployed_params_dict = None
    query_project_id = PROJECT_ID # Default project for Gemini & RAG corpus
    query_location = VERTEX_AI_LOCATION

    if model_choice == 'self-deployed':
        sd_project = session['sd_project_id']
        sd_location = session['sd_location']
        sd_endpoint = session['sd_endpoint_id']
        sd_domain = session['sd_domain_value'] # Retrieve new domain from session

        if not all([sd_project, sd_location, sd_endpoint]): # Domain is optional, not checked here
            flash('Project ID, Location, and Endpoint ID are required for self-deployed models.', 'error')
            return redirect(url_for('index'))

        self_deployed_params_dict = {
            'PROJECT_ID': sd_project,
            'LOCATION': sd_location,
            'ENDPOINT_ID': sd_endpoint,
            'DEDICATED_DOMAIN': sd_domain if sd_domain else None # Add new domain
        }
        # If self-deployed model uses a different project for its endpoint,
        # that's handled by self_deployed_params. query_project_id/location are for corpus.
        flash_msg = f"Querying with Self-Deployed model: Endpoint Project={sd_project}, Location={sd_location}, Endpoint ID={sd_endpoint}"
        if sd_domain:
            flash_msg += f", Domain={sd_domain}"
        flash(flash_msg, "info")
    elif model_choice == 'gemini':
        flash("Querying with Gemini (Vertex AI) model.", "info")
    else:
        flash('Invalid model type selected.', 'error')
        return redirect(url_for('index'))

    if not user_prompt:
        flash('Prompt input is empty. Please enter a prompt.', 'error')
        return redirect(url_for('index'))

    # Ensure PROJECT_ID and VERTEX_AI_LOCATION are valid before calling rag_engine
    if query_project_id == 'your-gcp-project-id':
        flash("GOOGLE_CLOUD_PROJECT is not set. Cannot proceed with RAG query.", "error")
        return redirect(url_for('index'))

    flash(f"Prompt submitted: '{user_prompt[:50]}...'", "info")

    try:
        print(f"Calling RAG Engine to query: Corpus='{RAG_CORPUS_DISPLAY_NAME}', Model='{model_choice}', Prompt='{user_prompt[:30]}...', Project='{query_project_id}', Location='{query_location}'")
        response_text, error_message = rag_engine.query_rag_corpus(
            prompt_text=user_prompt,
            model_choice=model_choice,
            corpus_display_name=RAG_CORPUS_DISPLAY_NAME,
            project_id=query_project_id,
            location=query_location,
            self_deployed_params=self_deployed_params_dict
        )

        if error_message:
            flash(error_message, 'error') # Error message from rag_engine should be user-friendly
            if "corpus" in error_message.lower() and "not found" in error_message.lower():
                flash("RAG Corpus not found. Please upload and import a document using 'Step 1' before submitting a prompt.", 'warning')
            session['response_text_value'] = None # Clear any old successful response
        else:
            flash("RAG query successful!", 'success')
            session['response_text_value'] = response_text

    except Exception as e:
        error_msg_unexpected = f"An unexpected error occurred during RAG query: {e}"
        flash(error_msg_unexpected, 'error')
        print(f"RAG Query Call Exception: {e}")
        session['response_text_value'] = None # Clear on unexpected error too

    return redirect(url_for('index'))

if __name__ == '__main__':
    print(f"Flask App Startup Configuration:")
    print(f"  GOOGLE_CLOUD_PROJECT (for GCS & default Vertex AI): {PROJECT_ID}")
    print(f"  VERTEX_AI_LOCATION (for Vertex AI services): {VERTEX_AI_LOCATION}")
    print(f"  GCS_BUCKET_NAME (for document uploads): {GCS_BUCKET_NAME}")
    print(f"  GCS_DESTINATION_FOLDER (in bucket): {GCS_DESTINATION_FOLDER}")
    print(f"  RAG_CORPUS_DISPLAY_NAME (target corpus): {RAG_CORPUS_DISPLAY_NAME}")

    if PROJECT_ID == 'your-gcp-project-id' or GCS_BUCKET_NAME == 'your-gcs-bucket-name':
        print("\nWARNING: GOOGLE_CLOUD_PROJECT or GCS_BUCKET_NAME are using default placeholder values.")
        print("Ensure these are set correctly as environment variables for the application to function properly.")

    if not storage_client:
         print("\nWARNING: GCS storage client was not initialized. This typically means GOOGLE_CLOUD_PROJECT was not set to a valid ID at startup.")

    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
