import os
import time
import vertexai
from vertexai import rag
from vertexai.generative_models import GenerativeModel, Tool

# Default Project ID and Location can be used as fallbacks if not provided directly to functions
FALLBACK_PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "your-gcp-project-id")
FALLBACK_LOCATION = "us-central1"

def _initialize_vertex_ai(project_id: str = None, location: str = None) -> tuple[bool, str | None]:
    """
    Initializes Vertex AI SDK with provided or fallback project and location.
    Returns: (success_boolean, error_message_string_if_any)
    """
    resolved_project_id = project_id or FALLBACK_PROJECT_ID
    resolved_location = location or FALLBACK_LOCATION

    if resolved_project_id == "your-gcp-project-id":
        error_msg = "Vertex AI SDK Initialization failed: Project ID is not configured. Please set GOOGLE_CLOUD_PROJECT or pass project_id."
        print(error_msg)
        return False, error_msg

    try:
        print(f"Attempting Vertex AI initialization with project: {resolved_project_id} and location: {resolved_location}")
        vertexai.init(project=resolved_project_id, location=resolved_location)
        print(f"Vertex AI SDK initialized successfully for project '{resolved_project_id}' and location '{resolved_location}'.")
        return True, None
    except Exception as e:
        error_msg = f"Vertex AI SDK Initialization failed for project '{resolved_project_id}', location '{resolved_location}': {e}"
        print(error_msg)
        return False, error_msg

def import_documents_to_corpus(
    gcs_document_paths: list[str],
    corpus_display_name: str,
    project_id: str = None,
    location: str = None
) -> tuple[bool, str]:
    """
    Imports documents from GCS into a specified RAG corpus. Creates the corpus if it doesn't exist.
    Returns: (success_boolean, message_string)
    """
    success, init_error = _initialize_vertex_ai(project_id, location)
    if not success:
        return False, init_error

    # 1. Find or Create RAG Corpus
    rag_corpus = None
    try:
        print(f"Looking for existing RAG corpus with display name: {corpus_display_name}")
        all_corpora = rag.list_corpora()
        matching_corpora = [c for c in all_corpora if c.display_name == corpus_display_name]
        print(f"Found {len(matching_corpora)} corpora matching display name '{corpus_display_name}' after client-side filtering.")

        if matching_corpora:
            rag_corpus = matching_corpora[0]
            print(f"Found existing RAG corpus: {rag_corpus.name}")
        else:
            print(f"No existing corpus found. Creating a new one: {corpus_display_name}")
            embedding_model_config = rag.RagEmbeddingModelConfig(
                vertex_prediction_endpoint=rag.VertexPredictionEndpoint(
                    publisher_model="publishers/google/models/text-embedding-004"
                )
            )
            rag_corpus = rag.create_corpus(
                display_name=corpus_display_name,
                backend_config=rag.RagVectorDbConfig(rag_embedding_model_config=embedding_model_config),
            )
            print(f"Created new RAG corpus: {rag_corpus.name}")
    except Exception as e_corpus_ops:
        error_msg = f"Error finding or creating RAG corpus '{corpus_display_name}': {e_corpus_ops}"
        print(error_msg)
        return False, error_msg

    if not rag_corpus:
        return False, f"Fatal: RAG corpus '{corpus_display_name}' could not be found or created."

    # 2. Import Files
    if not gcs_document_paths:
        return True, f"No documents provided for import into corpus '{corpus_display_name}'. Corpus is ready."

    print(f"Importing files into corpus {rag_corpus.name}: {gcs_document_paths}")
    try:
        # rag.import_files is expected to be a synchronous call for this SDK version
        # or handles LRO polling transparently if it returns a direct response object.
        import_response = rag.import_files(
            rag_corpus.name,
            gcs_document_paths,
            transformation_config=rag.TransformationConfig(
                chunking_config=rag.ChunkingConfig(chunk_size=512, chunk_overlap=100),
            ),
            max_embedding_requests_per_min=1000,
        )
        print(f"Call to rag.import_files() for corpus '{rag_corpus.name}' completed.")
        print(f"Type of response object from import_files: {type(import_response)}")

        imported_count = 0
        failed_count = 0

        # Attributes might vary based on exact SDK version and response type
        if hasattr(import_response, 'imported_rag_files_count'):
            imported_count = import_response.imported_rag_files_count
        elif hasattr(import_response, 'imported_files_count'): # Older attribute name
             imported_count = import_response.imported_files_count

        if hasattr(import_response, 'failed_rag_files_count'):
            failed_count = import_response.failed_rag_files_count
        elif hasattr(import_response, 'failed_files_count'): # Older attribute name
             failed_count = import_response.failed_files_count

        print(f"Import summary for corpus '{rag_corpus.name}': Imported {imported_count}, Failed {failed_count}")

        if failed_count > 0:
            # Partial success, but flag as error for user to check.
            # More detailed error reasons might be in logs or specific error fields of the response if available.
            return False, f"File import completed with {failed_count} failures for corpus '{corpus_display_name}'. Imported {imported_count} files."

        return True, f"File import process completed for corpus '{corpus_display_name}'. Imported {imported_count} files."

    except Exception as e_import:
        e_import_message = e_import.message if hasattr(e_import, 'message') else str(e_import)
        error_msg = f"Error during file import to corpus '{corpus_display_name}': {e_import_message}. Check GCS permissions, file formats, and Vertex AI service limits. Original error type: {type(e_import).__name__}"
        print(error_msg)
        return False, error_msg


