"""Embedding service using NVIDIA NIM embeddings API."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    import httpx


class EmbeddingService:
    """Service for generating text embeddings using NVIDIA NIM.

    Uses NVIDIA's free endpoint embedding model for high-quality
    text embeddings optimized for RAG retrieval tasks.

    Model: nvidia/llama-3.2-nemoretriever-300m-embed-v1
    - 1024-dimensional embeddings
    - Optimized for question-answering retrieval
    - Free endpoint available via NVIDIA NIM
    """

    def __init__(
        self,
        api_key: str,
        model: str = "nvidia/llama-3.2-nemoretriever-300m-embed-v1",
        base_url: str = "https://integrate.api.nvidia.com/v1",
        dimension: int = 1024,
        timeout: float = 60.0,
    ):
        """Initialize the embedding service.

        Args:
            api_key: NVIDIA NIM API key
            model: Embedding model to use
            base_url: NVIDIA NIM API base URL
            dimension: Expected embedding dimension
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.dimension = dimension
        self.timeout = timeout

        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(
                    connect=self.timeout,
                    read=self.timeout,
                    write=10.0,
                    pool=self.timeout,
                ),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
        self._client = None

    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            ValueError: If API returns an error
        """
        client = await self._get_client()

        response = await client.post(
            "/embeddings",
            json={
                "model": self.model,
                "input": [text],
                "encoding_format": "float",
                "input_type": "query",
                "truncate": "NONE",
            },
        )

        if response.status_code != 200:
            raise ValueError(
                f"Embedding API error ({response.status_code}): {response.text}"
            )

        data = response.json()
        embeddings = data.get("data", [])

        if not embeddings:
            raise ValueError("No embedding returned from API")

        return embeddings[0]["embedding"]

    async def embed_texts(
        self, texts: Sequence[str], batch_size: int = 10
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process in parallel

        Returns:
            List of embedding vectors
        """
        # NVIDIA NIM supports batched requests, so we can send all at once
        client = await self._get_client()

        response = await client.post(
            "/embeddings",
            json={
                "model": self.model,
                "input": list(texts),
                "encoding_format": "float",
                "input_type": "query",
                "truncate": "NONE",
            },
        )

        if response.status_code != 200:
            raise ValueError(
                f"Embedding API error ({response.status_code}): {response.text}"
            )

        data = response.json()
        embeddings = data.get("data", [])

        # Sort by index to maintain order
        embeddings.sort(key=lambda x: x["index"])

        return [e["embedding"] for e in embeddings]

    async def embed_documents(
        self, chunks: list["DocumentChunk"], batch_size: int = 10
    ) -> list[list[float]]:
        """Generate embeddings for document chunks.

        Args:
            chunks: List of DocumentChunk objects
            batch_size: Batch size for processing

        Returns:
            List of embedding vectors corresponding to chunks
        """
        from services.rag import DocumentChunk

        texts = [chunk.content for chunk in chunks]
        return await self.embed_texts(texts, batch_size=batch_size)

    @property
    def model_info(self) -> dict:
        """Get information about the embedding model."""
        return {
            "model": self.model,
            "dimension": self.dimension,
            "base_url": self.base_url,
        }
