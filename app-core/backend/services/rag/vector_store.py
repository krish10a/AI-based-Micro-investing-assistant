"""Pinecone vector store for RAG document retrieval."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    import httpx


class VectorStore:
    """Pinecone vector store for RAG document retrieval.

    This is a lightweight, production-ready wrapper around Pinecone's API
    that doesn't require the pinecone-client library. It uses direct HTTP
    calls for better control and fewer dependencies.

    Features:
    - Upsert vectors with metadata
    - Semantic similarity search
    - Filter support
    - Batch operations
    """

    def __init__(
        self,
        api_key: str,
        index_name: str,
        dimension: int = 1024,
        host: str = "",
        timeout: float = 60.0,
    ):
        """Initialize the vector store.

        Args:
            api_key: Pinecone API key
            index_name: Name of the Pinecone index
            dimension: Dimension of the embedding vectors
            host: Full Pinecone host URL (e.g., "index-name.region.svc.pinecone.io")
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.index_name = index_name
        self.dimension = dimension
        self.timeout = timeout

        # Use direct host for modern Pinecone indexes
        # Remove https:// prefix if present to avoid double https://
        if host:
            clean_host = host.replace("https://", "").replace("http://", "")
            self.api_base = f"https://{clean_host}"
        else:
            # Fallback to old-style URL construction
            self.api_base = f"https://{index_name}-default.svc.aped-4627-b74a.pinecone.io"

        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.api_base,
                timeout=httpx.Timeout(
                    connect=self.timeout,
                    read=self.timeout,
                    write=self.timeout,
                    pool=self.timeout,
                ),
                headers={
                    "Api-Key": self.api_key,
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
        self._client = None

    async def index_exists(self) -> bool:
        """Check if the index exists.

        Returns:
            True if index exists, False otherwise
        """
        # We can't directly check index existence without the SDK,
        # but we can try to describe the index
        client = await self._get_client()

        try:
            response = await client.get("/describe_index_stats")
            return response.status_code == 200
        except Exception:
            return False

    async def upsert(
        self,
        vectors: Sequence[tuple[str, list[float], dict]],
        batch_size: int = 100,
    ) -> int:
        """Upsert vectors into the index.

        Args:
            vectors: List of (id, vector, metadata) tuples
            batch_size: Number of vectors to upsert per batch

        Returns:
            Total number of vectors upserted
        """
        client = await self._get_client()
        total_upserted = 0

        for i in range(0, len(vectors), batch_size):
            batch = vectors[i : i + batch_size]

            # Format vectors for Pinecone API
            request_vectors = []
            for vec_id, vector, metadata in batch:
                request_vectors.append(
                    {
                        "id": vec_id,
                        "values": vector,
                        "metadata": metadata,
                    }
                )

            response = await client.post("/vectors/upsert", json={"vectors": request_vectors})

            if response.status_code != 200:
                raise ValueError(
                    f"Upsert failed ({response.status_code}): {response.text}"
                )

            total_upserted += len(batch)

        return total_upserted

    async def query(
        self,
        vector: list[float],
        top_k: int = 5,
        filter: dict | None = None,
        include_metadata: bool = True,
    ) -> list[dict]:
        """Query the vector store for similar documents.

        Args:
            vector: Query embedding vector
            top_k: Number of results to return
            filter: Optional filter dictionary
            include_metadata: Whether to include metadata in results

        Returns:
            List of matching results with scores and metadata
        """
        client = await self._get_client()

        request = {
            "vector": vector,
            "topK": top_k,
            "includeMetadata": include_metadata,
        }

        if filter:
            request["filter"] = filter

        response = await client.post("/query", json=request)

        if response.status_code != 200:
            raise ValueError(
                f"Query failed ({response.status_code}): {response.text}"
            )

        data = response.json()
        return data.get("matches", [])

    async def query_by_text(
        self,
        text: str,
        embedding_service: "EmbeddingService",
        top_k: int = 5,
        filter: dict | None = None,
    ) -> list[dict]:
        """Query the vector store using text (auto-embeds the text).

        Args:
            text: Query text
            embedding_service: EmbeddingService instance for embedding
            top_k: Number of results to return
            filter: Optional filter dictionary

        Returns:
            List of matching results with scores and metadata
        """
        vector = await embedding_service.embed_text(text)
        return await self.query(vector, top_k=top_k, filter=filter)

    async def delete_vectors(self, ids: list[str]) -> int:
        """Delete vectors by ID.

        Args:
            ids: List of vector IDs to delete

        Returns:
            Number of vectors deleted
        """
        client = await self._get_client()

        response = await client.post("/vectors/delete", json={"ids": ids})

        if response.status_code != 200:
            raise ValueError(
                f"Delete failed ({response.status_code}): {response.text}"
            )

        return len(ids)

    async def delete_by_filter(self, filter: dict) -> int:
        """Delete vectors matching a filter.

        Args:
            filter: Filter dictionary

        Returns:
            Number of vectors deleted
        """
        client = await self._get_client()

        response = await client.post("/vectors/delete", json={"filter": filter})

        if response.status_code != 200:
            raise ValueError(
                f"Delete by filter failed ({response.status_code}): {response.text}"
            )

        # Pinecone doesn't return count, so we return -1 to indicate unknown
        return -1

    async def describe_index_stats(self) -> dict:
        """Get statistics about the index.

        Returns:
            Dictionary with index statistics
        """
        client = await self._get_client()

        response = await client.get("/describe_index_stats")

        if response.status_code != 200:
            raise ValueError(
                f"Describe index stats failed ({response.status_code}): {response.text}"
            )

        return response.json()

    async def fetch(self, ids: list[str]) -> dict:
        """Fetch vectors by ID.

        Args:
            ids: List of vector IDs to fetch

        Returns:
            Dictionary with vector data
        """
        client = await self._get_client()

        response = await client.post("/vectors/fetch", json={"ids": ids})

        if response.status_code != 200:
            raise ValueError(
                f"Fetch failed ({response.status_code}): {response.text}"
            )

        return response.json()