def query_rag_corpus(
    prompt_text: str,
    model_choice: str,
    corpus_display_name: str,
    project_id: str = None,
    location: str = None,
    self_deployed_params: dict = None
) -> tuple[str | None, str | None]:
    """
    Queries an existing RAG corpus with a given prompt and model.
    Returns: (response_text, error_message_string_if_any)
    """
    success, init_error = _initialize_vertex_ai(project_id, location)
    if not success:
        return None, init_error

    # 1. Find RAG Corpus
    rag_corpus = None
    try:
        print(f"Looking for existing RAG corpus with display name: {corpus_display_name}")
        all_corpora = rag.list_corpora()
        matching_corpora = [c for c in all_corpora if c.display_name == corpus_display_name]
        print(f"Found {len(matching_corpora)} corpora matching display name '{corpus_display_name}' after client-side filtering.")

        if matching_corpora:
            rag_corpus = matching_corpora[0]
            print(f"Using existing RAG corpus: {rag_corpus.name}")
        else:
            error_msg = f"Error: RAG corpus '{corpus_display_name}' not found. Please upload and import documents first."
            print(error_msg)
            return None, error_msg
    except Exception as e_corpus_find:
        error_msg = f"Error when trying to find RAG corpus '{corpus_display_name}': {e_corpus_find}"
        print(error_msg)
        return None, error_msg

    # 2. Create RAG Retrieval Tool
    try:
        rag_retrieval_config = rag.RagRetrievalConfig(top_k=3)
        retrieval_obj = rag.Retrieval(
            source=rag.VertexRagStore(
                rag_resources=[rag.RagResource(rag_corpus=rag_corpus.name)],
                rag_retrieval_config=rag_retrieval_config,
            )
        )
        rag_retrieval_tool = Tool.from_retrieval(retrieval=retrieval_obj)
    except Exception as e_tool:
        error_msg = f"Error creating RAG retrieval tool for corpus '{corpus_display_name}': {e_tool}"
        print(error_msg)
        return None, error_msg

    # 3. Instantiate Generative Model
    rag_model = None
    try:
        if model_choice == 'gemini':
            model_name = "gemini-2.0-flash-001"
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
            # Ensure the project_id for the self-deployed endpoint's vertexai.init call is handled
            # if it's different from the main one. _initialize_vertex_ai could be enhanced or called again.
            # For now, assume the initial _initialize_vertex_ai was sufficient or params match.
            # Removed debug print statements that were here.
            rag_model = GenerativeModel(endpoint_str, tools=[rag_retrieval_tool])
        else:
            return None, f"Invalid model_choice: {model_choice}. Must be 'gemini' or 'self-deployed'."
    except Exception as e_model_init:
        error_msg = f"Error instantiating generative model '{model_choice}': {e_model_init}"
        print(error_msg)
        return None, error_msg

    # 4. Generate Content
    print(f"Generating content with prompt: '{prompt_text[:100]}...' using corpus '{corpus_display_name}'")
    try:
        response = rag_model.generate_content(prompt_text)
        generated_text = response.text
        print(f"Successfully generated content. Response: {generated_text[:100]}...")
        return generated_text, None
    except Exception as e_generate:
        error_msg = f"Error during content generation: {e_generate}"
        print(error_msg)
        return None, error_msg


