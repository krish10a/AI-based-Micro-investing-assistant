"""Main RAG service orchestrating document processing, embeddings, and retrieval."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.rag import DocumentChunk

from services.rag.config import RAGSettings
from services.rag.document_processor import DocumentProcessor
from services.rag.embedding_service import EmbeddingService
from services.rag.vector_store import VectorStore


class RAGService:
    """Retrieval-Augmented Generation service.

    This service orchestrates the complete RAG pipeline:
    1. Document ingestion and chunking
    2. Embedding generation
    3. Vector storage in Pinecone
    4. Semantic retrieval for queries

    Designed to be:
    - Modular: Each component can be swapped independently
    - Production-ready: Proper error handling and validation
    - Multi-agent ready: Stateless design with explicit dependencies
    """

    def __init__(
        self,
        settings: RAGSettings | None = None,
        embedding_service: EmbeddingService | None = None,
        vector_store: VectorStore | None = None,
        document_processor: DocumentProcessor | None = None,
    ):
        """Initialize the RAG service.

        Args:
            settings: RAG settings (auto-created from env if not provided)
            embedding_service: Optional custom embedding service
            vector_store: Optional custom vector store
            document_processor: Optional custom document processor

        Note:
            For multi-agent scenarios, you can inject custom services.
            For normal use, settings alone is sufficient.
        """
        self.settings = settings or RAGSettings.from_env()
        # Skip strict validation - errors will be raised when actually used

        self.embedding_service = embedding_service or EmbeddingService(
            api_key=self.settings.nvidia_nim_api_key,
            model=self.settings.embedding_model,
            dimension=self.settings.embedding_dimension,
        )

        self.vector_store = vector_store or VectorStore(
            api_key=self.settings.pinecone_api_key,
            index_name=self.settings.pinecone_index_name,
            dimension=self.settings.embedding_dimension,
            host=self.settings.pinecone_host,
        )

        self.document_processor = document_processor or DocumentProcessor(
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
        )

    async def initialize(self) -> bool:
        """Initialize the service and verify connection.

        Returns:
            True if initialization successful

        Raises:
            ValueError: If index doesn't exist or connection fails
        """
        exists = await self.vector_store.index_exists()

        if not exists:
            raise ValueError(
                f"Pinecone index '{self.settings.pinecone_index_name}' not found. "
                "Please create the index in your Pinecone dashboard first. "
                "See instructions below."
            )

        return True

    async def close(self) -> None:
        """Close all connections."""
        await self.embedding_service.close()
        await self.vector_store.close()

    async def ingest_document(
        self,
        text: str,
        source: str = "unknown",
    ) -> int:
        """Ingest a document into the RAG system.

        Args:
            text: Document text content
            source: Source identifier (file path, URL, etc.)

        Returns:
            Number of vectors indexed
        """
        # Chunk the document
        chunks = self.document_processor.process_text(text, source=source)

        if not chunks:
            return 0

        # Generate embeddings
        embeddings = await self.embedding_service.embed_documents(chunks)

        # Prepare vectors for upsert
        vectors = []
        for chunk, embedding in zip(chunks, embeddings):
            metadata = {
                "source": chunk.source,
                "chunk_index": chunk.chunk_index,
                "total_chunks": chunk.total_chunks,
                "char_length": chunk.metadata.get("char_length", "0")
                if chunk.metadata
                else "0",
            }
            vectors.append((chunk.chunk_id, embedding, metadata))

        # Upsert to Pinecone
        count = await self.vector_store.upsert(vectors)

        return count

    async def ingest_file(self, file_path: str) -> int:
        """Ingest a file into the RAG system.

        Args:
            file_path: Path to the file

        Returns:
            Number of vectors indexed
        """
        chunks = self.document_processor.process_file(file_path)

        if not chunks:
            return 0

        embeddings = await self.embedding_service.embed_documents(chunks)

        vectors = []
        for chunk, embedding in zip(chunks, embeddings):
            metadata = {
                "source": chunk.source,
                "chunk_index": chunk.chunk_index,
                "total_chunks": chunk.total_chunks,
                "char_length": chunk.metadata.get("char_length", "0")
                if chunk.metadata
                else "0",
            }
            vectors.append((chunk.chunk_id, embedding, metadata))

        count = await self.vector_store.upsert(vectors)

        return count

    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        filter: dict | None = None,
    ) -> list[dict]:
        """Retrieve relevant documents for a query.

        Args:
            query: Search query text
            top_k: Number of results (uses settings default if not provided)
            filter: Optional filter dictionary

        Returns:
            List of results with score, metadata, and vector ID
        """
        top_k = top_k or self.settings.top_k_results

        results = await self.vector_store.query_by_text(
            text=query,
            embedding_service=self.embedding_service,
            top_k=top_k,
            filter=filter,
        )

        # Filter by similarity threshold
        filtered_results = []
        for result in results:
            score = result.get("score", 0)
            if score >= self.settings.similarity_threshold:
                filtered_results.append(result)

        return filtered_results

    async def retrieve_as_context(
        self,
        query: str,
        top_k: int | None = None,
        filter: dict | None = None,
    ) -> str:
        """Retrieve relevant documents and format as context string.

        Args:
            query: Search query text
            top_k: Number of results
            filter: Optional filter dictionary

        Returns:
            Formatted context string for RAG augmentation
        """
        results = await self.retrieve(query, top_k=top_k, filter=filter)

        if not results:
            return "No relevant context found."

        context_parts = []
        for i, result in enumerate(results, 1):
            metadata = result.get("metadata", {})
            source = metadata.get("source", "unknown")
            chunk_index = metadata.get("chunk_index", 0)

            # Note: Pinecone doesn't return the vector values in query by default
            # We need to fetch the original content separately if needed
            # For now, we'll note that the content should be stored in metadata
            # or retrieved from a separate document store

            context_parts.append(f"[{i}] Source: {source} (chunk {chunk_index})")

        return "\n\n".join(context_parts)

    async def retrieve_with_content(
        self,
        query: str,
        top_k: int | None = None,
        filter: dict | None = None,
    ) -> list[dict]:
        """Retrieve relevant documents with full content.

        Args:
            query: Search query text
            top_k: Number of results
            filter: Optional filter dictionary

        Returns:
            List of results with content, score, and metadata
        """
        results = await self.retrieve(query, top_k=top_k, filter=filter)

        # Fetch full content for each result
        enriched_results = []
        for result in results:
            vector_id = result.get("id", "")
            metadata = result.get("metadata", {})
            source = metadata.get("source", "")

            # Extract chunk info from ID
            if "_" in vector_id:
                source_from_id, chunk_index = vector_id.rsplit("_", 1)
            else:
                source_from_id = source
                chunk_index = "0"

            enriched_results.append({
                "id": vector_id,
                "score": result.get("score", 0),
                "metadata": metadata,
                "source": source,
                "chunk_index": chunk_index,
            })

        return enriched_results

    async def delete_document(self, source: str) -> int:
        """Delete all vectors from a source document.

        Args:
            source: Source identifier to filter by

        Returns:
            Number of vectors deleted
        """
        filter_dict = {"source": source}
        return await self.vector_store.delete_by_filter(filter_dict)

    async def get_stats(self) -> dict:
        """Get statistics about the RAG index.

        Returns:
            Dictionary with index statistics
        """
        return await self.vector_store.describe_index_stats()

    @property
    def is_ready(self) -> bool:
        """Check if the service is properly configured."""
        return bool(
            self.settings.pinecone_api_key
            and self.settings.pinecone_index_name
        )
