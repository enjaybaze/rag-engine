import os
import time
import vertexai
from vertexai import rag
from vertexai.generative_models import GenerativeModel, Tool

# Default Project ID and Location for vertexai.init()
# These can be overridden by self_deployed_params if provided for that specific model
DEFAULT_PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "your-gcp-project-id")
DEFAULT_LOCATION = "us-central1" # Default location

def perform_rag_generation(
    gcs_document_paths: list[str],
    model_choice: str,  # 'gemini' or 'self-deployed'
    prompt_text: str,
    corpus_display_name: str = "rag_app_corpus", # Default corpus name
    self_deployed_params: dict = None  # Expected keys: 'PROJECT_ID', 'LOCATION', 'ENDPOINT_ID'
) -> str:
    """
    Performs Retrieval Augmented Generation using Vertex AI.

    Args:
        gcs_document_paths: List of GCS URIs for documents to import into the RAG corpus.
        model_choice: 'gemini' or 'self-deployed'.
        prompt_text: The user prompt for generation.
        corpus_display_name: Display name for the RAG corpus.
        self_deployed_params: Dictionary with 'PROJECT_ID', 'LOCATION', 'ENDPOINT_ID'
                              if model_choice is 'self-deployed'.

    Returns:
        The generated text response from the model.
    """
    print(f"Initializing Vertex AI for project: {DEFAULT_PROJECT_ID} and location: {DEFAULT_LOCATION}")
    try:
        # Attempt to initialize with default project and location
        # This might have already been called if other Vertex AI services are used elsewhere in the app
        # but calling it here ensures it's done before RAG operations if this module is used standalone.
        # A more sophisticated app might manage vertexai.init() globally.
        print(f"Attempting Vertex AI initialization with project: {DEFAULT_PROJECT_ID} and location: {DEFAULT_LOCATION}")
        vertexai.init(project=DEFAULT_PROJECT_ID, location=DEFAULT_LOCATION)
        print("Vertex AI SDK initialized with default project and location.")
    except Exception as e_init_default:
        print(f"Warning: Default Vertex AI SDK initialization failed: {e_init_default}")
        # If self-deployed params are provided, try initializing with them as they might be more specific/correct
        if model_choice == 'self-deployed' and self_deployed_params and \
           self_deployed_params.get('PROJECT_ID') and self_deployed_params.get('LOCATION'):
            try:
                print(f"Attempting Vertex AI initialization with self-deployed params: Project={self_deployed_params['PROJECT_ID']}, Location={self_deployed_params['LOCATION']}")
                vertexai.init(project=self_deployed_params['PROJECT_ID'], location=self_deployed_params['LOCATION'])
                print("Vertex AI SDK initialized with self-deployed parameters.")
            except Exception as e_init_sd:
                error_msg = f"Vertex AI SDK Initialization failed for both default and self-deployed params. Default error: {e_init_default}. Self-deployed error: {e_init_sd}. Ensure GOOGLE_CLOUD_PROJECT is set or provide valid project/location."
                print(error_msg)
                return None, error_msg
        else:
            # If not using self-deployed or params are insufficient for init, the default init error is critical.
            error_msg = f"Vertex AI SDK Initialization failed with default settings: {e_init_default}. Ensure GOOGLE_CLOUD_PROJECT is set."
            print(error_msg)
            return None, error_msg

    # 1. Create or Re-use RAG Corpus
    # For simplicity, this example tries to find an existing corpus or creates a new one.
    # A more robust app might manage corpus lifecycle (creation, deletion, updates) more explicitly.

    # Check for existing corpuses
    print(f"Looking for existing RAG corpus with display name: {corpus_display_name}")
    # List all corpora and filter client-side for compatibility with older SDK versions.
    # For more efficient server-side filtering, consider upgrading google-cloud-aiplatform.
    print("Listing all available RAG corpora (client-side filtering will be applied)...")
    all_corpora = rag.list_corpora()
    rag_corpora = [corpus for corpus in all_corpora if corpus.display_name == corpus_display_name]
    print(f"Found {len(rag_corpora)} corpora matching display name '{corpus_display_name}' after client-side filtering.")

    rag_corpus = None
    if rag_corpora:
        rag_corpus = rag_corpora[0]
        print(f"Found existing RAG corpus: {rag_corpus.name}")
    else:
        print(f"No existing corpus found. Creating a new one: {corpus_display_name}")
        # Configure embedding model
        embedding_model_config = rag.RagEmbeddingModelConfig(
            vertex_prediction_endpoint=rag.VertexPredictionEndpoint(
                publisher_model="publishers/google/models/text-embedding-004" # text-embedding-004 is a common choice
            )
        )
        # Outer try removed here. The 'try' below is for the rag.create_corpus call.
        try:
            rag_corpus = rag.create_corpus(
                display_name=corpus_display_name,
                backend_config=rag.RagVectorDbConfig(
                    rag_embedding_model_config=embedding_model_config
                ),
            )
            print(f"Created new RAG corpus: {rag_corpus.name}")
        except Exception as e_create_corpus: # Catching google.api_core.exceptions.GoogleAPIError or similar
            error_msg = f"Error creating RAG corpus '{corpus_display_name}': {e_create_corpus}. This could be due to naming conflicts, permissions, or invalid configuration."
            print(error_msg)
            return None, error_msg

    if not rag_corpus: # This 'if' statement is now correctly positioned relative to the corpus creation logic
        # This case should ideally be caught by the error handling above if creation fails.
        # However, if rag_corpus remains None due to an unexpected path not caught by the try-except, this is a fallback.
        return None, "Fatal: Could not create or find RAG corpus. The corpus object is None after creation attempt."

    # 2. Import Files to the RagCorpus
    if gcs_document_paths:
        print(f"Importing files into corpus {rag_corpus.name}: {gcs_document_paths}")
        try:
            import_op = rag.import_files(
                rag_corpus.name,
                gcs_document_paths,
                transformation_config=rag.TransformationConfig(
                    chunking_config=rag.ChunkingConfig(chunk_size=512, chunk_overlap=100),
                ),
                max_embedding_requests_per_min=1000, # Adjust as needed
            )
            # Assuming rag.import_files() is now synchronous or its LRO handling is managed by the SDK transparently,
            # or we are treating it as a direct response object (e.g., ImportRagFilesResponse).
            print(f"Call to rag.import_files() completed for corpus {rag_corpus.name}.")
            print(f"Type of response object from import_files: {type(import_op)}")

            # Cautiously log attributes that might exist on an ImportRagFilesResponse object
            if hasattr(import_op, 'imported_files_count'): # Note: Attribute name might differ, e.g. imported_rag_files_count
                print(f"Imported files count (from response object): {import_op.imported_files_count}")
            elif hasattr(import_op, 'imported_rag_files_count'):
                 print(f"Imported RAG files count (from response object): {import_op.imported_rag_files_count}")

            if hasattr(import_op, 'failed_files_count'): # Note: Attribute name might differ
                print(f"Failed files count (from response object): {import_op.failed_files_count}")
            elif hasattr(import_op, 'failed_rag_files_count'):
                 print(f"Failed RAG files count (from response object): {import_op.failed_rag_files_count}")

            # If the operation failed and returned a specific error structure within the response object,
            # you might inspect it here. However, typically errors would raise exceptions.
            print(f"File import process for corpus '{rag_corpus.name}' finished processing.")

        except Exception as e_import:
            print(f"Caught exception during file import: {type(e_import)}")
            print(f"Exception details: {e_import}")
            if hasattr(e_import, 'errors'): # For GoogleAPIError
                print(f"Google API Errors: {e_import.errors}")

            e_import_message = e_import.message if hasattr(e_import, 'message') else str(e_import)
            error_msg = f"Error during file import to corpus '{rag_corpus.name}': {e_import_message}. Check GCS permissions, file formats, and Vertex AI service limits. Original error type: {type(e_import).__name__}"
            print(error_msg)
            return None, error_msg
    else:
        print("No GCS document paths provided for import in this call.")

    # 3. Create RAG Retrieval Tool
    rag_retrieval_config = rag.RagRetrievalConfig(top_k=3)
    try:
        retrieval_obj = rag.Retrieval(
            source=rag.VertexRagStore(
                rag_resources=[rag.RagResource(rag_corpus=rag_corpus.name)],
                rag_retrieval_config=rag_retrieval_config,
            )
        )
        rag_retrieval_tool = Tool.from_retrieval(retrieval=retrieval_obj)
    except Exception as e_tool:
        error_msg = f"Error creating RAG retrieval tool: {e_tool}. Ensure corpus exists and is accessible."
        print(error_msg)
        return None, error_msg

    # 4. Instantiate Generative Model
    print(f"Instantiating generative model. Choice: {model_choice}")
    rag_model = None
    try:
        if model_choice == 'gemini':
            model_name = "gemini-1.5-flash-001" # Ensure this model is available
            print(f"Using Gemini model: {model_name}")
            rag_model = GenerativeModel(model_name=model_name, tools=[rag_retrieval_tool])
        elif model_choice == 'self-deployed':
            if not self_deployed_params:
                return None, "Missing self_deployed_params (Project ID, Location, Endpoint ID) for self-deployed model."

            endpoint_str = (
                f"projects/{self_deployed_params['PROJECT_ID']}/locations/"
                f"{self_deployed_params['LOCATION']}/endpoints/{self_deployed_params['ENDPOINT_ID']}"
            )
            print(f"Using self-deployed model endpoint: {endpoint_str}")
            rag_model = GenerativeModel.from_vertex_endpoint(
                endpoint_name=endpoint_str, tools=[rag_retrieval_tool]
            )
        else:
            return None, f"Invalid model_choice: {model_choice}. Must be 'gemini' or 'self-deployed'."
    except Exception as e_model_init:
        error_msg = f"Error instantiating generative model '{model_choice}': {e_model_init}. Check model name/endpoint and permissions."
        print(error_msg)
        return None, error_msg

    # 5. Generate Content
    print(f"Generating content with prompt: '{prompt_text[:100]}...'")
    try:
        response = rag_model.generate_content(prompt_text)
        generated_text = response.text
        print(f"Successfully generated content. Response: {generated_text[:100]}...")
        return generated_text, None # Success: (response_text, None)
    except Exception as e_generate:
        error_msg = f"Error during content generation: {e_generate}. The model might have refused the prompt or an internal error occurred."
        print(error_msg)
        return None, error_msg