# Example usage (for testing, can be removed or commented out)
if __name__ == '__main__':
    print("Starting RAG Engine refactored test run...")

    # Ensure GOOGLE_CLOUD_PROJECT is set for _initialize_vertex_ai fallback
    if FALLBACK_PROJECT_ID == "your-gcp-project-id":
        print("Error: GOOGLE_CLOUD_PROJECT environment variable not set. Please set it to your GCP project ID for testing.")
        exit(1)

    test_gcs_bucket = os.environ.get("TEST_GCS_BUCKET_NAME")
    if not test_gcs_bucket:
        print("Error: TEST_GCS_BUCKET_NAME environment variable not set. Please set it for testing.")
        exit(1)

    test_corpus_name = "my_test_corpus_for_refactor"
    test_file_name = "test_doc_refactor.txt"
    test_gcs_path = f"gs://{test_gcs_bucket}/rag_test_docs/{test_file_name}"

    print(f"Test setup: Project='{FALLBACK_PROJECT_ID}', Corpus='{test_corpus_name}', File='{test_gcs_path}'")
    print(f"Make sure the test file '{test_file_name}' exists at '{test_gcs_path}'.")
    print("You can create it with: echo 'This is a test document for the refactored RAG engine.' | gsutil cp - " + test_gcs_path)

    # Test 1: Import documents
    print("\n--- Test Case 1: Import Documents ---")
    import_success, import_message = import_documents_to_corpus(
        gcs_document_paths=[test_gcs_path],
        corpus_display_name=test_corpus_name,
        project_id=FALLBACK_PROJECT_ID, # Explicitly pass for clarity in test
        location=FALLBACK_LOCATION
    )
    print(f"Import Status: {import_success}, Message: {import_message}")

    if not import_success:
        print("Halting test due to import failure.")
    else:
        # Test 2: Query the corpus
        print("\n--- Test Case 2: Query Corpus (Gemini) ---")
        test_prompt = "What is this document about?"
        query_response, query_error = query_rag_corpus(
            prompt_text=test_prompt,
            model_choice='gemini',
            corpus_display_name=test_corpus_name,
            project_id=FALLBACK_PROJECT_ID,
            location=FALLBACK_LOCATION
        )
        if query_error:
            print(f"Query Error: {query_error}")
        else:
            print(f"Query Response: {query_response}")

        # Optional: Test with a self-deployed endpoint if configured
        # TEST_SELF_DEPLOYED_PROJECT_ID = os.environ.get("TEST_SELF_DEPLOYED_PROJECT_ID", FALLBACK_PROJECT_ID)
        # TEST_SELF_DEPLOYED_LOCATION = os.environ.get("TEST_SELF_DEPLOYED_LOCATION", FALLBACK_LOCATION)
        # TEST_SELF_DEPLOYED_ENDPOINT_ID = os.environ.get("TEST_SELF_DEPLOYED_ENDPOINT_ID")

        # if TEST_SELF_DEPLOYED_ENDPOINT_ID:
        #     print("\n--- Test Case 3: Query Corpus (Self-Deployed) ---")
        #     sd_params = {
        #         'PROJECT_ID': TEST_SELF_DEPLOYED_PROJECT_ID,
        #         'LOCATION': TEST_SELF_DEPLOYED_LOCATION,
        #         'ENDPOINT_ID': TEST_SELF_DEPLOYED_ENDPOINT_ID
        #     }
        #     sd_response, sd_error = query_rag_corpus(
        #         prompt_text=test_prompt,
        #         model_choice='self-deployed',
        #         corpus_display_name=test_corpus_name,
        #         project_id=FALLBACK_PROJECT_ID, # Main project for SDK init
        #         location=FALLBACK_LOCATION,
        #         self_deployed_params=sd_params
        #     )
        #     if sd_error:
        #         print(f"Self-Deployed Query Error: {sd_error}")
        #     else:
        #         print(f"Self-Deployed Query Response: {sd_response}")
        # else:
        #     print("\nSkipping Self-Deployed query test as TEST_SELF_DEPLOYED_ENDPOINT_ID is not set.")

    print("\nRefactored RAG Engine test run finished.")
