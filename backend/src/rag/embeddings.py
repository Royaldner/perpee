"""
Embeddings module for Perpee RAG system.
Uses OpenAI text-embedding-3-small for generating embeddings.
"""

import logging
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI, OpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config.settings import get_settings
from src.core.exceptions import EmbeddingError

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""

    embedding: list[float]
    model: str
    tokens_used: int


@dataclass
class BatchEmbeddingResult:
    """Result of batch embedding generation."""

    embeddings: list[list[float]]
    model: str
    total_tokens: int


class EmbeddingService:
    """
    Service for generating embeddings using OpenAI.

    Features:
    - OpenAI text-embedding-3-small (1536 dimensions)
    - Batch embedding support
    - Automatic retries with exponential backoff
    """

    MODEL = "text-embedding-3-small"
    DIMENSION = 1536
    MAX_BATCH_SIZE = 100  # OpenAI limit
    MAX_INPUT_TOKENS = 8191  # Model limit

    def __init__(self, api_key: str | None = None):
        """
        Initialize embedding service.

        Args:
            api_key: OpenAI API key (uses settings default if None)
        """
        settings = get_settings()
        self._api_key = api_key or settings.openai_api_key

        if not self._api_key:
            logger.warning("OpenAI API key not configured - embeddings will fail")

        self._sync_client: OpenAI | None = None
        self._async_client: AsyncOpenAI | None = None

    @property
    def sync_client(self) -> OpenAI:
        """Get synchronous OpenAI client."""
        if self._sync_client is None:
            self._sync_client = OpenAI(api_key=self._api_key)
        return self._sync_client

    @property
    def async_client(self) -> AsyncOpenAI:
        """Get asynchronous OpenAI client."""
        if self._async_client is None:
            self._async_client = AsyncOpenAI(api_key=self._api_key)
        return self._async_client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True,
    )
    def embed(self, text: str) -> EmbeddingResult:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            EmbeddingResult with embedding vector

        Raises:
            EmbeddingError: If embedding generation fails
        """
        if not text or not text.strip():
            raise EmbeddingError("Cannot embed empty text")

        try:
            response = self.sync_client.embeddings.create(
                model=self.MODEL,
                input=text,
            )

            return EmbeddingResult(
                embedding=response.data[0].embedding,
                model=response.model,
                tokens_used=response.usage.total_tokens,
            )
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise EmbeddingError(f"Failed to generate embedding: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True,
    )
    async def embed_async(self, text: str) -> EmbeddingResult:
        """
        Generate embedding for a single text asynchronously.

        Args:
            text: Text to embed

        Returns:
            EmbeddingResult with embedding vector

        Raises:
            EmbeddingError: If embedding generation fails
        """
        if not text or not text.strip():
            raise EmbeddingError("Cannot embed empty text")

        try:
            response = await self.async_client.embeddings.create(
                model=self.MODEL,
                input=text,
            )

            return EmbeddingResult(
                embedding=response.data[0].embedding,
                model=response.model,
                tokens_used=response.usage.total_tokens,
            )
        except Exception as e:
            logger.error(f"Async embedding generation failed: {e}")
            raise EmbeddingError(f"Failed to generate embedding: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True,
    )
    def embed_batch(self, texts: list[str]) -> BatchEmbeddingResult:
        """
        Generate embeddings for multiple texts in batch.

        Args:
            texts: List of texts to embed

        Returns:
            BatchEmbeddingResult with embeddings

        Raises:
            EmbeddingError: If embedding generation fails
        """
        if not texts:
            raise EmbeddingError("Cannot embed empty text list")

        # Filter empty texts
        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            raise EmbeddingError("All texts are empty")

        # Handle batching for large lists
        if len(valid_texts) > self.MAX_BATCH_SIZE:
            return self._embed_batch_chunked(valid_texts)

        try:
            response = self.sync_client.embeddings.create(
                model=self.MODEL,
                input=valid_texts,
            )

            embeddings = [data.embedding for data in response.data]

            return BatchEmbeddingResult(
                embeddings=embeddings,
                model=response.model,
                total_tokens=response.usage.total_tokens,
            )
        except Exception as e:
            logger.error(f"Batch embedding generation failed: {e}")
            raise EmbeddingError(f"Failed to generate batch embeddings: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True,
    )
    async def embed_batch_async(self, texts: list[str]) -> BatchEmbeddingResult:
        """
        Generate embeddings for multiple texts asynchronously.

        Args:
            texts: List of texts to embed

        Returns:
            BatchEmbeddingResult with embeddings

        Raises:
            EmbeddingError: If embedding generation fails
        """
        if not texts:
            raise EmbeddingError("Cannot embed empty text list")

        # Filter empty texts
        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            raise EmbeddingError("All texts are empty")

        # Handle batching for large lists
        if len(valid_texts) > self.MAX_BATCH_SIZE:
            return await self._embed_batch_chunked_async(valid_texts)

        try:
            response = await self.async_client.embeddings.create(
                model=self.MODEL,
                input=valid_texts,
            )

            embeddings = [data.embedding for data in response.data]

            return BatchEmbeddingResult(
                embeddings=embeddings,
                model=response.model,
                total_tokens=response.usage.total_tokens,
            )
        except Exception as e:
            logger.error(f"Async batch embedding generation failed: {e}")
            raise EmbeddingError(f"Failed to generate batch embeddings: {e}") from e

    def _embed_batch_chunked(self, texts: list[str]) -> BatchEmbeddingResult:
        """Embed large batch by chunking into smaller batches."""
        all_embeddings = []
        total_tokens = 0
        model = self.MODEL

        for i in range(0, len(texts), self.MAX_BATCH_SIZE):
            chunk = texts[i : i + self.MAX_BATCH_SIZE]
            response = self.sync_client.embeddings.create(
                model=self.MODEL,
                input=chunk,
            )

            all_embeddings.extend([data.embedding for data in response.data])
            total_tokens += response.usage.total_tokens
            model = response.model

        return BatchEmbeddingResult(
            embeddings=all_embeddings,
            model=model,
            total_tokens=total_tokens,
        )

    async def _embed_batch_chunked_async(self, texts: list[str]) -> BatchEmbeddingResult:
        """Embed large batch by chunking into smaller batches asynchronously."""
        all_embeddings = []
        total_tokens = 0
        model = self.MODEL

        for i in range(0, len(texts), self.MAX_BATCH_SIZE):
            chunk = texts[i : i + self.MAX_BATCH_SIZE]
            response = await self.async_client.embeddings.create(
                model=self.MODEL,
                input=chunk,
            )

            all_embeddings.extend([data.embedding for data in response.data])
            total_tokens += response.usage.total_tokens
            model = response.model

        return BatchEmbeddingResult(
            embeddings=all_embeddings,
            model=model,
            total_tokens=total_tokens,
        )


# ===========================================
# Helper Functions
# ===========================================


def create_product_document(
    name: str,
    brand: str | None = None,
    store: str | None = None,
    price: float | None = None,
    currency: str = "CAD",
) -> str:
    """
    Create a document string for product embedding.

    Args:
        name: Product name
        brand: Product brand
        store: Store name
        price: Current price
        currency: Currency code

    Returns:
        Formatted document string for embedding
    """
    parts = [name]

    if brand:
        parts.append(f"Brand: {brand}")
    if store:
        parts.append(f"Store: {store}")
    if price is not None:
        parts.append(f"Price: {currency} {price:.2f}")

    return " | ".join(parts)


def create_product_metadata(
    product_id: int,
    name: str,
    store_domain: str,
    current_price: float | None = None,
    in_stock: bool = True,
    brand: str | None = None,
    upc: str | None = None,
) -> dict[str, Any]:
    """
    Create metadata dict for ChromaDB storage.

    Args:
        product_id: Product database ID
        name: Product name
        store_domain: Store domain
        current_price: Current price
        in_stock: Stock status
        brand: Product brand
        upc: Universal Product Code

    Returns:
        Metadata dict for ChromaDB
    """
    metadata: dict[str, Any] = {
        "product_id": product_id,
        "name": name,
        "store_domain": store_domain,
        "in_stock": in_stock,
    }

    if current_price is not None:
        metadata["current_price"] = current_price
    if brand:
        metadata["brand"] = brand
    if upc:
        metadata["upc"] = upc

    return metadata


# ===========================================
# Global Service Instance
# ===========================================

_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Get the global embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


def reset_embedding_service() -> None:
    """Reset the global embedding service instance."""
    global _embedding_service
    _embedding_service = None
