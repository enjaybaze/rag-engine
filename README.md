# Vertex AI RAG Python Script Demo

This repository contains a Python script that demonstrates how to use the Vertex AI RAG (Retrieval Augmented Generation) service.

## Script Functionality: `rag-engine-vanilla.py`

This script demonstrates the core functionalities of the Vertex AI RAG service. It performs the following steps:

1.  **Initialization**: Initializes the Vertex AI API with the specified project ID and location.
2.  **Create RAG Corpus**: Creates a new RAG corpus with a display name. It configures the embedding model to be used (e.g., "text-embedding-005").
3.  **Import Files**: Imports files into the created RAG corpus. The script supports Google Cloud Storage and Google Drive links. It also allows for optional configuration of chunking size and overlap for processing the documents.
4.  **Direct Context Retrieval**: Performs a direct retrieval query against the RAG corpus. It retrieves the top K relevant chunks based on the input text and an optional vector distance threshold.
5.  **Enhance Generation with RAG Retrieval Tool**:
    *   Creates a RAG retrieval tool using the corpus.
    *   Initializes a Generative Model (e.g., "gemini-2.0-flash-001") and equips it with the RAG retrieval tool.
    *   Generates a response to a query, where the model's response is augmented with information retrieved from the RAG corpus.

### Configurable Parameters

The script includes the following configurable parameters that you need to update:

*   `PROJECT_ID`: Your Google Cloud Project ID.
*   `display_name`: The desired display name for your RAG corpus (e.g., "test_corpus").
*   `paths`: A list of strings containing Google Cloud Storage URIs (e.g., "gs://my_bucket/my_files_dir") or Google Drive links (e.g., "https://drive.google.com/file/d/123") pointing to the documents you want to import into the corpus.

## Prerequisites

Before running the script, ensure you have the following:

*   A Google Cloud Project.
*   The Vertex AI API enabled in your Google Cloud Project.
*   A Vertex AI endpoint configured for your project.
*   Authenticated to Google Cloud (e.g., by running `gcloud auth application-default login`).
*   Python installed on your system.

## Installation & Setup

1.  **Clone the repository (if applicable):**
    ```bash
    # If this script is part of a Git repository, clone it:
    # git clone <repository-url>
    # cd <repository-directory>
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install the required Python libraries:**
    ```bash
    pip install google-cloud-aiplatform vertexai
    ```
    *   `google-cloud-aiplatform`: The official Google Cloud library for Vertex AI.
    *   `vertexai`: The Vertex AI SDK, which includes the RAG functionalities.

4.  **Configure the script parameters:**
    Open the `rag-engine-vanilla.py` script and update the following placeholder values:
    *   `PROJECT_ID = "your-project-id"`: Replace `"your-project-id"` with your actual Google Cloud Project ID.
    *   `display_name = "test_corpus"`: You can change this to your preferred name for the RAG corpus.
    *   `paths = ["https://drive.google.com/file/d/123", "gs://my_bucket/my_files_dir"]`: Replace these with the actual Google Drive links or Google Cloud Storage URIs of the files you want to import.

## Usage

Once the prerequisites are met and the setup is complete:

1.  **Ensure your environment is activated (if you used a virtual environment):**
    ```bash
    source venv/bin/activate
    ```

2.  **Run the script:**
    ```bash
    python rag-engine-vanilla.py
    ```
    The script will then execute the defined steps: create a RAG corpus, import your specified files, perform a retrieval query, and finally generate content using the RAG-enhanced model. The output, including the retrieved context and the generated text, will be printed to the console.

## Customization

The `rag-engine-vanilla.py` script provides several points for customization to tailor it to your specific use case:

*   **Embedding Model**:
    *   The script uses `"text-embedding-005"` by default. You can change this by modifying the `publisher_model` in the `RagEmbeddingModelConfig`.
    *   Ensure the chosen model is compatible and available in your Vertex AI environment.
    ```python
    embedding_model_config = rag.RagEmbeddingModelConfig(
        vertex_prediction_endpoint=rag.VertexPredictionEndpoint(
            publisher_model="publishers/google/models/your-chosen-embedding-model"  # Update here
        )
    )
    ```

*   **Chunking Configuration**:
    *   During file import, you can adjust how documents are split into chunks.
    *   Modify `chunk_size` (default: 512 tokens) and `chunk_overlap` (default: 100 tokens) within the `ChunkingConfig`.
    ```python
    rag.import_files(
        rag_corpus.name,
        paths,
        transformation_config=rag.TransformationConfig(
            chunking_config=rag.ChunkingConfig(
                chunk_size=1024,  # Example: Larger chunk size
                chunk_overlap=200, # Example: Larger overlap
            ),
        ),
        # ...
    )
    ```

*   **Retrieval Parameters**:
    *   When performing a direct retrieval or setting up the RAG tool, you can customize retrieval behavior.
    *   `top_k`: (default: 3) The number of top matching chunks to retrieve.
    *   `filter`: (default: `vector_distance_threshold=0.5`) The threshold for filtering chunks based on vector distance. A lower value means stricter matching.
    ```python
    rag_retrieval_config = rag.RagRetrievalConfig(
        top_k=5,  # Retrieve more chunks
        filter=rag.Filter(vector_distance_threshold=0.4),  # Stricter filtering
    )
    ```

*   **Generative Model for RAG**:
    *   The script uses `"gemini-2.0-flash-001"` for the RAG-enhanced generation. You can switch to other compatible Gemini models based on your needs (e.g., `"gemini-1.0-pro"`).
    ```python
    rag_model = GenerativeModel(
        model_name="gemini-1.0-pro-002",  # Example: Different Gemini model
        tools=[rag_retrieval_tool]
    )
    ```

*   **Input Documents**:
    *   Modify the `paths` list to point to your own set of documents in Google Cloud Storage or Google Drive.

By adjusting these parameters, you can fine-tune the RAG pipeline's performance, relevance of retrieved information, and the nature of the generated content.

## Contributing

Guidelines for contributing to the project.

## License

Information about the project's license.