# Example of how to call this function (for testing purposes)
if __name__ == '__main__':
    print("Starting RAG Engine test run...")
    # Ensure GOOGLE_CLOUD_PROJECT is set in your environment for this test
    # For example: export GOOGLE_CLOUD_PROJECT="your-actual-gcp-project"

    # Replace with your actual GCS bucket and file path for testing
    # You must upload a file to this GCS path for the test to work.
    test_gcs_bucket = os.environ.get("TEST_GCS_BUCKET_NAME") # e.g., "your-rag-test-bucket"

    if not DEFAULT_PROJECT_ID or DEFAULT_PROJECT_ID == "your-gcp-project-id":
        print("Error: GOOGLE_CLOUD_PROJECT environment variable not set. Please set it to your GCP project ID.")
    elif not test_gcs_bucket:
        print("Error: TEST_GCS_BUCKET_NAME environment variable not set. Please set it to a GCS bucket name for testing.")
    else:
        # Create a dummy test file in GCS for the test to run
        # This part would typically be done manually or via gsutil before running the test
        # For an automated test, you'd use the GCS client library to upload a test file.
        # For now, this assumes a file "test_document.txt" exists in the specified bucket/folder.
        test_file_name = "test_document.txt"
        test_gcs_path = f"gs://{test_gcs_bucket}/rag_test_docs/{test_file_name}"
        print(f"This test expects a file at: {test_gcs_path}")
        print("If it doesn't exist, RAG import might be empty or fail.")
        print("Consider creating it with: echo 'This is a test document for RAG.' | gsutil cp - gs://your-rag-test-bucket/rag_test_docs/test_document.txt")

        test_prompt = "What is RAG and why is it helpful based on the provided document?"

        print(f"\n--- Test Case 1: Gemini Model ---")
        gemini_response_text, gemini_error = perform_rag_generation(
            gcs_document_paths=[test_gcs_path],
            model_choice='gemini',
            prompt_text=test_prompt,
            corpus_display_name="test_corpus_gemini_rag_engine" # Use a distinct name for testing
        )
        if gemini_error:
            print(f"Gemini Model Error:\n{gemini_error}")
        else:
            print(f"\nGemini Model Response:\n{gemini_response_text}")

        # --- Test Case 2: Self-Deployed Model (Optional - requires a deployed endpoint) ---
        # Replace with your actual self-deployed endpoint details if you have one
        # TEST_SELF_DEPLOYED_PROJECT_ID = os.environ.get("TEST_SELF_DEPLOYED_PROJECT_ID", DEFAULT_PROJECT_ID)
        # TEST_SELF_DEPLOYED_LOCATION = os.environ.get("TEST_SELF_DEPLOYED_LOCATION", "us-central1")
        # TEST_SELF_DEPLOYED_ENDPOINT_ID = os.environ.get("TEST_SELF_DEPLOYED_ENDPOINT_ID") # e.g., "1234567890123456789"

        # if TEST_SELF_DEPLOYED_ENDPOINT_ID:
        #     print(f"\n--- Test Case 2: Self-Deployed Model ---")
        #     self_deployed_params_test = {
        #         'PROJECT_ID': TEST_SELF_DEPLOYED_PROJECT_ID,
        #         'LOCATION': TEST_SELF_DEPLOYED_LOCATION,
        #         'ENDPOINT_ID': TEST_SELF_DEPLOYED_ENDPOINT_ID
        #     }
        #     sd_response_text, sd_error = perform_rag_generation(
        #         gcs_document_paths=[test_gcs_path],
        #         model_choice='self-deployed',
        #         prompt_text=test_prompt,
        #         self_deployed_params=self_deployed_params_test,
        #         corpus_display_name="test_corpus_self_deployed_rag_engine" # Distinct name
        #     )
        #     if sd_error:
        #         print(f"Self-Deployed Model Error:\n{sd_error}")
        #     else:
        #         print(f"\nSelf-Deployed Model Response:\n{sd_response_text}")
        # else:
        #     print("\nSkipping Self-Deployed Model test case as TEST_SELF_DEPLOYED_ENDPOINT_ID is not set.")

    print("\nRAG Engine test run finished.")
