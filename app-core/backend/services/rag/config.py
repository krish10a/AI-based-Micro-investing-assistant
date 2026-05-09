"""RAG configuration settings."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RAGSettings:
    """RAG service configuration.

    All settings are designed to be overridden via environment variables
    or passed explicitly for testing/multi-agent scenarios.
    """

    # Pinecone configuration
    pinecone_api_key: str
    pinecone_index_name: str = "microinvesting"  # User's actual index
    pinecone_environment: str = "gcp-starter"
    pinecone_host: str = ""  # Full host URL including https://

    # NVIDIA NIM configuration (for embeddings)
    nvidia_nim_api_key: str = ""

    # Embedding model configuration
    # Using NVIDIA's free endpoint: llama-3.2-nemoretriever-300m-embed-v1
    embedding_model: str = "nvidia/llama-3.2-nemoretriever-300m-embed-v1"
    embedding_dimension: int = 1024  # Dimension for llama-3.2-nemoretriever-300m-embed-v1

    # Text chunking configuration
    chunk_size: int = 500  # Characters per chunk
    chunk_overlap: int = 50  # Overlap between chunks for context preservation

    # Retrieval configuration
    top_k_results: int = 5  # Number of results to retrieve
    similarity_threshold: float = 0.3  # Minimum similarity score

    # Indexing configuration
    batch_size: int = 100  # Documents to batch during indexing

    @classmethod
    def from_env(cls) -> "RAGSettings":
        """Create settings from environment variables."""
        import os

        return cls(
            pinecone_api_key=os.environ.get("PINECONE_API_KEY", ""),
            pinecone_index_name=os.environ.get(
                "PINECONE_INDEX_NAME", "microinvesting"
            ),
            pinecone_host=os.environ.get("PINECONE_HOST", ""),
            nvidia_nim_api_key=os.environ.get("NVIDIA_NIM_API_KEY", ""),
            embedding_model=os.environ.get(
                "RAG_EMBEDDING_MODEL",
                "nvidia/llama-3.2-nemoretriever-300m-embed-v1",
            ),
            embedding_dimension=int(
                os.environ.get("RAG_EMBEDDING_DIMENSION", "1024")
            ),
            chunk_size=int(os.environ.get("RAG_CHUNK_SIZE", "500")),
            chunk_overlap=int(os.environ.get("RAG_CHUNK_OVERLAP", "50")),
            top_k_results=int(os.environ.get("RAG_TOP_K", "5")),
            similarity_threshold=float(
                os.environ.get("RAG_SIMILARITY_THRESHOLD", "0.3")
            ),
            batch_size=int(os.environ.get("RAG_BATCH_SIZE", "100")),
        )

    def check_config(self) -> None:
        """Validate required settings (no-op for now - env loaded at runtime)."""
        pass
